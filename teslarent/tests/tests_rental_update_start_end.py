import datetime
import uuid

from django.utils import timezone
from django.test import TestCase
import requests_mock

from teslarent.management.commands import rental_start_end
from teslarent.models import *
from teslarent.tests.tests_teslaapi import CURRENT_VEHICLE_ID, VEHICLE_DATA_RESPONSE, TeslaApiTestCase


class RentalStartEndTestCase(TestCase):
    def setUp(self):
        pass

    def test_update_start(self):
        TeslaApiTestCase.create_credentials()
        TeslaApiTestCase.create_vehicle_default()

        start = timezone.now()
        end = timezone.now() + datetime.timedelta(days=1)
        TeslaApiTestCase.create_rental(start=start, end=end)

        r = Rental.objects.all()[0]
        self.assertIsNone(r.odometer_start)
        self.assertIsNone(r.odometer_start_updated_at)
        self.assertIsNone(r.odometer_end)
        self.assertIsNone(r.odometer_end_updated_at)

        with requests_mock.mock() as m:
            m.get('/api/1/vehicles/' + str(CURRENT_VEHICLE_ID) + '/vehicle_data', text=VEHICLE_DATA_RESPONSE)

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
