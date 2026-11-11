from datetime import date, timedelta

from django.db import transaction
from django.db.models import Exists, OuterRef, Q
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminRole
from audit.models import AuditLog, record
from reports.grids import MAX_DAYS

from . import photos
from .drive import copy_photo, drive_link
from .saving import save_report_copies
from .models import NonConformance, Photo, Update
from .pdf import render_register, render_report
from .serializers import AddUpdateSerializer, NonConformanceSerializer, PhotoSerializer, UpdateSerializer

DEFAULT_REGISTER_DAYS = 365


class Pagination(PageNumberPagination):
    page_size = 50


def void_with_reason(request, item, label):
    """Mark a report, follow-up or photo void. Returns an error Response, or None when it worked."""
    if item.voided:
        return Response({'detail': 'This entry is already voided.'}, status=status.HTTP_400_BAD_REQUEST)
    reason = str(request.data.get('reason', '')).strip()
    if len(reason) < 3:
        return Response({'reason': 'Say why this is being voided.'}, status=status.HTTP_400_BAD_REQUEST)
    with transaction.atomic():
        item.voided = True
        item.void_reason = reason[:300]
        item.save(update_fields=['voided', 'void_reason'])
        record(request.user, AuditLog.Action.VOIDED, f'Voided: {label}', reason, module=AuditLog.Module.NONCONFORMANCE)
    return None


class NonConformanceViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Day staff only. A report is saved once and never edited or deleted. Follow-ups are added to it, and a mistake is
    voided with a reason."""

    permission_classes = [IsAdminRole]
    serializer_class = NonConformanceSerializer
    pagination_class = Pagination
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def get_queryset(self):
        reports = NonConformance.objects.select_related('recorded_by', 'entered_by').prefetch_related(
            'updates__recorded_by', 'updates__entered_by', 'photos__recorded_by',
        )
        params = self.request.query_params
        if self.action == 'list' and params.get('include_voided') != '1':
            reports = reports.filter(voided=False)
        if params.get('from'):
            reports = reports.filter(date__gte=params['from'])
        if params.get('to'):
            reports = reports.filter(date__lte=params['to'])
        search = params.get('q', '').strip()
        if search:
            reports = reports.filter(
                Q(product__icontains=search) | Q(customer__icontains=search) | Q(manufacturer__icontains=search)
                | Q(description__icontains=search)
            )
        closed = Exists(Update.objects.filter(report=OuterRef('pk'), kind=Update.Kind.CLOSED, voided=False))
        if params.get('status') == 'open':
            reports = reports.filter(~closed)
        elif params.get('status') == 'closed':
            reports = reports.filter(closed)
        return reports

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        notified_at = serializer.validated_data.pop('notified_at', None)
        with transaction.atomic():
            report = serializer.save(entered_by=request.user)
            if notified_at:  # "Has the manufacturer been notified?" answered on the first page of the report
                Update.objects.create(report=report, kind=Update.Kind.NOTIFIED, happened_at=notified_at,
                                      recorded_by=report.recorded_by, entered_by=request.user)
        return Response(self.get_serializer(report).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """How many reports are still open, and how long the oldest has been open."""
        open_reports = list(self.get_queryset().filter(voided=False).filter(~Exists(
            Update.objects.filter(report=OuterRef('pk'), kind=Update.Kind.CLOSED, voided=False))))
        oldest = min((r.date for r in open_reports), default=None)
        return Response({'open': len(open_reports), 'oldest_open_days': (timezone.localdate() - oldest).days if oldest else None,
                         'drive_url': drive_link()})

    @action(detail=True, methods=['post'])
    def updates(self, request, pk=None):
        """Add a follow-up: manufacturer notified, their response, a corrective action, a note, or closing the report."""
        report = self.get_object()
        if report.voided:
            return Response({'detail': 'This report is voided.'}, status=status.HTTP_400_BAD_REQUEST)
        serializer = AddUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if report.is_closed and data['kind'] != Update.Kind.NOTE:
            return Response({'detail': 'This report is closed. Only a note can be added.'}, status=status.HTTP_400_BAD_REQUEST)
        update = Update.objects.create(
            report=report, kind=data['kind'], text=data['text'], recorded_by=data['recorded_by'], entered_by=request.user,
            **({'happened_at': data['happened_at']} if 'happened_at' in data else {}),
        )
        return Response(UpdateSerializer(update).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def add_photos(self, request, pk=None):
        """Attach one or more photos (multipart form field `files`, plus `recorded_by`)."""
        report = self.get_object()
        if report.voided:
            return Response({'detail': 'This report is voided.'}, status=status.HTTP_400_BAD_REQUEST)
        person = AddUpdateSerializer(data={'kind': 'note', 'text': 'x', 'recorded_by': request.data.get('recorded_by')})
        person.is_valid(raise_exception=True)
        update = None
        if request.data.get('update'):  # the photo belongs to a follow-up, e.g. the manufacturer's response
            update = get_object_or_404(report.updates, pk=request.data['update'])
        files = request.FILES.getlist('files')
        if not files:
            return Response({'files': 'Choose at least one photo.'}, status=status.HTTP_400_BAD_REQUEST)
        if report.photos.filter(voided=False).count() + len(files) > photos.MAX_PER_REPORT:
            return Response({'files': f'A report can have up to {photos.MAX_PER_REPORT} photos.'}, status=status.HTTP_400_BAD_REQUEST)

        saved = []
        for uploaded in files:
            try:
                relative, content_type, size = photos.save(uploaded)
            except ValueError as problem:
                return Response({'files': str(problem)}, status=status.HTTP_400_BAD_REQUEST)
            saved.append(Photo.objects.create(
                report=report, update=update, path=relative, original_name=uploaded.name[:200], content_type=content_type, size=size,
                recorded_by=person.validated_data['recorded_by'], entered_by=request.user,
            ))
        for photo in saved:
            copy_photo(photo)  # a second copy in Google Drive; a problem is kept on the photo and retried later
        return Response(PhotoSerializer(saved, many=True).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def void(self, request, pk=None):
        report = self.get_object()
        problem = void_with_reason(request, report, str(report))
        return problem or Response(self.get_serializer(report).data)

    @action(detail=True, methods=['get'])
    def pdf(self, request, pk=None):
        report = self.get_object()
        response = HttpResponse(render_report(report), content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{report.number}.pdf"'
        return response

    @action(detail=True, methods=['post'])
    def save_to_drive(self, request, pk=None):
        """Save a PDF of the report, as it is now, on this PC and in Google Drive. Each press makes a new dated file."""
        return Response(save_report_copies(self.get_object()))

    @action(detail=False, methods=['get'])
    def register(self, request):
        """Table 5 as a register, a row for each report. ?from=&to= (default: the last year)."""
        today = timezone.localdate()
        try:
            end = date.fromisoformat(request.query_params.get('to', today.isoformat()))
            start = date.fromisoformat(request.query_params.get('from', (end - timedelta(days=DEFAULT_REGISTER_DAYS - 1)).isoformat()))
        except ValueError:
            return Response({'message': 'Use dates like 2026-11-02.'}, status=status.HTTP_400_BAD_REQUEST)
        if start > end or (end - start).days >= max(MAX_DAYS, DEFAULT_REGISTER_DAYS):
            return Response({'message': 'Choose a period of up to a year.'}, status=status.HTTP_400_BAD_REQUEST)
        response = HttpResponse(render_register(start, end), content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="non-conformance-register-{start}-to-{end}.pdf"'
        return response


class UpdateVoidView(APIView):
    permission_classes = [IsAdminRole]

    def post(self, request, pk):
        update = get_object_or_404(Update.objects.select_related('report'), pk=pk)
        problem = void_with_reason(request, update, f'{update.report.number} follow-up ({update.get_kind_display()})')
        return problem or Response(UpdateSerializer(update).data)


class PhotoView(APIView):
    """GET sends the picture itself (day login only). POST .../void/ cancels a photo put on by mistake."""

    permission_classes = [IsAdminRole]

    def get(self, request, pk):
        photo = get_object_or_404(Photo, pk=pk)
        try:
            path = photos.full_path(photo.path)
        except ValueError:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if not path.is_file():
            return Response({'detail': 'The photo file is missing on this computer.'}, status=status.HTTP_404_NOT_FOUND)
        response = FileResponse(open(path, 'rb'), content_type=photo.content_type)
        response['Content-Disposition'] = 'inline'
        response['X-Content-Type-Options'] = 'nosniff'
        return response


class PhotoVoidView(APIView):
    permission_classes = [IsAdminRole]

    def post(self, request, pk):
        photo = get_object_or_404(Photo.objects.select_related('report'), pk=pk)
        problem = void_with_reason(request, photo, f'{photo.report.number} photo {photo.original_name}')
        return problem or Response(PhotoSerializer(photo).data)
