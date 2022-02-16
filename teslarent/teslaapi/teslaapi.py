import base64
import hashlib
import time
from urllib.parse import urlencode

import requests
import logging
import json

from bs4 import BeautifulSoup

from django.conf import settings
from django.utils import timezone

from teslarent.models import Credentials, Vehicle, VehicleData
from teslarent.utils.crypt import decrypt, random_string

AUTH_HOST = 'https://auth.tesla.com'
OWNERAPI_HOST = 'https://owner-api.teslamotors.com'

log = logging.getLogger('teslaapi')


class ApiException(Exception):
    pass


def get_auth_host():
    return AUTH_HOST


def get_host():
    return OWNERAPI_HOST


def get_headers(credentials):
    return {
        'Authorization': 'Bearer ' + decrypt(credentials.current_token, settings.SECRET_KEY, credentials.salt, credentials.iv)
    }


def generate_code_verifier():
    return random_string(86)


def get_code_challenge(code_verifier):
    return base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode()).digest()).rstrip(b'=').decode('utf-8')


def generate_oauth_state():
    return random_string(10)


def get_auth_url(code_challenge, oauth_state, login_hint=''):
    return get_auth_host()\
           + '/oauth2/v3/authorize?' \
             'client_id=ownerapi&' \
             'code_challenge={}&'  \
             'code_challenge_method=S256&'  \
             '{}&'  \
             'response_type=code&'  \
             'scope=openid email offline_access&'  \
             'state={}&'  \
             'login_hint={}'.format(code_challenge, urlencode({'redirect_uri': 'https://auth.tesla.com/void/callback'}),
                                    oauth_state, login_hint)


def login_and_save_credentials(credentials, auth_code, code_verifier):
    """
    @type credentials: Credentials
    """

    # Step 3: Exchange authorization code for bearer token
    body = {
        'grant_type': 'authorization_code',
        'client_id': 'ownerapi',
        'code': auth_code,
        'code_verifier': code_verifier,
        'redirect_uri': "https://auth.tesla.com/void/callback",
    }

    log.debug('login on ' + get_auth_host())
    r3 = requests\
        .post(get_auth_host() + '/oauth2/v3/token', json=body)\
        .json()

    if 'access_token' not in r3 or 'refresh_token' not in r3:
        log.error("login not possible, response=" + str(r3))
        raise ApiException("login not possible, response=" + str(r3))

    # Step 4: Exchange bearer token for access token
    body = {
        'grant_type': "urn:ietf:params:oauth:grant-type:jwt-bearer",
        'client_id': settings.TESLA_CLIENT_ID,
        'client_secret': settings.TESLA_CLIENT_SECRET,
    }

    log.debug('login on ' + get_host())
    r4 = requests\
        .post(get_host() + '/oauth/token', json=body, headers={'Authorization': 'Bearer ' + r3['access_token']})\
        .json()

    if 'access_token' in r4 and 'expires_in' in r4:
        credentials.update_token(r4['access_token'], r3['refresh_token'], r4['expires_in'])
        credentials.save()
    else:
        log.error("login not possible, response=" + str(r4))
        raise ApiException("login not possible, response=" + str(r4))


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
        'grant_type': 'refresh_token',
        'client_id': 'ownerapi',
        'refresh_token': decrypt(credentials.refresh_token, settings.SECRET_KEY, credentials.salt, credentials.iv),
        'scope': 'openid email offline_access',
    }

    r3 = requests\
        .post(get_auth_host() + '/oauth2/v3/token', json=body)\
        .json()

    if 'access_token' not in r3 or 'refresh_token' not in r3:
        log.error("refresh token not possible, response=" + str(r3))
        raise ApiException("refresh token not possible, response=" + str(r3))

    # Step 4: Exchange bearer token for access token
    body = {
        'grant_type': "urn:ietf:params:oauth:grant-type:jwt-bearer",
        'client_id': settings.TESLA_CLIENT_ID,
        'client_secret': settings.TESLA_CLIENT_SECRET,
    }

    log.debug('login on ' + get_host())
    r4 = requests\
        .post(get_host() + '/oauth/token', json=body, headers={'Authorization': 'Bearer ' + r3['access_token']})\
        .json()

    if 'access_token' in r4 and 'expires_in' in r4:
        credentials.update_token(r4['access_token'], r3['refresh_token'], r4['expires_in'])
        credentials.save()
    else:
        log.error("refresh token not possible, response=" + str(r4))
        raise ApiException("login not possible, response=" + str(r4))


def get_json(text):
    def strip_comment(s):
        return s.split('//')[0]

    d = [strip_comment(s) for s in text.split('\n')]
    return json.loads(''.join(d))


