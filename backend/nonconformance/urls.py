from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import NonConformanceViewSet, PhotoVoidView, PhotoView, UpdateVoidView

router = DefaultRouter()
router.register('non-conformances', NonConformanceViewSet, basename='non-conformance')

urlpatterns = [
    path('non-conformances/photos/<int:pk>/', PhotoView.as_view()),
    path('non-conformances/photos/<int:pk>/void/', PhotoVoidView.as_view()),
    path('non-conformances/updates/<int:pk>/void/', UpdateVoidView.as_view()),
] + router.urls
