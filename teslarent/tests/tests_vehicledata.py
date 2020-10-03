import json

from django.test import TestCase

from teslarent.models import *
from teslarent.tests.tests_teslaapi import CURRENT_VEHICLE_ID, VEHICLE_DATA_RESPONSE, TeslaApiTestCase


class VehicleDataTestCase(TestCase):

    def setUp(self):
        pass


    @staticmethod
    def create_vehicle_data(vehicle, battery_level=None):
        v = VehicleData()
        v.vehicle = vehicle
        v.data = json.loads(VEHICLE_DATA_RESPONSE)['response']

        if battery_level:
            v.data['charge_state']['battery_level'] = battery_level

        v.save()
        return v

    def test_query(self):
        TeslaApiTestCase.create_credentials()
        vehicle = TeslaApiTestCase.create_vehicle_default()

        self.create_vehicle_data(vehicle, battery_level=64)
        self.create_vehicle_data(vehicle, battery_level=65)
        data = VehicleData.objects.filter(vehicle=vehicle)
        print(data[0].data)
        self.assertEqual(2, len(list(data)))

        self.assertEqual(2, len(list(VehicleData.objects.filter(data__state='online'))))

        self.assertEqual(2, len(list(VehicleData.objects.filter(data__charge_state__battery_level__gte=64))))
        self.assertEqual(1, len(list(VehicleData.objects.filter(data__charge_state__battery_level__gte=65))))
        self.assertEqual(0, len(list(VehicleData.objects.filter(data__charge_state__battery_level__gte=66))))
