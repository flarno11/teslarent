import datetime

from django.utils import timezone
from django.test import TestCase
import requests_mock

from teslarent.teslaapi.teslaapi import *


LOGIN_RESPONSE = '{"access_token": "abc1234", "token_type": "bearer", "expires_in": 7776000, "created_at": 1457385291, "refresh_token": "cba321"}'
LIST_VEHICLES_RESPONSE = '{"response":[{"color": "white", "display_name": null, "id": 321, "option_codes": "MS01,RENA,TM00,DRLH,PF00,BT85,PBCW,RFPO,WT19,IBMB,IDPB,TR00,SU01,SC01,TP01,AU01,CH00,HP00,PA00,PS00,AD02,X020,X025,X001,X003,X007,X011,X013", "user_id": 123, "vehicle_id": 1234567890, "vin": "5YJSA1CN5CFP01657", "tokens": ["x", "x"], "state": "online"}]}'
VEHICLE_STATE_RESPONSE = '{"response":{"locked": true, "odometer": 25000}}'
MOBILE_ENABLED_RESPONSE = '{"response": true}'
OLD_VEHICLE_ID = 10001
CURRENT_VEHICLE_ID = 321


class TeslaApiTestCase(TestCase):

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
    def create_vehicle(vehicle_id, display_name, credentials):
        v = Vehicle()
        v.id = vehicle_id
        v.vehicle_id = vehicle_id * 10
        v.display_name = display_name
        v.credentials = credentials
        v.linked = True
        v.mobile_enabled = True
        v.save()
        return v

    def test_login(self):
        c = Credentials(email="test@test.com")

        with requests_mock.mock() as m:
            m.post('/oauth/token', text=LOGIN_RESPONSE)
            login_and_save_credentials(c, password="test")

        self.assertGreater(c.token_expires_at, timezone.now() + datetime.timedelta(days=89))
        self.assertLess(c.token_expires_at, timezone.now() + datetime.timedelta(days=91))

    def test_update_vehicle_initial(self):
        self.create_credentials()

        self.assertEquals(0, len(list(Vehicle.objects.all())))

        with requests_mock.mock() as m:
            m.post('/oauth/token', text=LOGIN_RESPONSE)
            m.get('/api/1/vehicles', text=LIST_VEHICLES_RESPONSE)
            m.get('/api/1/vehicles/' + str(CURRENT_VEHICLE_ID) + '/mobile_enabled', text=MOBILE_ENABLED_RESPONSE)
            update_all_vehicles()

        self.assertEquals(1, len(list(Vehicle.objects.all())))

    def test_update_vehicle_remove(self):
        c = self.create_credentials()

        self.assertEquals(0, len(list(Vehicle.objects.all())))
        self.create_vehicle(vehicle_id=OLD_VEHICLE_ID, display_name="old", credentials=c)
        self.assertEquals(1, len(list(Vehicle.objects.all())))

        with requests_mock.mock() as m:
            m.post('/oauth/token', text=LOGIN_RESPONSE)
            m.get('/api/1/vehicles', text=LIST_VEHICLES_RESPONSE)
            m.get('/api/1/vehicles/' + str(CURRENT_VEHICLE_ID) + '/mobile_enabled', text=MOBILE_ENABLED_RESPONSE)
            update_all_vehicles()

        self.assertEquals(2, len(list(Vehicle.objects.all())))

        self.assertFalse(Vehicle.objects.get(display_name="old").linked)
        self.assertTrue(Vehicle.objects.get(color="white").linked)

    def test_update_vehicle_update(self):
        c = self.create_credentials()

        self.assertEquals(0, len(list(Vehicle.objects.all())))
        self.create_vehicle(vehicle_id=CURRENT_VEHICLE_ID, display_name="old", credentials=c)

        vehicles = list(Vehicle.objects.all())
        self.assertEquals(1, len(vehicles))

        created_at = vehicles[0].created_at

        with requests_mock.mock() as m:
            m.post('/oauth/token', text=LOGIN_RESPONSE)
            m.get('/api/1/vehicles', text=LIST_VEHICLES_RESPONSE)
            m.get('/api/1/vehicles/' + str(CURRENT_VEHICLE_ID) + '/mobile_enabled', text=MOBILE_ENABLED_RESPONSE)
            login_and_save_credentials(c, password="test")
            update_all_vehicles()

        vehicles = list(Vehicle.objects.all())
        self.assertEquals(1, len(vehicles))
        self.assertEquals(created_at, vehicles[0].created_at)

