from rest_framework.routers import DefaultRouter

from .views import RunViewSet, StaffMemberViewSet, SupplierViewSet, UnitViewSet

router = DefaultRouter()
router.register('staff', StaffMemberViewSet, basename='staff')
router.register('units', UnitViewSet, basename='unit')
router.register('suppliers', SupplierViewSet, basename='supplier')
router.register('runs', RunViewSet, basename='run')

urlpatterns = router.urls
