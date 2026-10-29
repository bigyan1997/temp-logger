from django.urls import re_path

from .views import ReportView

urlpatterns = [
    re_path(r'^(?P<kind>storage|receiving|dispatch)\.pdf$', ReportView.as_view()),
]
