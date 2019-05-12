import json
import logging
import datetime

from django.core.management import call_command
from django.http.response import Http404, HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from jsonview.decorators import json_view

from teslarent.models import Rental, VehicleData
from teslarent.teslaapi import teslaapi
from teslarent.teslaapi.teslaapi import get_vehicle_data, ApiException

log = logging.getLogger('backgroundTask')


@ensure_csrf_cookie
def index(request):
    with open('teslarent/static/index.html', 'r') as f:
        return HttpResponse(f.read())


def get_rental(uuid, validate_active):
    try:
        rental = Rental.objects.get(code=uuid)
    except ValueError:
        raise Http404
    except Rental.DoesNotExist:
        raise Http404

    if validate_active and not rental.is_active:
        raise Http404

    return rental


def get_vehicle_state(d, state='online'):
    return {
        'timestamp': d.vehicle_state__timestamp_fmt,
        'locked': d.vehicle_state__locked,
        'odometer': int(round(d.vehicle_state__odometer, 0)),
        'state': state,
        'trunksOpen': {
            'front': d.vehicle_state__trunk_front_open,
            'rear': d.vehicle_state__trunk_rear_open,
        },
        'doorsOpen': {
            'frontLeft': d.vehicle_state__door_front_left_open,
            'frontRight': d.vehicle_state__door_front_right_open,
            'rearLeft': d.vehicle_state__door_rear_left_open,
            'rearRight': d.vehicle_state__door_rear_right_open,
        }
    }


def get_climate_state(vehicle_data):
    return {
        'insideTemp': vehicle_data.climate_state__inside_temp,
        'outsideTemp': vehicle_data.climate_state__outside_temp,
        'driverTempSetting': vehicle_data.climate_state__driver_temp_setting,
        'autoConditioningOn': vehicle_data.climate_state__is_climate_on,
    }


@json_view
@ensure_csrf_cookie
def info(request, uuid):
    rental = get_rental(uuid, validate_active=False)
    rental_info = {
        'start': rental.start,
        'end': rental.end,
        'isActive': rental.is_active,
        'odometerStart': rental.odometer_start,
        'odometerEnd': rental.odometer_end,
        'superChargerUsageKWh': 0,  # TODO
        'superChargerUsageIdle': 0,
    }

    if rental.is_active:
        d = VehicleData.objects \
            .filter(vehicle=rental.vehicle) \
            .filter(data__charge_state__isnull=False) \
            .order_by('-created_at')[0]

        age = (timezone.now() - d.created_at).total_seconds()
        state = 'asleep' if age > 15*60 else 'online'

        return JsonResponse({
            'rental': rental_info,
            'chargeState': {
                'chargingState': d.charge_state__charging_state,
                'chargerPower': d.charge_state__charger_power,
                'chargeRate': int(round(d.charge_state__charge_rate, 2)),
                'batteryLevel': d.charge_state__usable_battery_level,
                'batteryRange': int(d.charge_state__battery_range),
                'timeToFullCharge': d.charge_state__time_to_full_charge,
            },
            'driveState': {
                'shiftState': d.drive_state__shift_state,
                'gpsAsOf': d.drive_state__gps_as_of_fmt,
                'longitude': d.drive_state__longitude,
                'latitude': d.drive_state__latitude,
                'speed': int(round(d.drive_state__speed, 0)) if d.drive_state__speed else 0,
            },
            'vehicleState': get_vehicle_state(d, state),
            'climateState': get_climate_state(d),
            'uiSettings': {},
        })
    else:
        return JsonResponse({
            'rental': rental_info,
        })


def ensure_vehicle_is_awake(vehicle):
    fifteen_minutes_ago = timezone.now() - datetime.timedelta(minutes=15)
    latest_vehicle_datas = VehicleData.objects\
        .filter(vehicle=vehicle)\
        .filter(created_at__gte=fifteen_minutes_ago)\
        .order_by('-created_at')
    if len(latest_vehicle_datas) == 0 or not latest_vehicle_datas[0].is_online:
        log.info('vehicle not online, trying to wakeup vehicle_id %s' % (str(vehicle.id)))
        call_command('fetch_vehicles_data', wakeup=True, vehicle_id=vehicle.id)


