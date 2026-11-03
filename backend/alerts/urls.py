from rest_framework.routers import DefaultRouter

from .views import AlertSentViewSet

router = DefaultRouter()
router.register('alerts-sent', AlertSentViewSet, basename='alert-sent')

urlpatterns = router.urls
