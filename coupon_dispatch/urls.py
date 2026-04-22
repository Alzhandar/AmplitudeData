from rest_framework.routers import DefaultRouter

from coupon_dispatch.views import CouponDispatchJobViewSet, CouponDispatchMarketingSaleViewSet

router = DefaultRouter()
router.register('coupon-dispatch/marketing-sales', CouponDispatchMarketingSaleViewSet, basename='coupon-dispatch-marketing-sales')
router.register('coupon-dispatch/jobs', CouponDispatchJobViewSet, basename='coupon-dispatch-jobs')

urlpatterns = router.urls
