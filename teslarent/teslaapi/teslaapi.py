import requests
import logging
import json

from django.conf import settings

from teslarent.models import Credentials, Vehicle
from teslarent.utils.crypt import decrypt

PRODUCTION_HOST = 'https://owner-api.teslamotors.com'

log = logging.getLogger('teslaapi')


class ApiException(Exception):
    pass


def get_host():
    return PRODUCTION_HOST


def get_headers(credentials):
    return {
        'Authorization': 'Bearer ' + decrypt(credentials.current_token, settings.SECRET_KEY, credentials.salt, credentials.iv)
    }


def login_and_save_credentials(credentials, password):
    """
    @type credentials: Credentials
    """

    body = {
        "grant_type": "password",
        "client_id": settings.TESLA_CLIENT_ID,
        "client_secret": settings.TESLA_CLIENT_SECRET,
        "email": credentials.email,
        "password": password
    }

    log.debug('login on ' + get_host())
    r = requests\
        .post(get_host() + '/oauth/token?grant_type=password', json=body)\
        .json()

    if 'access_token' in r and 'refresh_token' in r and 'expires_in' in r:
        credentials.update_token(r['access_token'], r['refresh_token'], r['expires_in'])
        credentials.save()
    else:
        log.error("login not possible, response=" + str(r))
        raise ApiException("login not possible, response=" + str(r))


def refresh_token(credentials):
    """
    @type credentials: Credentials
    responses:
     {
        'access_token': 'xx', 'token_type': 'bearer', 'expires_in': 3888000,
         'refresh_token': 'xx', 'created_at': 1487705494}
    }
    {'error': 'invalid_grant', 'error_description': 'The provided authorization grant is invalid, expired, revoked, does not match the redirection URI used in the authorization request, or was issued to another client.'}
    """

    body = {
        "grant_type": "refresh_token",
        "client_id": settings.TESLA_CLIENT_ID,
        "client_secret": settings.TESLA_CLIENT_SECRET,
        "refresh_token": decrypt(credentials.refresh_token, settings.SECRET_KEY, credentials.salt, credentials.iv),
    }

    r = requests\
        .post(get_host() + '/oauth/token?grant_type=refresh_token', json=body)\
        .json()

    if 'access_token' in r and 'refresh_token' in r and 'expires_in' in r:
        credentials.update_token(r['access_token'], r['refresh_token'], r['expires_in'])
        credentials.save()
    else:
        log.error("refresh token not possible, response=" + str(r))
        raise ApiException("refresh token not possible, response=" + str(r))


def get_json(text):
    def strip_comment(s):
        return s.split('//')[0]

    d = [strip_comment(s) for s in text.split('\n')]
    return json.loads(''.join(d))


def req(req, credentials, method='get'):
    response = requests.request(method, get_host() + req, headers=get_headers(credentials))
    log.debug('req=' + req + ', status=' + str(response.status_code) + ', resp=' + response.text.replace("\n", " "))
    if response.status_code != 200:
        raise ApiException(req + " returned " + str(response.status_code) + " (" + response.text + ")")

    r = get_json(response.text)

    if 'error' in r:
        raise ApiException(r['error'])

    return r['response']


def list_vehicles(credentials):
    """
    @type credentials: Credentials
    """
    return req('/api/1/vehicles', credentials)


def wake_up(vehicle_id, credentials):
    """
    @type vehicle_id: Int
    @type credentials: Credentials
    @return state: String
    """
    d = req('/api/1/vehicles/' + str(vehicle_id) + '/wake_up', credentials, method='post')
    return d['state']


def is_mobile_enabled(vehicle_id, credentials):
    """
    @type vehicle_id: Int
    @type credentials: Credentials
    @return true|false
    """
    return req('/api/1/vehicles/' + str(vehicle_id) + '/mobile_enabled', credentials)


def get_vehicle_data(vehicle_id, credentials):
    return req('/api/1/vehicles/' + str(vehicle_id) + '/vehicle_data', credentials)


