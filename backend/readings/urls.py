from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    CorrectiveActionViewSet,
    DashboardView,
    DayView,
    DispatchReadingViewSet,
    ReadingOptionsView,
    ReceivingCheckViewSet,
    StorageReadingViewSet,
    TrendsView,
)

router = DefaultRouter()
router.register('storage-readings', StorageReadingViewSet, basename='storage-reading')
router.register('receiving-checks', ReceivingCheckViewSet, basename='receiving-check')
router.register('dispatch-readings', DispatchReadingViewSet, basename='dispatch-reading')
router.register('corrective-actions', CorrectiveActionViewSet, basename='corrective-action')

urlpatterns = [
    path('reading-options/', ReadingOptionsView.as_view()),
    path('dashboard/', DashboardView.as_view()),
    path('day/', DayView.as_view()),
    path('trends/', TrendsView.as_view()),
    *router.urls,
]
