import uuid
import json
import logging
from datetime import datetime

from django.contrib import admin
from django.forms import widgets
from django.utils.safestring import mark_safe

from teslarent.models import Credentials, Rental, Vehicle, VehicleData

logger = logging.getLogger(__name__)


class PrettyJSONWidget(widgets.Textarea):
    def format_value(self, value):
        try:
            value = json.dumps(json.loads(value), indent=4)  #, sort_keys=True
            # these lines will try to adjust size of TextArea to fit to content
            row_lengths = [len(r) for r in value.split('\n')]
            self.attrs['rows'] = min(max(len(row_lengths) + 2, 10), 30)
            self.attrs['cols'] = min(max(max(row_lengths) + 2, 40), 120)
            return value
        except Exception as e:
            logger.warning("Error while formatting JSON: {}".format(e))
            return super(PrettyJSONWidget, self).format_value(value)


@admin.register(Credentials)
class CredentialsAdmin(admin.ModelAdmin):
    list_display = ('email', 'current_token', 'refresh_token', 'token_expires_at', 'salt', 'iv', 'created_at', 'updated_at', )


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ('linked', 'id', 'vehicle_id', 'credentials', 'display_name', 'color', 'vin', 'state', 'created_at', 'updated_at', )
    readonly_fields = list_display

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return True

    def has_change_permission(self, request, obj=None):
        return True


@admin.register(Rental)
class RentalAdmin(admin.ModelAdmin):
    list_display = ('vehicle', 'start', 'end', 'code', 'odometer_start', 'odometer_end', 'created_at', 'updated_at', )
    list_filter = ('start',)
    #readonly_fields = ('odometer_start', 'odometer_end', )
    ordering = ('start', 'end',)

    def get_form(self, request, obj=None, **kwargs):
        form = super(RentalAdmin, self).get_form(request, obj, **kwargs)
        form.base_fields['code'].initial = str(uuid.uuid4())

        if len(Vehicle.objects.all()) == 1:
            form.base_fields['vehicle'].initial = Vehicle.objects.all()[0]

        return form


@admin.register(VehicleData)
class VehicleDataAdmin(admin.ModelAdmin):
    list_display = ('created_at',
                    'vehicle',
                    'state',
                    'vehicle_state__timestamp_fmt',
                    'vehicle_state__timestamp',
                    'vehicle_state__odometer',
                    'vehicle_state__locked',
                    'vehicle_state__valet_mode',
                    'vehicle_state__software_update__status',
                    'drive_state__power',
                    'drive_state__speed',
                    'drive_state__gps_as_of_fmt',
                    'drive_state__gps_as_of',
                    'drive_state__latitude',
                    'drive_state__longitude',
                    'drive_state__heading',
                    'charge_state__battery_level',
                    'charge_state__usable_battery_level',
                    'charge_state__battery_range',
                    'charge_state__est_battery_range',
                    'charge_state__charge_rate',
                    'charge_state__charger_power',
                    'charge_state__charger_voltage',
                    'charge_state__charging_state',
                    'charge_state__battery_heater_on',
                    'climate_state__inside_temp',
                    'climate_state__outside_temp',
                    'climate_state__battery_heater',
                    'climate_state__driver_temp_setting',
                    'climate_state__passenger_temp_setting',
                    'climate_state__fan_status',
                    'climate_state__is_climate_on',
                    'climate_state__is_preconditioning',
                    'climate_state__is_auto_conditioning_on',
                    )

    exclude = ('data',)
    readonly_fields = ('data_fmt', ) + list_display

    def data_fmt(self, obj):
        return mark_safe('<pre>' + json.dumps(obj.data, indent=4) + '</pre>')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return True

    def has_change_permission(self, request, obj=None):
        return False
