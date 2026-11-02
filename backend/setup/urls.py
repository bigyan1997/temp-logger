from rest_framework.routers import DefaultRouter

from .views import AlertRecipientViewSet, RunViewSet, StaffMemberViewSet, SupplierViewSet, UnitViewSet

router = DefaultRouter()
router.register('staff', StaffMemberViewSet, basename='staff')
router.register('units', UnitViewSet, basename='unit')
router.register('suppliers', SupplierViewSet, basename='supplier')
router.register('runs', RunViewSet, basename='run')
router.register('alert-recipients', AlertRecipientViewSet, basename='alert-recipient')

urlpatterns = router.urls
