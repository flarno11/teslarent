import datetime
import uuid

from django.test import TestCase
import requests_mock

from teslarent.models import Rental
from teslarent.teslaapi.teslaapi import *


LOGIN_RESPONSE = '{"access_token": "abc1234", "token_type": "bearer", "expires_in": 7776000, "created_at": 1457385291, "refresh_token": "cba321"}'
LIST_VEHICLES_RESPONSE = '{"response":[{"color": "", "display_name": null, "id": 321, "option_codes": "MS01,RENA,TM00,DRLH,PF00,BT85,PBCW,RFPO,WT19,IBMB,IDPB,TR00,SU01,SC01,TP01,AU01,CH00,HP00,PA00,PS00,AD02,X020,X025,X001,X003,X007,X011,X013", "user_id": 123, "vehicle_id": 3210, "vin": "5YJSA1CN5CFP01657", "tokens": ["x", "x"], "state": "online"}]}'
VEHICLE_STATE_RESPONSE = '{"response":{"locked": true, "odometer": 25000}}'
VEHICLE_DATA_RESPONSE = '{"response":{"id":12345678901234567,"user_id":123,"vehicle_id":1234567890,"vin":"5YJSA11111111111","display_name":"Nikola2.0","option_codes":"MDLS,RENA,AF02,APF1,APH2,APPB,AU01,BC0R,BP00,BR00,BS00,CDM0,CH05,PBCW,CW00,DCF0,DRLH,DSH7,DV4W,FG02,FR04,HP00,IDBA,IX01,LP01,ME02,MI01,PF01,PI01,PK00,PS01,PX00,PX4D,QTVB,RFP2,SC01,SP00,SR01,SU01,TM00,TP03,TR00,UTAB,WTAS,X001,X003,X007,X011,X013,X021,X024,X027,X028,X031,X037,X040,X044,YFFC,COUS","color":null,"tokens":["abcdef1234567890","1234567890abcdef"],"state":"online","in_service":false,"id_s":"12345678901234567","calendar_enabled":true,"api_version":4,"backseat_token":null,"backseat_token_updated_at":null,"drive_state":{"gps_as_of":1538363883,"heading":5,"latitude":33.111111,"longitude":-88.111111,"native_latitude":33.111111,"native_location_supported":1,"native_longitude":-88.111111,"native_type":"wgs","power":0,"shift_state":null,"speed":null,"timestamp":1538364666096},"climate_state":{"battery_heater":false,"battery_heater_no_power":false,"driver_temp_setting":21.6,"fan_status":0,"inside_temp":null,"is_auto_conditioning_on":null,"is_climate_on":false,"is_front_defroster_on":false,"is_preconditioning":false,"is_rear_defroster_on":false,"left_temp_direction":null,"max_avail_temp":28.0,"min_avail_temp":15.0,"outside_temp":null,"passenger_temp_setting":21.6,"right_temp_direction":null,"seat_heater_left":false,"seat_heater_rear_center":false,"seat_heater_rear_left":false,"seat_heater_rear_left_back":0,"seat_heater_rear_right":false,"seat_heater_rear_right_back":0,"seat_heater_right":false,"side_mirror_heaters":false,"smart_preconditioning":false,"steering_wheel_heater":false,"timestamp":1543186971731,"wiper_blade_heater":false},"charge_state":{"battery_heater_on":false,"battery_level":64,"battery_range":167.96,"charge_current_request":48,"charge_current_request_max":48,"charge_enable_request":true,"charge_energy_added":12.41,"charge_limit_soc":90,"charge_limit_soc_max":100,"charge_limit_soc_min":50,"charge_limit_soc_std":90,"charge_miles_added_ideal":50.0,"charge_miles_added_rated":40.0,"charge_port_door_open":false,"charge_port_latch":"Engaged","charge_rate":0.0,"charge_to_max_range":false,"charger_actual_current":0,"charger_phases":null,"charger_pilot_current":48,"charger_power":0,"charger_voltage":0,"charging_state":"Disconnected","conn_charge_cable":"<invalid>","est_battery_range":118.38,"fast_charger_brand":"<invalid>","fast_charger_present":false,"fast_charger_type":"<invalid>","ideal_battery_range":209.95,"managed_charging_active":false,"managed_charging_start_time":null,"managed_charging_user_canceled":false,"max_range_charge_counter":0,"not_enough_power_to_heat":false,"scheduled_charging_pending":false,"scheduled_charging_start_time":null,"time_to_full_charge":0.0,"timestamp":1543186971727,"trip_charging":false,"usable_battery_level":64,"user_charge_enable_request":null},"gui_settings":{"gui_24_hour_time":false,"gui_charge_rate_units":"mi/hr","gui_distance_units":"mi/hr","gui_range_display":"Rated","gui_temperature_units":"F","timestamp":1543186971728},"vehicle_state":{"api_version":4,"autopark_state_v2":"standby","autopark_style":"standard","calendar_supported":true,"car_version":"2018.42.219e7e44","center_display_state":0,"df":0,"dr":0,"ft":0,"homelink_nearby":true,"is_user_present":false,"last_autopark_error":"no_error","locked":true,"media_state":{"remote_control_enabled":true},"notifications_supported":true,"odometer":25000,"parsed_calendar_supported":true,"pf":0,"pr":0,"remote_start":false,"remote_start_supported":true,"rt":0,"software_update":{"expected_duration_sec":2700,"status":""},"speed_limit_mode":{"active":false,"current_limit_mph":75.0,"max_limit_mph":90,"min_limit_mph":50,"pin_code_set":false},"sun_roof_percent_open":0,"sun_roof_state":"unknown","timestamp":1538364666096,"valet_mode":false,"valet_pin_needed":true,"vehicle_name":"Nikola2.0"},"vehicle_config":{"can_accept_navigation_requests":true,"can_actuate_trunks":true,"car_special_type":"base","car_type":"models2","charge_port_type":"US","eu_vehicle":false,"exterior_color":"White","has_air_suspension":true,"has_ludicrous_mode":false,"motorized_charge_port":true,"perf_config":"P2","plg":true,"rear_seat_heaters":0,"rear_seat_type":0,"rhd":false,"roof_color":"None","seat_type":2,"spoiler_type":"None","sun_roof_installed":2,"third_row_seats":"None","timestamp":1538364666096,"trim_badging":"p90d","wheel_type":"AeroTurbine19"}}}'
MOBILE_ENABLED_RESPONSE = '{"response": true}'
OLD_VEHICLE_ID = 10001
CURRENT_VEHICLE_ID = 321


