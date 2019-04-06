import logging

from django.core.management import call_command
from django.http.response import Http404, HttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404, render_to_response
from jsonview.decorators import json_view

from teslarent.models import Rental, VehicleData
from teslarent.teslaapi import teslaapi
from teslarent.teslaapi.teslaapi import get_vehicle_data

log = logging.getLogger('backgroundTask')


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


def get_climate_state(vehicle_data):
    return {
        'insideTemp': vehicle_data.climate_state__inside_temp,
        'outsideTemp': vehicle_data.climate_state__outside_temp,
        'driverTempSetting': vehicle_data.climate_state__driver_temp_setting,
        'autoConditioningOn': vehicle_data.climate_state__is_auto_conditioning_on,
    }


@json_view
def info(request, uuid):
    rental = get_rental(uuid, validate_active=False)
    rental_info = {
        'start': rental.start,
        'end': rental.end,
        'isActive': rental.is_active,
        'odometerStart': rental.odometer_start,
        'superChargerUsageKWh': 0,  # TODO
        'superChargerUsageIdle': 0,
    }

    if rental.is_active:
        d = VehicleData.objects\
            .filter(vehicle=rental.vehicle) \
            .filter(data__charge_state__isnull=False) \
            .order_by('-created_at')[0]

        return JsonResponse({
            'rental': rental_info,
            'chargeState': {
                'chargingState': d.charge_state__charging_state,
                'chargerPower': d.charge_state__charger_power,
                'batteryLevel': d.charge_state__usable_battery_level,
                'batteryRange': int(d.charge_state__battery_range),
                'timeToFullCharge': d.charge_state__time_to_full_charge,
            },
            'driveState': {
                'gpsAsOf': d.drive_state__gps_as_of_fmt,
                'longitude': d.drive_state__longitude,
                'latitude': d.drive_state__latitude,
                'speed': int(round(d.drive_state__speed, 0)) if d.drive_state__speed else 0,
            },
            'vehicleState': {
                'timestamp': d.vehicle_state__timestamp_fmt,
                'locked': d.vehicle_state__locked,
                'odometer': int(round(d.vehicle_state__odometer, 0)),
            },
            'climateState': get_climate_state(d),
            'uiSettings': {},
        })
    else:
        return JsonResponse({
            'rental': rental_info,
        })


def ensure_vehicle_is_awake(vehicle):
    latest_vehicle_data = VehicleData.objects.filter(vehicle=vehicle).order_by('-created_at')[0]
    if not latest_vehicle_data.is_online:
        log.info('vehicle not online, trying to wakeup vehicle_id %s' % (str(latest_vehicle_data.vehicle.id)))
        call_command('fetch_vehicles_data', wakeup=True, vehicle_id=latest_vehicle_data.vehicle.id)


def fetch_and_save_vehicle_state(vehicle):
    vehicle_data = VehicleData()
    vehicle_data.vehicle = vehicle
    vehicle_data.data = get_vehicle_data(vehicle.id, vehicle.credentials)
    vehicle_data.save()
    return vehicle_data


@json_view
def hvac_start(request, uuid):
    if request.method != "POST":
        raise Http404

    log.debug('hvac_start uuid=%s' % (str(uuid)))
    rental = get_rental(uuid, validate_active=True)
    ensure_vehicle_is_awake(rental.vehicle)
    teslaapi.set_hvac_start(rental.vehicle)
    vehicle_data = fetch_and_save_vehicle_state(rental.vehicle)
    return JsonResponse({
        'climateState': get_climate_state(vehicle_data),
    })


@json_view
def hvac_stop(request, uuid):
    if request.method != "POST":
        raise Http404

    log.debug('hvac_stop uuid=%s' % (str(uuid)))
    rental = get_rental(uuid, validate_active=True)
    ensure_vehicle_is_awake(rental.vehicle)
    teslaapi.set_hvac_stop(rental.vehicle)
    vehicle_data = fetch_and_save_vehicle_state(rental.vehicle)
    return JsonResponse({
        'climateState': get_climate_state(vehicle_data),
    })


@json_view
def hvac_set_temperature(request, uuid, temperature):
    if request.method != "POST":
        raise Http404

    log.debug('hvac_set_temperature uuid=%s' % (str(uuid)))
    rental = get_rental(uuid, validate_active=True)
    ensure_vehicle_is_awake(rental.vehicle)
    teslaapi.set_temperature(rental.vehicle, int(temperature)/10)
    vehicle_data = fetch_and_save_vehicle_state(rental.vehicle)
    return JsonResponse({
        'climateState': get_climate_state(vehicle_data),
    })