def get_charge_state(vehicle):
    """
    @type vehicle: Vehicle
    @return: "{
        "charging_state": "Complete",  // "Charging", "Complete" ?
        "charge_to_max_range": false,  // current std/max-range setting
        "max_range_charge_counter": 0,
        "fast_charger_present": false, // connected to Supercharger?
        "battery_range": 239.02,       // rated miles
        "est_battery_range": 155.79,   // range estimated from recent driving
        "ideal_battery_range": 275.09, // ideal miles
        "battery_level": 91,           // integer charge percentage
        "battery_current": -0.6,       // current flowing into battery
        "charge_starting_range": null,
        "charge_starting_soc": null,
        "charger_voltage": 0,          // only has value while charging
        "charger_pilot_current": 40,   // max current allowed by charger & adapter
        "charger_actual_current": 0,   // current actually being drawn
        "charger_power": 0,            // kW (rounded down) of charger
        "time_to_full_charge": null,   // valid only while charging
        "charge_rate": -1.0,           // float mi/hr charging or -1 if not charging
        "charge_port_door_open": true
      }"
    """
    d = req('/api/1/vehicles/' + str(vehicle.id) + '/data_request/charge_state', vehicle.credentials)
    return {
        'chargingState': d['charging_state'],
        'chargerPower': d['charger_power'],
        'batteryLevel': d['battery_level'],
        'estBatteryRange': d['est_battery_range'],
        'timeToFullCharge': d['time_to_full_charge'] if 'time_to_full_charge' in d and d['time_to_full_charge'] else 0.0,
    }


def get_climate_settings(vehicle):
    """
    @type vehicle: Vehicle
    @return: "{
        "inside_temp": 17.0,          // degC inside car
        "outside_temp": 9.5,          // degC outside car or null
        "driver_temp_setting": 22.6,  // degC of driver temperature setpoint
        "passenger_temp_setting": 22.6, // degC of passenger temperature setpoint
        "is_auto_conditioning_on": false, // apparently even if on
        "is_front_defroster_on": null, // null or boolean as integer?
        "is_rear_defroster_on": false,
        "fan_status": 0               // fan speed 0-6 or null
      }"
    """
    d = req('/api/1/vehicles/' + str(vehicle.id) + '/data_request/climate_state', vehicle.credentials)
    return {
        'insideTemp': d['inside_temp'],
        'outsideTemp': d['outside_temp'],
        'driverTempSetting': d['driver_temp_setting'],
        'autoConditioningOn': d['is_auto_conditioning_on'],
    }


def get_drive_state(vehicle):
    """
    @type vehicle: Vehicle
    @return: "{
        "shift_state": null,          //
        "speed": null,                //
        "latitude": 33.794839,        // degrees N of equator
        "longitude": -84.401593,      // degrees W of the prime meridian
        "heading": 4,                 // integer compass heading, 0-359
        "gps_as_of": 1359863204       // Unix timestamp of GPS fix
      }"
    """
    d = req('/api/1/vehicles/' + str(vehicle.id) + '/data_request/drive_state', vehicle.credentials)
    return {
        'latitude': d['latitude'],
        'longitude': d['longitude'],
        'gpsAsOf': d['gps_as_of'],
        'speed': d['speed'],
        'heading': d['heading'],
        'shiftState': d['shift_state'],
    }


def get_gui_settings(vehicle):
    """
    @type vehicle: Vehicle
    @return: "{
        "gui_distance_units": "mi/hr",
        "gui_temperature_units": "F",
        "gui_charge_rate_units": "mi/hr",
        "gui_24_hour_time": false,
        "gui_range_display": "Rated"
      }"
    """
    d = req('/api/1/vehicles/' + str(vehicle.id) + '/data_request/gui_settings', vehicle.credentials)
    return {
        'temperatureUnits': d['gui_temperature_units']
    }


def get_vehicle_state(vehicle):
    """
    @type vehicle: Vehicle
    @return: "{
        "df": false,                  // driver's side front door open
        "dr": false,                  // driver's side rear door open
        "pf": false,                  // passenger's side front door open
        "pr": false,                  // passenger's side rear door open
        "ft": false,                  // front trunk is open
        "rt": false,                  // rear trunk is open
        "car_verson": "1.19.42",      // car firmware version
        "locked": true,               // car is locked
        "sun_roof_installed": false,  // panoramic roof is installed
        "sun_roof_state": "unknown",
        "sun_roof_percent_open": 0,   // null if not installed
        "dark_rims": false,           // gray rims installed
        "wheel_type": "Base19",       // wheel type installed
        "has_spoiler": false,         // spoiler is installed
        "roof_color": "Colored",      // "None" for panoramic roof
        "perf_config": "Base"
      }"
    """
    d = req('/api/1/vehicles/' + str(vehicle.id) + '/data_request/vehicle_state', vehicle.credentials)
    return {
        'odometer': d['odometer'] if 'odometer' in d else None,
        'locked': d['locked'],
    }


