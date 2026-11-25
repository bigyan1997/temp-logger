from django.db import transaction
from django.db.models import Q
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminRole
from audit.models import AuditLog, record
from nonconformance import photos
from nonconformance.views import named_person
from setup.models import StaffMember

from django.utils import timezone

from .drive import copy_file
from .due import equipment_due
from .removal import delete_file, delete_record
from .models import ServiceFile, ServiceRecord
from .serializers import ServiceEditSerializer, ServiceFileSerializer, ServiceRecordSerializer

MAX_FILES = 20


class Pagination(PageNumberPagination):
    page_size = 50


def delete_details(request):
    """The reason and the person for a delete, or (an error Response, None) when one is missing."""
    reason = str(request.data.get('reason', '')).strip()
    if len(reason) < 3:
        return Response({'reason': 'Say why it is being deleted.'}, status=status.HTTP_400_BAD_REQUEST), None
    person = named_person(request)
    if not person:
        return Response({'recorded_by': 'Pick your name first.'}, status=status.HTTP_400_BAD_REQUEST), None
    return reason[:300], person


class ServiceRecordViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Day staff only. Edits go to the audit log; a record or file can be deleted with a reason (see removal.py)."""

    permission_classes = [IsAdminRole]
    serializer_class = ServiceRecordSerializer
    pagination_class = Pagination
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def get_queryset(self):
        services = ServiceRecord.objects.select_related('recorded_by', 'entered_by').prefetch_related('files__recorded_by')
        params = self.request.query_params
        if params.get('from'):
            services = services.filter(service_date__gte=params['from'])
        if params.get('to'):
            services = services.filter(service_date__lte=params['to'])
        if params.get('kind') in ('service', 'repair'):
            services = services.filter(kind=params['kind'])
        if params.get('equipment'):
            services = services.filter(equipment__iexact=params['equipment'])
        search = params.get('q', '').strip()
        if search:
            services = services.filter(
                Q(equipment__icontains=search) | Q(serviced_by__icontains=search) | Q(work_done__icontains=search)
                | Q(invoice_number__icontains=search)
            )
        return services

    def perform_create(self, serializer):
        serializer.save(entered_by=self.request.user)

    @action(detail=False, methods=['get'])
    def due(self, request):
        """Each piece of equipment with the date its next 6-monthly service is due."""
        return Response(equipment_due(timezone.localdate()))

    @action(detail=True, methods=['post'])
    def add_files(self, request, pk=None):
        """Attach invoices or photos (multipart form field `files`, plus `recorded_by`)."""
        service = self.get_object()
        person = StaffMember.objects.filter(pk=request.data.get('recorded_by') or 0, active=True).first()
        if not person:
            return Response({'recorded_by': 'Pick your name first.'}, status=status.HTTP_400_BAD_REQUEST)
        files = request.FILES.getlist('files')
        if not files:
            return Response({'files': 'Choose at least one file.'}, status=status.HTTP_400_BAD_REQUEST)
        if service.files.count() + len(files) > MAX_FILES:
            return Response({'files': f'A service record can have up to {MAX_FILES} files.'}, status=status.HTTP_400_BAD_REQUEST)

        saved = []
        for uploaded in files:
            try:
                relative, content_type, size = photos.save(uploaded)
            except ValueError as problem:
                return Response({'files': str(problem)}, status=status.HTTP_400_BAD_REQUEST)
            saved.append(ServiceFile.objects.create(
                service=service, path=relative, original_name=uploaded.name[:200], content_type=content_type, size=size,
                recorded_by=person, entered_by=request.user,
            ))
        for file in saved:
            copy_file(file)  # a second copy in Google Drive; a problem is kept on the file and retried later
        return Response(ServiceFileSerializer(saved, many=True).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def edit(self, request, pk=None):
        """Correct the details of a record. Needs the name of the person editing; the audit log keeps the old and new values."""
        service = self.get_object()
        person = named_person(request)
        if not person:
            return Response({'recorded_by': 'Pick your name first.'}, status=status.HTTP_400_BAD_REQUEST)
        serializer = ServiceEditSerializer(service, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        changes = [f'{name}: {getattr(service, name) or "-"} -> {value or "-"}'
                   for name, value in serializer.validated_data.items() if getattr(service, name) != value]
        if not changes:
            return Response(self.get_serializer(service).data)
        with transaction.atomic():
            serializer.save()
            record(request.user, AuditLog.Action.EDITED, f'Edited {service.number}: ' + '; '.join(changes), module=AuditLog.Module.SERVICING, staff=person)
        return Response(self.get_serializer(service).data)

    @action(detail=True, methods=['post'], url_path='delete')
    def remove(self, request, pk=None):
        """Delete the record and its files (needs a reason and the name of who is doing it). One audit line keeps what was deleted."""
        service = self.get_object()
        reason, person = delete_details(request)
        if isinstance(reason, Response):
            return reason
        return Response({'deleted': True, 'problems': delete_record(service, request.user, reason, person)})


class ServiceFileView(APIView):
    """GET sends the file itself (day login only)."""

    permission_classes = [IsAdminRole]

    def get(self, request, pk):
        file = get_object_or_404(ServiceFile, pk=pk)
        try:
            path = photos.full_path(file.path)
        except ValueError:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if not path.is_file():
            return Response({'detail': 'The file is missing on this computer.'}, status=status.HTTP_404_NOT_FOUND)
        response = FileResponse(
            open(path, 'rb'), content_type=file.content_type,
            as_attachment=not photos.shows_in_browser(file.content_type), filename=file.original_name,
        )
        response['X-Content-Type-Options'] = 'nosniff'
        return response


class ServiceFileDeleteView(APIView):
    permission_classes = [IsAdminRole]

    def post(self, request, pk):
        file = get_object_or_404(ServiceFile.objects.select_related('service'), pk=pk)
        reason, person = delete_details(request)
        if isinstance(reason, Response):
            return reason
        return Response({'deleted': True, 'problems': delete_file(file, request.user, reason, person)})
