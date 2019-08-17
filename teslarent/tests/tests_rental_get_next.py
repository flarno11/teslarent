import datetime

from django.test import TestCase

from teslarent.models import *
from teslarent.tests.tests_teslaapi import TeslaApiTestCase


class RentalGetNextCase(TestCase):
    def setUp(self):
        pass

    def test_start_end_in_future(self):
        TeslaApiTestCase.create_credentials()
        TeslaApiTestCase.create_vehicle_default()

        now = timezone.now()
        start = now + datetime.timedelta(days=1)
        end = now + datetime.timedelta(days=2)
        TeslaApiTestCase.create_rental(start=start, end=end)

        next_rental_at = Rental.get_next_rental_start_or_end_time(now)
        self.assertEqual(start, next_rental_at)

    def test_start_in_past_end_in_future(self):
        TeslaApiTestCase.create_credentials()
        TeslaApiTestCase.create_vehicle_default()

        now = timezone.now()
        start = now - datetime.timedelta(days=1)
        end = now + datetime.timedelta(days=1)
        TeslaApiTestCase.create_rental(start=start, end=end)

        next_rental_at = Rental.get_next_rental_start_or_end_time(now)
        self.assertEqual(end, next_rental_at)

    def test_start_end_in_past(self):
        TeslaApiTestCase.create_credentials()
        TeslaApiTestCase.create_vehicle_default()

        now = timezone.now()
        start = now - datetime.timedelta(days=2)
        end = now - datetime.timedelta(days=1)
        TeslaApiTestCase.create_rental(start=start, end=end)

        next_rental_at = Rental.get_next_rental_start_or_end_time(now)
        self.assertIsNone(next_rental_at)