def req(path, credentials, method='get', data=None):
    response = requests.request(method, get_host() + path, headers=get_headers(credentials), json=data)
    log.debug('req=' + path + ', status=' + str(response.status_code) + ', resp=' + response.text.replace("\n", " "))
    if response.status_code != 200:
        raise ApiException(path + " returned " + str(response.status_code) + " (" + response.text + ")")

    r = get_json(response.text)

    if 'error' in r:
        raise ApiException(r['error'])

    return r['response']


def list_vehicles(credentials):
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


def fetch_and_save_vehicle_state(vehicle):
    """
    :param Vehicle vehicle
    :return: VehicleData
    """
    vehicle_data = VehicleData()
    vehicle_data.vehicle = vehicle
    vehicle_data.data = get_vehicle_data(vehicle.tesla_id, vehicle.credentials)
    vehicle_data.save()
    return vehicle_data


def get_nearby_charging_sites(vehicle):
    return req('/api/1/vehicles/' + str(vehicle.tesla_id) + '/nearby_charging_sites', vehicle.credentials)


def set_temperature(vehicle, temperature):
    """
    :param Vehicle vehicle
    :param int temperature
    """
    req('/api/1/vehicles/' + str(vehicle.tesla_id) + '/command/set_temps', vehicle.credentials, method='post',
        data={'driver_temp': str(temperature), 'passenger_temp': str(temperature)})


def set_hvac_start(vehicle):
    req('/api/1/vehicles/' + str(vehicle.tesla_id) + '/command/auto_conditioning_start', vehicle.credentials, method='post')


def set_hvac_stop(vehicle):
    req('/api/1/vehicles/' + str(vehicle.tesla_id) + '/command/auto_conditioning_stop', vehicle.credentials, method='post')


def set_hvac_seat_heater(vehicle, seat, level):
    """
    :param Vehicle vehicle
    :param int seat: The desired seat to heat. (front: 0,1; rear: 2,4,5; no 3)
    :param int level: The desired level for the heater. (0-3)

    response if hvac is not on: status=200, resp={"response":{"reason":"cabin comfort remote settings not enabled","result":false}}
    """
    req('/api/1/vehicles/' + str(vehicle.tesla_id) + '/command/remote_seat_heater_request', vehicle.credentials, method='post',
        data={'heater': int(seat), 'level': int(level)})


def set_hvac_steering_wheel_heater_on(vehicle):
    """
    response: status=200, resp={"response":{"reason":"cabin comfort remote settings not enabled","result":false}}
    """
    req('/api/1/vehicles/' + str(vehicle.tesla_id) + '/command/remote_steering_wheel_heater_request', vehicle.credentials, method='post',
        data={'on': True})


def set_hvac_steering_wheel_heater_off(vehicle):
    req('/api/1/vehicles/' + str(vehicle.tesla_id) + '/command/remote_steering_wheel_heater_request', vehicle.credentials, method='post',
        data={'off': True})


def lock_vehicle(vehicle):
    req('/api/1/vehicles/' + str(vehicle.tesla_id) + '/command/door_lock', vehicle.credentials, method='post')


def unlock_vehicle(vehicle):
    req('/api/1/vehicles/' + str(vehicle.tesla_id) + '/command/door_unlock', vehicle.credentials, method='post')


def open_frunk(vehicle):
    req('/api/1/vehicles/' + str(vehicle.tesla_id) + '/command/actuate_trunk', vehicle.credentials, method='post',
        data={'which_trunk': 'front'})


def open_trunk(vehicle):
    d = get_vehicle_data(vehicle.tesla_id, vehicle.credentials)
    if d['vehicle_state']['rt'] != 0:
        log.info('trunk already open')
        return

    req('/api/1/vehicles/' + str(vehicle.tesla_id) + '/command/actuate_trunk', vehicle.credentials, method='post',
        data={'which_trunk': 'rear'})


def close_trunk(vehicle):
    d = get_vehicle_data(vehicle.tesla_id, vehicle.credentials)
    if d['vehicle_state']['rt'] == 0:
        log.info('trunk already closed')
        return

    req('/api/1/vehicles/' + str(vehicle.tesla_id) + '/command/actuate_trunk', vehicle.credentials, method='post',
        data={'which_trunk': 'rear'})


def set_charge_limit(vehicle, limit):
    """
    :param Vehicle vehicle
    :param int limit: percent value
    """
    req('/api/1/vehicles/' + str(vehicle.tesla_id) + '/command/set_charge_limit', vehicle.credentials, method='post',
        data={'percent': int(limit)})


def charge_port_door_open(vehicle):
    req('/api/1/vehicles/' + str(vehicle.tesla_id) + '/command/charge_port_door_open', vehicle.credentials, method='post')


def charge_port_door_close(vehicle):
    req('/api/1/vehicles/' + str(vehicle.tesla_id) + '/command/charge_port_door_close', vehicle.credentials, method='post')


def charge_start(vehicle):
    """
    response: status=200, resp={"response":{"reason":"charging","result":false}}
    """
    req('/api/1/vehicles/' + str(vehicle.tesla_id) + '/command/charge_start', vehicle.credentials, method='post')


