from rest_framework.routers import DefaultRouter

from .views import CalibrationViewSet

router = DefaultRouter()
router.register('calibrations', CalibrationViewSet, basename='calibration')

urlpatterns = router.urls