def fetch_and_save_vehicle_state(vehicle):
    vehicle_data = VehicleData()
    vehicle_data.vehicle = vehicle
    vehicle_data.data = get_vehicle_data(vehicle.id, vehicle.credentials)
    vehicle_data.save()
    return vehicle_data


@json_view
@ensure_csrf_cookie
def vehicle_open_frunk(request, uuid):
    if request.method != "POST":
        raise Http404

    log.warning('vehicle_open_frunk uuid=%s' % (str(uuid)))
    rental = get_rental(uuid, validate_active=True)
    ensure_vehicle_is_awake(rental.vehicle)
    teslaapi.open_frunk(rental.vehicle)
    vehicle_data = fetch_and_save_vehicle_state(rental.vehicle)
    return JsonResponse({'vehicleState': get_vehicle_state(vehicle_data),})


@json_view
@ensure_csrf_cookie
def vehicle_lock(request, uuid):
    if request.method != "POST":
        raise Http404

    log.warning('vehicle_lock uuid=%s' % (str(uuid)))
    rental = get_rental(uuid, validate_active=True)
    ensure_vehicle_is_awake(rental.vehicle)
    teslaapi.lock_vehicle(rental.vehicle)
    vehicle_data = fetch_and_save_vehicle_state(rental.vehicle)
    return JsonResponse({'vehicleState': get_vehicle_state(vehicle_data),})


@json_view
@ensure_csrf_cookie
def hvac_start(request, uuid):
    if request.method != "POST":
        raise Http404

    log.warning('hvac_start uuid=%s' % (str(uuid)))
    rental = get_rental(uuid, validate_active=True)
    ensure_vehicle_is_awake(rental.vehicle)
    teslaapi.set_hvac_start(rental.vehicle)
    vehicle_data = fetch_and_save_vehicle_state(rental.vehicle)
    return JsonResponse({'climateState': get_climate_state(vehicle_data),})


@json_view
@ensure_csrf_cookie
def hvac_stop(request, uuid):
    if request.method != "POST":
        raise Http404

    log.warning('hvac_stop uuid=%s' % (str(uuid)))
    rental = get_rental(uuid, validate_active=True)
    ensure_vehicle_is_awake(rental.vehicle)
    teslaapi.set_hvac_stop(rental.vehicle)
    vehicle_data = fetch_and_save_vehicle_state(rental.vehicle)
    return JsonResponse({'climateState': get_climate_state(vehicle_data),})


@json_view
@ensure_csrf_cookie
def hvac_set_temperature(request, uuid, temperature):
    if request.method != "POST":
        raise Http404

    log.warning('hvac_set_temperature temp=%s uuid=%s' % (str(temperature), str(uuid)))
    rental = get_rental(uuid, validate_active=True)
    ensure_vehicle_is_awake(rental.vehicle)
    teslaapi.set_temperature(rental.vehicle, int(temperature)/10)
    vehicle_data = fetch_and_save_vehicle_state(rental.vehicle)
    return JsonResponse({'climateState': get_climate_state(vehicle_data),})


@json_view
@ensure_csrf_cookie
def nearby_charging(request, uuid):
    rental = get_rental(uuid, validate_active=True)
    ensure_vehicle_is_awake(rental.vehicle)
    return JsonResponse(teslaapi.get_nearby_charging_sites(rental.vehicle))


@json_view
@ensure_csrf_cookie
def navigation_request(request, uuid):
    if request.method != "POST":
        raise Http404

    rental = get_rental(uuid, validate_active=True)
    received_json_data = json.loads(request.body.decode("utf-8"))
    if 'lat' not in received_json_data or 'long' not in received_json_data:
        raise ApiException('No location data received')

    address = str(received_json_data['lat']) + ',' + str(received_json_data['long'])
    ensure_vehicle_is_awake(rental.vehicle)
    teslaapi.navigation_request(rental.vehicle, address=address)
    return JsonResponse({'address': address})