def charge_stop(vehicle):
    req('/api/1/vehicles/' + str(vehicle.tesla_id) + '/command/charge_stop', vehicle.credentials, method='post')


def navigation_request(vehicle, address, locale='en-US'):
    """
    :param Vehicle vehicle
    :param str address: The address to set as the navigation destination.
    :param str locale: The locale for the navigation request.
    """
    req('/api/1/vehicles/' + str(vehicle.tesla_id) + '/command/navigation_request', vehicle.credentials, method='post',
        data={
            'type': 'share_ext_content_raw',
            'timestamp_ms': timezone.now().timestamp(),
            'locale': locale,
            'value': {
                'android.intent.extra.TEXT': address
            }
        })


def enable_valet_mode(vehicle, pin):
    """
    :param Vehicle vehicle
    :param int pin: 4 digit pin code
    """
    req('/api/1/vehicles/' + str(vehicle.tesla_id) + '/command/set_valet_mode', vehicle.credentials, method='post',
        data={'on': True, 'password': int(pin)})


def disable_valet_mode(vehicle):
    """
    :param Vehicle vehicle
    """
    req('/api/1/vehicles/' + str(vehicle.tesla_id) + '/command/set_valet_mode', vehicle.credentials, method='post',
        data={'on': False})


def enable_speed_limit(vehicle, limit_mph, pin):
    """
    :param Vehicle vehicle
    :param int limit: The speed limit in MPH. Must be between 50-90.
    :param int pin: 4 digit pin code
    """
    req('/api/1/vehicles/' + str(vehicle.tesla_id) + '/command/speed_limit_set_limit', vehicle.credentials, method='post',
        data={'limit_mph': str(int(limit_mph))})
    req('/api/1/vehicles/' + str(vehicle.tesla_id) + '/command/speed_limit_activate', vehicle.credentials, method='post',
        data={'pin': str(int(pin))})


def disable_speed_limit(vehicle):
    req('/api/1/vehicles/' + str(vehicle.tesla_id) + '/command/speed_limit_deactivate', vehicle.credentials, method='post')


def fetch_logs(credentials):
    """
    :param Credential credentials
    :return: {"response":"ok"}
    """
    return req('/api/1/logs', credentials, method='post')


def fetch_diagnostics(credentials):
    """
    :param Credential credentials
    :return: {"response":{"eligible":false}}
    """
    return req('/api/1/diagnostics', credentials)


def load_vehicles(credentials, wake_up_vehicle):
    """
    :param Credential credentials
    """

    existing_vehicles = {v.vehicle_id: v for v in Vehicle.objects.filter(credentials=credentials)}
    log.debug("existing_vehicles_db=%s for %s", existing_vehicles.keys(), credentials)

    new_vehicles = {v['vehicle_id']: v for v in list_vehicles(credentials)}
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
            existing_vehicle = Vehicle.objects.filter(vehicle_id=id).first()
            if existing_vehicle:
                log.info("assigning new vehicle %d from existing", id)
                v_model = existing_vehicle
            else:
                log.info("new vehicle %d", id)
                v_model = Vehicle()
                v_model.vehicle_id = id
            v_model.credentials = credentials

        v_model.linked = True
        v_model.tesla_id = v['id']
        v_model.display_name = v['display_name'] if v['display_name'] else ''
        #v_model.color = v['color'] if v['color'] else ''  # color always seems empty
        v_model.vin = v['vin']
        v_model.option_codes = v['option_codes']
        v_model.save()

        vehicle_state = v['state']
        if vehicle_state != 'online' and wake_up_vehicle:
            vehicle_state = wake_up(v_model.tesla_id, credentials)
            time.sleep(10)

        if vehicle_state == 'online':  # returns 408 otherwise
            v_model.mobile_enabled = is_mobile_enabled(v_model.tesla_id, credentials)  # doesn't seem to be available in vehicle_data

            vehicle_data = fetch_and_save_vehicle_state(v_model)
            if vehicle_data:
                v_model.color = vehicle_data.vehicle_config__exterior_color
                v_model.model = vehicle_data.vehicle_config__car_type
        elif wake_up_vehicle:
            log.warning("vehicle still not online %d", id)

        v_model.state = vehicle_state
        v_model.save()


def print_vehicles():
    for c in Credentials.objects.all():
        print(list_vehicles(c))


def update_all_vehicles(wake_up_vehicle):
    for c in Credentials.objects.all():
        load_vehicles(c, wake_up_vehicle=wake_up_vehicle)

    for unlinked_vehicle in Vehicle.objects.filter(credentials=None):
        if unlinked_vehicle.linked:
            log.info("unlinking global vehicle %d", unlinked_vehicle.id)
            unlinked_vehicle.linked = False
            unlinked_vehicle.save()
