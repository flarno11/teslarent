import datetime
import uuid

from django.utils import timezone
from django.test import TestCase
import requests_mock

from teslarent.management.commands import rental_start_end
from teslarent.models import *
from teslarent.tests.tests_teslaapi import CURRENT_VEHICLE_ID, VEHICLE_STATE_RESPONSE


class RentalStartEndTestCase(TestCase):

    def setUp(self):
        pass

    @staticmethod
    def create_credentials():
        c = Credentials(email="test@test.com")
        c.current_token = "1234"
        c.refresh_token = "5678"
        c.token_expires_at = timezone.now() + datetime.timedelta(days=10)
        c.save()
        return c

    @staticmethod
    def create_vehicle():
        v = Vehicle()
        v.id = CURRENT_VEHICLE_ID
        v.vehicle_id = CURRENT_VEHICLE_ID * 10
        v.display_name = ""
        v.credentials = Credentials.objects.all()[0]
        v.linked = True
        v.mobile_enabled = True
        v.save()
        return v

    @staticmethod
    def create_rental(start, end):
        r = Rental(start=start, end=end, code=(uuid.uuid4()))
        r.vehicle = Vehicle.objects.get(id=CURRENT_VEHICLE_ID)
        r.save()
        return r

    def test_update_start(self):
        self.create_credentials()
        self.create_vehicle()

        start = timezone.now()
        end = timezone.now() + datetime.timedelta(days=1)
        self.create_rental(start=start, end=end)

        r = Rental.objects.all()[0]
        self.assertIsNone(r.odometer_start)
        self.assertIsNone(r.odometer_start_updated_at)
        self.assertIsNone(r.odometer_end)
        self.assertIsNone(r.odometer_end_updated_at)

        with requests_mock.mock() as m:
            m.get('/api/1/vehicles/' + str(CURRENT_VEHICLE_ID) + '/data_request/vehicle_state', text=VEHICLE_STATE_RESPONSE)

            rental_start_end.Command().update_rentals(start)
            r = Rental.objects.all()[0]
            self.assertEquals(25000, r.odometer_start)
            self.assertEquals(start, r.odometer_start_updated_at)
            self.assertIsNone(r.odometer_end)
            self.assertIsNone(r.odometer_end_updated_at)

            rental_start_end.Command().update_rentals(end)
            r = Rental.objects.all()[0]
            self.assertEquals(25000, r.odometer_start)
            self.assertEquals(25000, r.odometer_end)
            self.assertEquals(start, r.odometer_start_updated_at)
            self.assertEquals(end, r.odometer_end_updated_at)
            self.assertEquals(0, r.distance_driven)
