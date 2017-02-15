from django.http.response import Http404, HttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404, render_to_response
from jsonview.decorators import json_view

from teslarent.models import Rental
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
        'superChargerUsageKWh': 0,
        'superChargerUsageIdle': 0,
    }

    if rental.is_active:
        return JsonResponse({
            'rental': rental_info,
            'chargeState': teslaapi.get_charge_state(rental.vehicle),
            'driveState': teslaapi.get_drive_state(rental.vehicle),
            'vehicleState': teslaapi.get_vehicle_state(rental.vehicle),
            'climateSettings': teslaapi.get_climate_settings(rental.vehicle),
            'uiSettings': teslaapi.get_gui_settings(rental.vehicle),
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
        'climateSettings': teslaapi.get_climate_settings(rental.vehicle),
    })


@json_view
def hvac_stop(request, uuid):
    if request.method != "POST":
        raise Http404

    rental = get_rental(uuid, validate_active=True)
    teslaapi.set_hvac_stop(rental.vehicle)
    return JsonResponse({
        'climateSettings': teslaapi.get_climate_settings(rental.vehicle),
    })


@json_view
def hvac_set_temperature(request, uuid, temperature):
    if request.method != "POST":
        raise Http404

    rental = get_rental(uuid, validate_active=True)
    teslaapi.set_temperature(rental.vehicle, int(temperature)/10)
    return JsonResponse({
        'climateSettings': teslaapi.get_climate_settings(rental.vehicle),
    })
