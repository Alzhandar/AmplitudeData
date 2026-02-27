from rest_framework import serializers

from .models import DailyDeviceActivity


class DailyDeviceActivitySerializer(serializers.ModelSerializer):
    visit_times = serializers.SerializerMethodField()

    class Meta:
        model = DailyDeviceActivity
        fields = (
            'date',
            'user_id',
            'device_id',
            'phone_number',
            'platform',
            'device_brand',
            'device_manufacturer',
            'device_model',
            'visits_count',
            'visit_times',
            'first_seen',
            'last_seen',
        )

    def get_visit_times(self, obj):
        return [
            visit_time.isoformat()
            for visit_time in obj.visit_records.order_by('event_time').values_list('event_time', flat=True)
        ]
