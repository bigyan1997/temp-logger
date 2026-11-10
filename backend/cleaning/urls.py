from rest_framework.routers import DefaultRouter

from .views import CleaningCheckViewSet, CleaningTaskViewSet

router = DefaultRouter()
router.register('cleaning-tasks', CleaningTaskViewSet, basename='cleaning-task')
router.register('cleaning-checks', CleaningCheckViewSet, basename='cleaning-check')

urlpatterns = router.urls
