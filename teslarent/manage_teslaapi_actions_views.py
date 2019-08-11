import logging

from django.contrib.admin.views.decorators import staff_member_required
from django.http.response import Http404
from django.shortcuts import redirect

from teslarent.models import *
from teslarent.teslaapi import teslaapi
from teslarent.views import ensure_vehicle_is_awake, fetch_and_save_vehicle_state

log = logging.getLogger('manage')


@staff_member_required
def refresh_credentials(request, credentials_id):
    if request.method == "POST":
        c = Credentials.objects.get(id=credentials_id)
        teslaapi.refresh_token(c)

    return redirect('/manage/')


@staff_member_required
def update_vehicles(request):
    if request.method != "POST":
        raise Http404

    log.warning('update_vehicles')
    teslaapi.update_all_vehicles()
    return redirect('/manage/')


@staff_member_required
def lock_vehicle(request, vehicle_id):
    if request.method != "POST":
        raise Http404

    log.warning('lock_vehicle vehicle=%s' % (str(vehicle_id)))
    vehicle = Vehicle.objects.get(id=vehicle_id)
    ensure_vehicle_is_awake(vehicle)
    teslaapi.lock_vehicle(vehicle)
    fetch_and_save_vehicle_state(vehicle)
    return redirect('/manage/')


@staff_member_required
def unlock_vehicle(request, vehicle_id):
    if request.method != "POST":
        raise Http404

    log.warning('unlock_vehicle vehicle=%s' % (str(vehicle_id)))
    vehicle = Vehicle.objects.get(id=vehicle_id)
    ensure_vehicle_is_awake(vehicle)
    teslaapi.unlock_vehicle(vehicle)
    fetch_and_save_vehicle_state(vehicle)
    return redirect('/manage/')
