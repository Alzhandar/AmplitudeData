from rest_framework.routers import DefaultRouter

from notifications.views import NotificationCityViewSet, PushDispatchViewSet

router = DefaultRouter()
router.register('notifications/cities', NotificationCityViewSet, basename='notifications-cities')
router.register('notifications/push-dispatch', PushDispatchViewSet, basename='notifications-push-dispatch')

urlpatterns = router.urls
