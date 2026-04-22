from rest_framework import serializers

from .models import CouponDispatchJob, CouponDispatchJobResult


class MarketingSaleOptionSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    available_coupons = serializers.IntegerField()


class CouponDispatchJobCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    marketing_sale_id = serializers.IntegerField(min_value=1)
    marketing_sale_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    phones_text = serializers.CharField(required=False, allow_blank=True)
    excel_file = serializers.FileField(required=False, allow_null=True)

    def validate(self, attrs):
        phones_text = str(attrs.get('phones_text') or '').strip()
        excel_file = attrs.get('excel_file')

        if not phones_text and not excel_file:
            raise serializers.ValidationError('Provide manual phone numbers or Excel file')

        if excel_file is not None:
            filename = str(getattr(excel_file, 'name', '')).lower()
            if filename and not filename.endswith(('.xlsx', '.xlsm', '.xltx', '.xltm')):
                raise serializers.ValidationError('Excel file must be .xlsx/.xlsm/.xltx/.xltm')

        return attrs


class CouponDispatchJobResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = CouponDispatchJobResult
        fields = (
            'id',
            'phone_raw',
            'phone_normalized',
            'guest_id',
            'coupon_id',
            'coupon_code',
            'success',
            'error_message',
            'created_at',
        )


class CouponDispatchJobListSerializer(serializers.ModelSerializer):
    initiated_by_email = serializers.SerializerMethodField()

    class Meta:
        model = CouponDispatchJob
        fields = (
            'id',
            'title',
            'marketing_sale_id',
            'marketing_sale_name',
            'input_source',
            'status',
            'total_phones',
            'unique_phones',
            'guests_found',
            'available_coupons',
            'coupons_assigned',
            'errors_count',
            'mobile_api_sent',
            'mobile_api_sent_at',
            'started_at',
            'finished_at',
            'initiated_by_email',
            'created_at',
            'updated_at',
        )

    def get_initiated_by_email(self, obj):
        user = obj.initiated_by
        if user is None:
            return ''
        return str(user.email or '').strip().lower()


class CouponDispatchJobDetailSerializer(CouponDispatchJobListSerializer):
    results = CouponDispatchJobResultSerializer(many=True, read_only=True)

    class Meta(CouponDispatchJobListSerializer.Meta):
        fields = CouponDispatchJobListSerializer.Meta.fields + (
            'error_log',
            'mobile_api_response',
            'results',
        )
