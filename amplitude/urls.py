from rest_framework.routers import DefaultRouter

from .views import DailyDeviceActivityViewSet

router = DefaultRouter()
router.register('amplitude/today-mobile-activity', DailyDeviceActivityViewSet, basename='today-mobile-activity')

urlpatterns = router.urls
