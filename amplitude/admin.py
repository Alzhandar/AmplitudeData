from django.contrib import admin

from .common import AmplitudeEventTranslations
from .models import AmplitudeSyncSchedule, DailyDeviceActivity, MobileSession

admin.site.site_header = 'Панель администратора'
admin.site.site_title = 'Админка'
admin.site.index_title = 'Управление системой'


class HasDeviceFilter(admin.SimpleListFilter):
    title = 'Есть устройство'
    parameter_name = 'has_device'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Да'),
            ('no', 'Нет'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.exclude(device_id='')
        if self.value() == 'no':
            return queryset.filter(device_id='')
        return queryset


class HasUserFilter(admin.SimpleListFilter):
    title = 'Есть пользователь'
    parameter_name = 'has_user'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Да'),
            ('no', 'Нет'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.exclude(user_id='')
        if self.value() == 'no':
            return queryset.filter(user_id='')
        return queryset


class HasEventTypeFilter(admin.SimpleListFilter):
    title = 'Есть событие'
    parameter_name = 'has_event_type'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Да'),
            ('no', 'Нет'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.exclude(event_type='')
        if self.value() == 'no':
            return queryset.filter(event_type='')
        return queryset


class EventTypeRuFilter(admin.SimpleListFilter):
    title = 'Тип события'
    parameter_name = 'event_type_ru'

    def lookups(self, request, model_admin):
        raw_event_types = (
            model_admin.get_queryset(request)
            .exclude(event_type='')
            .order_by()
            .values_list('event_type', flat=True)
            .distinct()
        )

        deduped = {}
        for event_type in raw_event_types:
            normalized = (event_type or '').strip()
            if not normalized:
                continue
            deduped.setdefault(normalized, normalized)

        sorted_events = sorted(
            deduped.keys(),
            key=lambda name: AmplitudeEventTranslations.translate(name).lower(),
        )

        return [
            (event_type, AmplitudeEventTranslations.translate(event_type))
            for event_type in sorted_events
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(event_type=self.value())
        return queryset


@admin.register(MobileSession)
class MobileSessionAdmin(admin.ModelAdmin):
    list_display = (
        'event_time',
        'event_type',
        'event_type_ru',
        'user_id',
        'device_id',
        'phone_number',
        'platform',
        'device_brand',
        'device_manufacturer',
        'device_model',
    )
    list_filter = ('date', 'platform', EventTypeRuFilter, HasEventTypeFilter, HasDeviceFilter, HasUserFilter)
    search_fields = ('user_id', 'device_id', 'phone_number', 'insert_id', 'device_brand', 'device_model')

    @admin.display(description='Событие (рус.)')
    def event_type_ru(self, obj):
        return AmplitudeEventTranslations.translate(obj.event_type)


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
    list_filter = ('date', 'platform', HasDeviceFilter, HasUserFilter)
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
