from datetime import datetime

from django.utils import timezone
from rest_framework import viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from .models import DailyDeviceActivity
from .services.location_presence_service import LocationPresenceAnalyticsService
from .serializers import DailyDeviceActivitySerializer


class DailyDeviceActivityViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DailyDeviceActivitySerializer

    def get_queryset(self):
        date_value = self.request.query_params.get('date') or timezone.localdate().isoformat()
        return DailyDeviceActivity.objects.filter(date=date_value).order_by('-last_seen')


class LocationPresenceStatsViewSet(viewsets.ViewSet):
    def list(self, request):
        today = timezone.localdate().isoformat()
        raw_start = request.query_params.get('start_date') or request.query_params.get('date') or today
        raw_end = request.query_params.get('end_date') or raw_start
        raw_window_hours = request.query_params.get('window_hours') or '24'

        try:
            start_date = datetime.strptime(raw_start, '%Y-%m-%d').date()
        except ValueError as exc:
            raise ValidationError({'start_date': 'Use YYYY-MM-DD format'}) from exc

        try:
            end_date = datetime.strptime(raw_end, '%Y-%m-%d').date()
        except ValueError as exc:
            raise ValidationError({'end_date': 'Use YYYY-MM-DD format'}) from exc

        try:
            window_hours = int(raw_window_hours)
        except ValueError as exc:
            raise ValidationError({'window_hours': 'Must be integer'}) from exc

        service = LocationPresenceAnalyticsService()
        try:
            result = service.calculate(start_date=start_date, end_date=end_date, window_hours=window_hours)
        except ValueError as exc:
            raise ValidationError({'detail': str(exc)}) from exc

        return Response(result)
