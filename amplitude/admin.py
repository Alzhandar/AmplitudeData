from django.contrib import admin

from .models import AmplitudeSyncSchedule, DailyDeviceActivity, MobileSession

admin.site.site_header = 'Панель администратора'
admin.site.site_title = 'Админка'
admin.site.index_title = 'Управление системой'


@admin.register(MobileSession)
class MobileSessionAdmin(admin.ModelAdmin):
    list_display = (
        'event_time',
        'event_type',
        'user_id',
        'device_id',
        'phone_number',
        'platform',
        'device_brand',
        'device_manufacturer',
        'device_model',
    )
    list_filter = ('date', 'platform', 'event_type')
    search_fields = ('user_id', 'device_id', 'phone_number', 'insert_id', 'device_brand', 'device_model')


@admin.register(DailyDeviceActivity)
class DailyDeviceActivityAdmin(admin.ModelAdmin):
    list_display = (
        'date',
        'device_id',
        'phone_number',
        'platform',
        'device_brand',
        'device_manufacturer',
        'device_model',
        'visits_count',
        'first_seen',
        'last_seen',
    )
    list_filter = ('date', 'platform')
    search_fields = ('user_id', 'device_id', 'phone_number', 'device_brand', 'device_model')


@admin.register(AmplitudeSyncSchedule)
class AmplitudeSyncScheduleAdmin(admin.ModelAdmin):
    list_display = ('run_at', 'enabled', 'last_run_on', 'updated_at')
    fields = ('run_at', 'enabled', 'last_run_on')
    readonly_fields = ('last_run_on',)

    def has_add_permission(self, request):
        return not AmplitudeSyncSchedule.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
