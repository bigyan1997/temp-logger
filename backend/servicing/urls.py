from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import ServiceFileView, ServiceFileDeleteView, ServiceRecordViewSet

router = DefaultRouter()
router.register('service-records', ServiceRecordViewSet, basename='service-record')

urlpatterns = [
    path('service-records/files/<int:pk>/', ServiceFileView.as_view()),
    path('service-records/files/<int:pk>/delete/', ServiceFileDeleteView.as_view()),
] + router.urls
