import requests
import logging
import json

from django.conf import settings
from django.utils import timezone

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


def req(path, credentials, method='get', body=None):
    response = requests.request(method, get_host() + path, headers=get_headers(credentials), json=body)
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


def get_nearby_charging_sites(vehicle):
    return req('/api/1/vehicles/' + str(vehicle.id) + '/nearby_charging_sites', vehicle.credentials)


def set_temperature(vehicle, temperature):
    """
    :param Vehicle vehicle
    :param int temperature
    """
    req('/api/1/vehicles/' + str(vehicle.id) + '/command/set_temps', vehicle.credentials, method='post',
        data={'driver_temp': str(temperature), 'passenger_temp': str(temperature)})


def set_hvac_start(vehicle):
    req('/api/1/vehicles/' + str(vehicle.id) + '/command/auto_conditioning_start', vehicle.credentials, method='post')


def set_hvac_stop(vehicle):
    req('/api/1/vehicles/' + str(vehicle.id) + '/command/auto_conditioning_stop', vehicle.credentials, method='post')


def set_hvac_seat_heater(vehicle, seat, level):
    """
    :param Vehicle vehicle
    :param int seat: The desired seat to heat. (0-5)
    :param int level: The desired level for the heater. (0-3)
    """
    req('/api/1/vehicles/' + str(vehicle.id) + '/command/remote_seat_heater_request', vehicle.credentials, method='post',
        data={'heater': int(seat), 'level': int(level)})


def set_hvac_steering_wheel_heater_on(vehicle):
    req('/api/1/vehicles/' + str(vehicle.id) + '/command/remote_steering_wheel_heater_request', vehicle.credentials, method='post',
        data={'on': True})


def set_hvac_steering_wheel_heater_off(vehicle):
    req('/api/1/vehicles/' + str(vehicle.id) + '/command/remote_steering_wheel_heater_request', vehicle.credentials, method='post',
        data={'off': True})


def lock_vehicle(vehicle):
    req('/api/1/vehicles/' + str(vehicle.id) + '/command/door_lock', vehicle.credentials, method='post')


def unlock_vehicle(vehicle):
    req('/api/1/vehicles/' + str(vehicle.id) + '/command/door_unlock', vehicle.credentials, method='post')


def open_frunk(vehicle):
    req('/api/1/vehicles/' + str(vehicle.id) + '/command/actuate_trunk', vehicle.credentials, method='post',
        data={'which_trunk': 'front'})


def open_trunk(vehicle):
    d = get_vehicle_data(vehicle)
    if d['vehicle_state']['rt'] != 0:
        log.info('trunk already open')
        return

    req('/api/1/vehicles/' + str(vehicle.id) + '/command/actuate_trunk', vehicle.credentials, method='post',
        data={'which_trunk': 'rear'})


def close_trunk(vehicle):
    d = get_vehicle_data(vehicle)
    if d['vehicle_state']['rt'] == 0:
        log.info('trunk already closed')
        return

    req('/api/1/vehicles/' + str(vehicle.id) + '/command/actuate_trunk', vehicle.credentials, method='post',
        data={'which_trunk': 'rear'})


def set_charge_limit(vehicle, limit):
    """
    :param Vehicle vehicle
    :param int limit: percent value
    """
    req('/api/1/vehicles/' + str(vehicle.id) + '/command/set_charge_limit?percent=' + str(int(limit)), vehicle.credentials, method='post')


def charge_port_door_open(vehicle):
    req('/api/1/vehicles/' + str(vehicle.id) + '/command/charge_port_door_open', vehicle.credentials, method='post')


def charge_port_door_close(vehicle):
    req('/api/1/vehicles/' + str(vehicle.id) + '/command/charge_port_door_close', vehicle.credentials, method='post')


def charge_start(vehicle):
    req('/api/1/vehicles/' + str(vehicle.id) + '/command/charge_start', vehicle.credentials, method='post')


def charge_stop(vehicle):
    req('/api/1/vehicles/' + str(vehicle.id) + '/command/charge_stop', vehicle.credentials, method='post')


def navigation_request(vehicle, address, locale='en-US'):
    """
    :param Vehicle vehicle
    :param str address: The address to set as the navigation destination.
    :param str locale: The locale for the navigation request.
    """
    req('/api/1/vehicles/' + str(vehicle.id) + '/command/navigation_request', vehicle.credentials, method='post',
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
    req('/api/1/vehicles/' + str(vehicle.id) + '/command/set_valet_mode?on=true&password=' + str(int(pin)), vehicle.credentials, method='post')


def disable_valet_mode(vehicle):
    """
    :param Vehicle vehicle
    """
    req('/api/1/vehicles/' + str(vehicle.id) + '/command/set_valet_mode?on=false', vehicle.credentials, method='post')


def enable_speed_limit(vehicle, limit_mph, pin):
    """
    :param Vehicle vehicle
    :param int limit: The speed limit in MPH. Must be between 50-90.
    :param int pin: 4 digit pin code
    """
    req('/api/1/vehicles/' + str(vehicle.id) + '/command/speed_limit_set_limit', vehicle.credentials, method='post',
        data={'limit_mph': str(int(limit_mph))})
    req('/api/1/vehicles/' + str(vehicle.id) + '/command/speed_limit_activate', vehicle.credentials, method='post',
        data={'pin': str(int(pin))})


def disable_speed_limit(vehicle):
    req('/api/1/vehicles/' + str(vehicle.id) + '/command/speed_limit_deactivate', vehicle.credentials, method='post')


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


def load_vehicles(credentials):
    """
    :param Credential credentials
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
