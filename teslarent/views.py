from django.http.response import Http404, HttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404, render_to_response
from jsonview.decorators import json_view

from teslarent.models import Rental, VehicleData
from teslarent.teslaapi import teslaapi


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
        latest_vehicle_data = VehicleData.objects.filter(vehicle=rental.vehicle).order_by('-created_at')[0]

        return JsonResponse({
            'rental': rental_info,
            'chargeState': {
                'chargingState': latest_vehicle_data.charge_state__charging_state,
                'chargerPower': latest_vehicle_data.charge_state__charger_power,
                'batteryLevel': latest_vehicle_data.charge_state__usable_battery_level,
                'estBatteryRange': latest_vehicle_data.charge_state__est_battery_range,
                'timeToFullCharge': latest_vehicle_data.charge_state__time_to_full_charge,
            },
            'driveState': {
                'gpsAsOf': latest_vehicle_data.drive_state__gps_as_of_fmt,
                'longitude': latest_vehicle_data.drive_state__longitude,
                'latitude': latest_vehicle_data.drive_state__latitude,
                'speed': latest_vehicle_data.drive_state__speed,
            },
            'vehicleState': {
                'timestamp': latest_vehicle_data.vehicle_state__timestamp,
                'locked': latest_vehicle_data.vehicle_state__locked,
                'odometer': latest_vehicle_data.vehicle_state__odometer,
            },
            'climateState': {
                'insideTemp': latest_vehicle_data.climate_state__inside_temp,
                'outsideTemp': latest_vehicle_data.climate_state__outside_temp,
                'driverTempSetting': latest_vehicle_data.climate_state__driver_temp_setting,
                'autoConditioningOn': latest_vehicle_data.climate_state__driver_temp_setting,
            },
            'uiSettings': {},
        })
    else:
        return JsonResponse({
            'rental': rental_info,
        })


@json_view
def hvac_start(request, uuid):
    if request.method != "POST":
        raise Http404

    rental = get_rental(uuid, validate_active=True)
    teslaapi.set_hvac_start(rental.vehicle)
    return JsonResponse({
        'climateState': teslaapi.get_climate_settings(rental.vehicle),
    })


@json_view
def hvac_stop(request, uuid):
    if request.method != "POST":
        raise Http404

    rental = get_rental(uuid, validate_active=True)
    teslaapi.set_hvac_stop(rental.vehicle)
    return JsonResponse({
        'climateState': teslaapi.get_climate_settings(rental.vehicle),
    })


@json_view
def hvac_set_temperature(request, uuid, temperature):
    if request.method != "POST":
        raise Http404

    rental = get_rental(uuid, validate_active=True)
    teslaapi.set_temperature(rental.vehicle, int(temperature)/10)
    return JsonResponse({
        'climateState': teslaapi.get_climate_settings(rental.vehicle),
    })