def set_temperature(vehicle, temperature):
    """
    @type vehicle: Vehicle
    """
    response = requests.post(get_host() + '/api/1/vehicles/' + str(vehicle.id) + '/command/set_temps',
                             data={'driver_temp': str(temperature), 'passenger_temp': str(temperature)},
                             headers=get_headers(vehicle.credentials)
                             )
    log.debug('req=' + '/command/set_temps' + ', status=' + str(response.status_code) + ', resp=' + response.text.replace("\n", " "))
    if response.status_code != 200:
        raise ApiException("set_temperature failed with " + str(response.status_code) + " " + response.text)


def set_hvac_start(vehicle):
    """
    @type vehicle: Vehicle
    """
    response = requests.post(get_host() + '/api/1/vehicles/' + str(vehicle.id) + '/command/auto_conditioning_start',
                             headers=get_headers(vehicle.credentials))
    log.debug('req=' + '/command/auto_conditioning_start' + ', status=' + str(response.status_code) + ', resp=' + response.text.replace("\n", " "))
    if response.status_code != 200:
        raise ApiException("auto_conditioning_start failed with " + str(response.status_code) + " " + response.text)


def set_hvac_stop(vehicle):
    """
    @type vehicle: Vehicle
    """
    response = requests.post(get_host() + '/api/1/vehicles/' + str(vehicle.id) + '/command/auto_conditioning_stop',
                             headers=get_headers(vehicle.credentials))
    log.debug('req=' + '/command/auto_conditioning_stop' + ', status=' + str(response.status_code) + ', resp=' + response.text.replace("\n", " "))
    if response.status_code != 200:
        raise ApiException("auto_conditioning_stop failed with " + str(response.status_code) + " " + response.text)


def load_vehicles(credentials):
    """
    @type credentials: Credentials
    """

    existing_vehicles = {v.id: v for v in Vehicle.objects.filter(credentials=credentials)}
    log.debug("existing_vehicles_db=%s for %s", existing_vehicles.keys(), credentials)

    new_vehicles = {v['id']: v for v in list_vehicles(credentials)}
    log.debug("vehicles_api=%s for %s", new_vehicles.keys(), credentials)

    removed_vehicles = existing_vehicles.keys() - new_vehicles.keys()
    log.debug("removed_vehicles=%s for %s", removed_vehicles, credentials)

    for id in removed_vehicles:
        log.info("unlinking vehicle %d", id)
        existing_vehicles[id].linked = False
        existing_vehicles[id].save()

    for id, v in new_vehicles.items():
        if id in existing_vehicles:
            v_model = existing_vehicles[id]
        else:
            existing_vehicle = Vehicle.objects.filter(id=id).first()
            if existing_vehicle:
                log.info("assigning new vehicle %d from existing", id)
                v_model = existing_vehicle
            else:
                log.info("new vehicle %d", id)
                v_model = Vehicle()
                v_model.id = id
            v_model.credentials = credentials

        v_model.linked = True
        v_model.vehicle_id = v['vehicle_id']
        v_model.display_name = v['display_name'] if v['display_name'] else ''
        v_model.color = v['color'] if v['color'] else ''
        v_model.vin = v['vin']

        vehicle_state = v['state']
        if vehicle_state != 'online':
            vehicle_state = wake_up(v_model.id, credentials)

        if vehicle_state == 'online':  # returns 408 otherwise
            v_model.mobile_enabled = is_mobile_enabled(v_model.id, credentials)

        v_model.state = vehicle_state
        v_model.save()


def print_vehicles():
    for c in Credentials.objects.all():
        print(list_vehicles(c))


def update_all_vehicles():
    for c in Credentials.objects.all():
        load_vehicles(c)

    for unlinked_vehicle in Vehicle.objects.filter(credentials=None):
        log.info("unlinking global vehicle %d", unlinked_vehicle.id)
        unlinked_vehicle.linked = False
        unlinked_vehicle.save()
