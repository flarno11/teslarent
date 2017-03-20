import os

import datetime

from django.conf import settings
from django.utils import timezone
from django.db import models
from django.db.models import Q

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
    mobile_enabled = models.BooleanField()

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
    vehicle = models.ForeignKey(Vehicle)
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
