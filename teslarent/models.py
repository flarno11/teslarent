import os

import datetime

from django.conf import settings
from django.utils import timezone
from django.db import models
from django.db.models import Q
from django.contrib.postgres.fields import JSONField

from teslarent.utils.crypt import encrypt


class Credentials(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    email = models.EmailField(max_length=200, unique=True)
    salt = models.CharField(max_length=16, verbose_name="Salt for KDF from secret to encryption key")
    iv = models.CharField(max_length=32, verbose_name="Initialization Vector for token encryption")
    current_token = models.CharField(max_length=512)  # currently the tokens seem to be 160 hex bytes (encrypted) long
    refresh_token = models.CharField(max_length=512)  # currently the tokens seem to be 160 hex bytes (encrypted) long
    token_expires_at = models.DateTimeField()

    class Meta:
        verbose_name_plural = "Credentials"

    def __str__(self):
        return self.email

    def update_token(self, access_token, refresh_token, expires_in):
        self.salt = os.urandom(8).hex()  # 64-bit salt
        self.iv = os.urandom(16).hex()   # 128-bit IV
        self.current_token = encrypt(access_token, settings.SECRET_KEY, self.salt, self.iv)
        self.refresh_token = encrypt(refresh_token, settings.SECRET_KEY, self.salt, self.iv)
        self.token_expires_at = timezone.now() + datetime.timedelta(seconds=expires_in)


class Vehicle(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    linked = models.BooleanField('False if the credentials were removed or the vehicle is not listed anymore')
    id = models.BigIntegerField(primary_key=True)
    vehicle_id = models.BigIntegerField()
    credentials = models.ForeignKey(Credentials, on_delete=models.SET_NULL, default=None, blank=True, null=True,)
    display_name = models.CharField(max_length=200)
    color = models.CharField(max_length=200)
    vin = models.CharField(max_length=17)
    state = models.CharField(max_length=200)
    mobile_enabled = models.BooleanField(null=True)

    @property
    def is_active(self):
        return self.linked and self.credentials is not None and self.mobile_enabled

    def __str__(self):
        return self.display_name + ' ' + self.vin + ' (' + str(self.credentials) + ')'

    @staticmethod
    def get_all_active_vehicles():
        return Vehicle.objects.filter(linked=True, credentials__isnull=False)


class Rental(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE)
    start = models.DateTimeField()
    end = models.DateTimeField()
    description = models.TextField(default=None, blank=True, null=True)
    code = models.UUIDField(unique=True)
    odometer_start = models.IntegerField(default=None, blank=True, null=True)
    odometer_start_updated_at = models.DateTimeField(default=None, blank=True, null=True)
    odometer_end = models.IntegerField(default=None, blank=True, null=True)
    odometer_end_updated_at = models.DateTimeField(default=None, blank=True, null=True)

    @property
    def is_active(self):
        return self.start <= timezone.now() < self.end and self.vehicle.is_active

    @property
    def distance_driven(self):
        return self.odometer_end - self.odometer_start

    @staticmethod
    def get_next_rental_start_or_end_time(date):
        rentals = list(Rental.objects.filter(Q(start__gt=date) | Q(end__gt=date)).order_by('start', 'end')[:1])
        if len(rentals) == 0:
            return None
        rental = rentals[0]
        if rental.start > date:
            return rental.start
        else:
            return rental.end


class VehicleData(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE)
    data = JSONField()

    @property
    def is_km(self):
        return self.data['gui_settings']['gui_distance_units'] == 'km/hr' if 'gui_settings' in self.data else None
    @property
    def factor_mi_to_km(self):
        return 1.609344 if self.is_km else 1.0

    @property
    def state(self):
        return self.data['state']

    @property
    def is_online(self):
        return self.state == 'online'

    @property
    def is_offline(self):
        return self.state == 'offline'

    @property
    def battery_soc_kwh(self):
        # 285.63km added battery range corresponds to 41.713kWh charged, 41.713/285.63 = 0.146038581381508
        # 255.87km added battery range corresponds to 37.255kWh charged, 37.255/255.87 = 0.145601281900965
        # 254.85km added battery range corresponds to 39.351kWh charged, 39.351/254.85 = 0.154408475573867
        return self.charge_state__battery_range * 0.146


    @property
    def vehicle_state__timestamp(self):
        return self.data['vehicle_state']['timestamp'] if 'vehicle_state' in self.data else None
    @property
    def vehicle_state__timestamp_fmt(self):
        return datetime.datetime.utcfromtimestamp(int(self.data['vehicle_state']['timestamp'] / 1000)).replace(tzinfo=timezone.utc) if 'vehicle_state' in self.data else None
    @property
    def vehicle_state__odometer(self):
        return self.data['vehicle_state']['odometer']*self.factor_mi_to_km if 'vehicle_state' in self.data else None
    @property
    def vehicle_state__locked(self):
        return self.data['vehicle_state']['locked'] if 'vehicle_state' in self.data else None
    @property
    def vehicle_state__valet_mode(self):
        return self.data['vehicle_state']['valet_mode'] if 'vehicle_state' in self.data else None
    @property
    def vehicle_state__software_update__status(self):
        return self.data['vehicle_state']['software_update']['status'] if 'vehicle_state' in self.data else None

    @property
    def drive_state__power(self):
        return self.data['drive_state']['power'] if 'drive_state' in self.data else None
    @property
    def drive_state__speed(self):
        if 'drive_state' in self.data and self.data['drive_state']['speed']:
            return self.data['drive_state']['speed']*self.factor_mi_to_km
    @property
    def drive_state__gps_as_of(self):
        return self.data['drive_state']['gps_as_of'] if 'drive_state' in self.data else None
    @property
    def drive_state__gps_as_of_fmt(self):
        return datetime.datetime.utcfromtimestamp(self.data['drive_state']['gps_as_of']).replace(tzinfo=timezone.utc) if 'drive_state' in self.data else None
    @property
    def drive_state__latitude(self):
        return self.data['drive_state']['latitude'] if 'drive_state' in self.data else None
    @property
    def drive_state__longitude(self):
        return self.data['drive_state']['longitude'] if 'drive_state' in self.data else None
    @property
    def drive_state__heading(self):
        return self.data['drive_state']['heading'] if 'drive_state' in self.data else None

    @property
    def charge_state__battery_level(self):
        return self.data['charge_state']['battery_level'] if 'charge_state' in self.data else None
    @property
    def charge_state__usable_battery_level(self):
        return self.data['charge_state']['usable_battery_level'] if 'charge_state' in self.data else None
    @property
    def charge_state__battery_range(self):
        return self.data['charge_state']['battery_range']*self.factor_mi_to_km if 'charge_state' in self.data else None
    @property
    def charge_state__est_battery_range(self):
        return self.data['charge_state']['est_battery_range']*self.factor_mi_to_km if 'charge_state' in self.data else None
    @property
    def charge_state__ideal_battery_range(self):
        return self.data['charge_state']['ideal_battery_range']*self.factor_mi_to_km if 'charge_state' in self.data else None
    @property
    def charge_state__battery_heater_on(self):
        return self.data['charge_state']['battery_heater_on'] if 'charge_state' in self.data else None
    @property
    def charge_state__charge_rate(self):
        return self.data['charge_state']['charge_rate'] if 'charge_state' in self.data else None
    @property
    def charge_state__charger_power(self):
        return self.data['charge_state']['charger_power'] if 'charge_state' in self.data else None
    @property
    def charge_state__charger_voltage(self):
        return self.data['charge_state']['charger_voltage'] if 'charge_state' in self.data else None
    @property
    def charge_state__charging_state(self):
        return self.data['charge_state']['charging_state'] if 'charge_state' in self.data else None
    @property
    def charge_state__time_to_full_charge(self):
        return self.data['charge_state']['time_to_full_charge'] if 'charge_state' in self.data else None

    @property
    def climate_state__inside_temp(self):
        return self.data['climate_state']['inside_temp'] if 'climate_state' in self.data else None
    @property
    def climate_state__outside_temp(self):
        return self.data['climate_state']['outside_temp'] if 'climate_state' in self.data else None
    @property
    def climate_state__battery_heater(self):
        return self.data['climate_state']['battery_heater'] if 'climate_state' in self.data else None
    @property
    def climate_state__driver_temp_setting(self):
        return self.data['climate_state']['driver_temp_setting'] if 'climate_state' in self.data else None
    @property
    def climate_state__passenger_temp_setting(self):
        return self.data['climate_state']['passenger_temp_setting'] if 'climate_state' in self.data else None
    @property
    def climate_state__fan_status(self):
        return self.data['climate_state']['fan_status'] if 'climate_state' in self.data else None
    @property
    def climate_state__is_climate_on(self):
        return self.data['climate_state']['is_climate_on'] if 'climate_state' in self.data else None
    @property
    def climate_state__is_preconditioning(self):
        return self.data['climate_state']['is_preconditioning'] if 'climate_state' in self.data else None
    @property
    def climate_state__is_auto_conditioning_on(self):
        return self.data['climate_state']['is_auto_conditioning_on'] if 'climate_state' in self.data else None
