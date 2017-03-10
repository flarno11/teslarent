import datetime
import uuid

from django.utils import timezone
from django.test import TestCase
import requests_mock

from teslarent.management.commands import rental_start_end
from teslarent.models import *
from teslarent.tests.tests_rental_update_start_end import RentalStartEndTestCase
from teslarent.tests.tests_teslaapi import CURRENT_VEHICLE_ID, VEHICLE_STATE_RESPONSE


class RentalGetNextCase(TestCase):

    def setUp(self):
        pass

    def test_start_end_in_future(self):
        RentalStartEndTestCase.create_credentials()
        RentalStartEndTestCase.create_vehicle()

        now = timezone.now()
        start = now + datetime.timedelta(days=1)
        end = now + datetime.timedelta(days=2)
        RentalStartEndTestCase.create_rental(start=start, end=end)

        next_rental_at = Rental.get_next_rental_start_or_end_time(now)
        self.assertEqual(start, next_rental_at)

    def test_start_in_past_end_in_future(self):
        RentalStartEndTestCase.create_credentials()
        RentalStartEndTestCase.create_vehicle()

        now = timezone.now()
        start = now - datetime.timedelta(days=1)
        end = now + datetime.timedelta(days=1)
        RentalStartEndTestCase.create_rental(start=start, end=end)

        next_rental_at = Rental.get_next_rental_start_or_end_time(now)
        self.assertEqual(end, next_rental_at)

    def test_start_end_in_past(self):
        RentalStartEndTestCase.create_credentials()
        RentalStartEndTestCase.create_vehicle()

        now = timezone.now()
        start = now - datetime.timedelta(days=2)
        end = now - datetime.timedelta(days=1)
        RentalStartEndTestCase.create_rental(start=start, end=end)

        next_rental_at = Rental.get_next_rental_start_or_end_time(now)
        self.assertIsNone(next_rental_at)
