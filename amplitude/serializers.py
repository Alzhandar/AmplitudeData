from rest_framework import serializers

from .models import DailyDeviceActivity


class DailyDeviceActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyDeviceActivity
        fields = (
            'date',
            'user_id',
            'device_id',
            'phone_number',
            'platform',
            'visits_count',
            'visit_times',
            'first_seen',
            'last_seen',
        )