class TeslaApiTestCase(TestCase):
    @staticmethod
    def create_credentials():
        c = Credentials(email="test@test.com")
        c.update_token("1234", "5678", 10 * 24 * 3600)
        c.save()
        return c

    @staticmethod
    def create_vehicle_wo_save():
        v = Vehicle()
        v.tesla_id = CURRENT_VEHICLE_ID
        v.vehicle_id = CURRENT_VEHICLE_ID * 10
        v.display_name = "display_name"
        v.credentials = Credentials.objects.all()[0]
        v.linked = True
        v.mobile_enabled = True
        return v

    @staticmethod
    def create_vehicle_default():
        v = TeslaApiTestCase.create_vehicle_wo_save()
        v.save()
        return v

    @staticmethod
    def create_vehicle_unlinked():
        v = TeslaApiTestCase.create_vehicle_wo_save()
        v.linked = False
        v.save()
        return v

    @staticmethod
    def create_vehicle(vehicle_id, display_name, credentials):
        v = Vehicle()
        v.tesla_id = vehicle_id
        v.vehicle_id = vehicle_id * 10
        v.display_name = display_name
        v.credentials = credentials
        v.linked = True
        v.mobile_enabled = True
        v.save()
        return v

    @staticmethod
    def create_rental(start, end):
        r = Rental(start=start, end=end, code=uuid.uuid4())
        r.handover_code = uuid.uuid4()
        r.vehicle = Vehicle.objects.get(tesla_id=CURRENT_VEHICLE_ID)
        r.save()
        return r

    @staticmethod
    def create_vehicle_data():
        vehicle_data = VehicleData()
        vehicle_data.vehicle = Vehicle.objects.get(tesla_id=CURRENT_VEHICLE_ID)
        vehicle_data.data = json.loads(VEHICLE_DATA_RESPONSE)['response']
        vehicle_data.save()
        return vehicle_data

    def setUp(self):
        pass

    def test_login(self):
        c = Credentials(email="test@test.com")

        with requests_mock.mock() as m:
            m.post('/oauth2/v3/token', text=LOGIN_RESPONSE)
            m.post('/oauth/token', text=LOGIN_RESPONSE)
            login_and_save_credentials(c, auth_code="test", code_verifier="code_verifier")

        self.assertGreater(c.token_expires_at, timezone.now() + datetime.timedelta(days=89))
        self.assertLess(c.token_expires_at, timezone.now() + datetime.timedelta(days=91))

    def test_update_vehicle_initial(self):
        self.create_credentials()

        self.assertEqual(0, len(list(Vehicle.objects.all())))

        with requests_mock.mock() as m:
            m.get('/api/1/vehicles', text=LIST_VEHICLES_RESPONSE)
            m.get('/api/1/vehicles/' + str(CURRENT_VEHICLE_ID) + '/mobile_enabled', text=MOBILE_ENABLED_RESPONSE)
            m.get('/api/1/vehicles/' + str(CURRENT_VEHICLE_ID) + '/vehicle_data', text=VEHICLE_DATA_RESPONSE)
            update_all_vehicles(wake_up_vehicle=True)

        self.assertEqual(1, len(list(Vehicle.objects.all())))

    def test_update_vehicle_remove(self):
        c = self.create_credentials()

        self.assertEqual(0, len(list(Vehicle.objects.all())))
        self.create_vehicle(vehicle_id=OLD_VEHICLE_ID, display_name="old", credentials=c)
        self.assertEqual(1, len(list(Vehicle.objects.all())))

        with requests_mock.mock() as m:
            m.get('/api/1/vehicles', text=LIST_VEHICLES_RESPONSE)
            m.get('/api/1/vehicles/' + str(CURRENT_VEHICLE_ID) + '/mobile_enabled', text=MOBILE_ENABLED_RESPONSE)
            m.get('/api/1/vehicles/' + str(CURRENT_VEHICLE_ID) + '/vehicle_data', text=VEHICLE_DATA_RESPONSE)
            update_all_vehicles(wake_up_vehicle=True)

        self.assertEqual(2, len(list(Vehicle.objects.all())))

        self.assertFalse(Vehicle.objects.get(display_name="old").linked)
        self.assertTrue(Vehicle.objects.get(color="White").linked)

    def test_update_vehicle_update(self):
        c = self.create_credentials()

        self.assertEqual(0, len(list(Vehicle.objects.all())))
        self.create_vehicle(vehicle_id=CURRENT_VEHICLE_ID, display_name="old", credentials=c)

        vehicles = list(Vehicle.objects.all())
        self.assertEqual(1, len(vehicles))

        created_at = vehicles[0].created_at

        with requests_mock.mock() as m:
            m.get('/api/1/vehicles', text=LIST_VEHICLES_RESPONSE)
            m.get('/api/1/vehicles/' + str(CURRENT_VEHICLE_ID) + '/mobile_enabled', text=MOBILE_ENABLED_RESPONSE)
            m.get('/api/1/vehicles/' + str(CURRENT_VEHICLE_ID) + '/vehicle_data', text=VEHICLE_DATA_RESPONSE)
            update_all_vehicles(wake_up_vehicle=True)

        vehicles = list(Vehicle.objects.all())
        self.assertEqual(1, len(vehicles))
        self.assertEqual(created_at, vehicles[0].created_at)
