from datetime import date, timedelta

from django.http import HttpResponse
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminRole

from .grids import MAX_DAYS, REPORTS, corrective_rows
from .pdf import render_report

DEFAULT_DAYS = 28


class ReportView(APIView):
    """Admin: a PDF for one of the paper tables. ?from=YYYY-MM-DD&to=YYYY-MM-DD (default: the last 4 weeks)."""

    permission_classes = [IsAdminRole]

    def get(self, request, kind):
        heading, build_content = REPORTS[kind]
        today = timezone.localdate()
        try:
            end = date.fromisoformat(request.query_params.get('to', today.isoformat()))
            start = date.fromisoformat(request.query_params.get('from', (end - timedelta(days=DEFAULT_DAYS - 1)).isoformat()))
        except ValueError:
            return Response({'code': 'bad_date', 'message': 'Use dates like 2026-11-02.'}, status=400)
        if start > end:
            return Response({'code': 'bad_range', 'message': 'The start date is after the end date.'}, status=400)
        if (end - start).days >= MAX_DAYS:
            return Response(
                {'code': 'range_too_long', 'message': f'Choose a period of up to {MAX_DAYS} days.'}, status=400
            )

        pdf = render_report(kind, heading, start, end, build_content(start, end), corrective_rows(start, end, kind))
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{kind}-{start}-to-{end}.pdf"'
        return response
