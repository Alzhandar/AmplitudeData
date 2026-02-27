from django.utils import timezone
from rest_framework import viewsets

from .models import DailyDeviceActivity
from .serializers import DailyDeviceActivitySerializer


class DailyDeviceActivityViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DailyDeviceActivitySerializer

    def get_queryset(self):
        date_value = self.request.query_params.get('date') or timezone.localdate().isoformat()
        return DailyDeviceActivity.objects.filter(date=date_value).order_by('-last_seen')
