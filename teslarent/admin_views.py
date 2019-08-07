import base64
import logging
import uuid
import datetime
from functools import reduce

from django.conf import settings
from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse, HttpResponseForbidden
from django.http.response import Http404, JsonResponse
from django.shortcuts import redirect, render
from jsonview.decorators import json_view

from json import encoder

from teslarent.views import ensure_vehicle_is_awake, fetch_and_save_vehicle_state

encoder.FLOAT_REPR = lambda o: format(o, '.2f')  # monkey patching https://stackoverflow.com/questions/1447287/format-floats-with-standard-json-module

from teslarent.forms import CredentialsForm, RentalForm
from teslarent.management.commands.rental_start_end import BackgroundTask
from teslarent.models import *
from teslarent.teslaapi import teslaapi

log = logging.getLogger('manage')


@json_view
def ping(request):
    t = BackgroundTask.Instance()
    t.ensure_thread_running()
    return JsonResponse({'initialized_at': t.initialized_at})


def each_context(request, title="Title"):
    return {
        'title': title,
        'site_title': "Tesla Rental Admin",
        'site_header': "Tesla Rental Admin",
        'has_permission': admin.site.has_permission(request),
    }


def check_basic_auth(request):
    if 'HTTP_AUTHORIZATION' in request.META:
        auth = request.META['HTTP_AUTHORIZATION'].split()
        if len(auth) == 2 and auth[0].lower() == "basic":
            return base64.b64decode(auth[1]).decode('utf-8').split(':')
    return None, None


def metrics(request):
    if settings.METRICS_SECRET:
        username, password = check_basic_auth(request)
        if not username or not password or password != settings.METRICS_SECRET:
            return HttpResponseForbidden()

    content = []

    for vehicle in Vehicle.objects.all():
        latest_vehicle_data_any = VehicleData.objects.filter(vehicle=vehicle).order_by('-created_at').first()
        if not latest_vehicle_data_any:
            continue

        latest_vehicle_data_online = VehicleData.objects.filter(vehicle=vehicle).filter(data__state='online').order_by('-created_at').first()

        content.append('vehicle_updated_at{vehicle="' + str(vehicle.vehicle_id) + '"} ' + str(latest_vehicle_data_any.created_at.timestamp()))
        content.append('vehicle_offline{vehicle="' + str(vehicle.vehicle_id) + '"} ' + ('1' if latest_vehicle_data_any.is_offline else '0'))
        content.append('vehicle_last_online_at{vehicle="' + str(vehicle.vehicle_id) + '"} ' + str(latest_vehicle_data_online.created_at.timestamp()))

        latest_vehicle_data_locked = VehicleData.objects.filter(vehicle=vehicle).filter(data__vehicle_state__locked=True).order_by('-created_at').first()
        latest_vehicle_data_unlocked = VehicleData.objects.filter(vehicle=vehicle).filter(data__vehicle_state__locked=False).order_by('-created_at').first()

        if latest_vehicle_data_locked and latest_vehicle_data_unlocked:
            if latest_vehicle_data_unlocked.created_at > latest_vehicle_data_locked.created_at:
                content.append('vehicle_locked{vehicle="' + str(vehicle.vehicle_id) + '"} ' + str(latest_vehicle_data_locked.created_at.timestamp()))
            else:
                content.append('vehicle_locked{vehicle="' + str(vehicle.vehicle_id) + '"} ' + str(timezone.now().timestamp()))

    for credential in Credentials.objects.all():
        content.append('token_expires_at{id="' + str(credential.email) + '"} ' + str(credential.token_expires_at.timestamp()))

    t = BackgroundTask.Instance()
    t.ensure_thread_running()
    content.append('background_task_initialized_at ' + str(t.initialized_at.timestamp()))

    content.append('')
    return HttpResponse("\n".join(content), content_type='text/plain')


def sum_non_null(func, iterable):
    return sum(filter(None, map(func, iterable)))


@staff_member_required
def index(request):
    now = timezone.now()
    one_day_ago = now - datetime.timedelta(days=1)
    one_day_from_now = now + datetime.timedelta(days=1)

    rentals = Rental.objects.all().order_by('start')
    totals = {
        'distance_driven': sum_non_null(lambda r: r.distance_driven, rentals),
        'price_brutto': sum_non_null(lambda r: r.price_brutto, rentals),
        'price_netto': sum_non_null(lambda r: r.price_netto, rentals),
        'price_charging': round(sum_non_null(lambda r: r.price_charging, rentals), 2),
        'earnings_per_km': round(sum_non_null(lambda r: r.price_netto, rentals) / sum_non_null(lambda r: r.distance_driven, rentals), 2),
    }

    vehicles = Vehicle.objects.all()
    for vehicle in vehicles:
        vehicle.d = VehicleData.objects.filter(vehicle=vehicle)\
            .filter(data__charge_state__battery_level__isnull=False)\
            .order_by('-created_at').first()

    context = dict(
        each_context(request, title="Manage Rentals"),
        debug=bool(settings.DEBUG),
        active_rentals=Rental.objects.filter(start__lt=one_day_from_now, end__gt=one_day_ago).order_by('start'),
        rentals=rentals,
        totals=totals,
        credentials=Credentials.objects.all(),
        vehicles=vehicles,
        has_any_vehicle=len(vehicles) > 0,
        has_active_vehicle=any([v.is_active for v in vehicles]),
    )
    return render(request, 'manage.html', context)


@staff_member_required
def add_credentials(request):
    if request.method == "POST":
        form = CredentialsForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            c = Credentials.objects.filter(email=email).first()
            if not c:
                c = Credentials(email=email)

            teslaapi.login_and_save_credentials(c, form.cleaned_data['password'])
            del form.cleaned_data['password']

            teslaapi.load_vehicles(c)
            return redirect('./')
    else:
        form = CredentialsForm()

    context = dict(
        each_context(request, title="Add Credentials"),
        form=form,
    )
    return render(request, 'add_credentials.html', context)


@staff_member_required
def delete_credentials(request, credentials_id):
    c = Credentials.objects.get(id=credentials_id)
    if request.method == "POST":
        c.delete()
        return redirect('/manage/')
    context = dict(
        each_context(request, title="Delete Credentials"),
        credentials=c,
    )
    return render(request, 'delete_credentials.html', context)


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


@staff_member_required
def add_rental(request):
    vehicles = Vehicle.get_all_active_vehicles()
    if len(vehicles) == 0:
        # TODO show error message to user
        log.warning("Cannot add rental, there is no active vehicle")
        return redirect('/manage/')

    vehicle = vehicles[0] if len(vehicles) == 1 else None
    start = timezone.now().replace(minute=0, second=0, microsecond=0) + datetime.timedelta(hours=1)
    end = start + datetime.timedelta(days=1)
    initial = Rental(start=start, end=end, vehicle=vehicle, code=str(uuid.uuid4()))
    return add_or_edit_rental(request, rental=initial)


@staff_member_required
def edit_rental(request, rental_id):
    return add_or_edit_rental(request, rental=Rental.objects.get(id=rental_id))


@staff_member_required
def delete_rental(request, rental_id):
    r = Rental.objects.get(id=rental_id)
    if request.method == "POST":
        r.delete()
        BackgroundTask.Instance().ensure_thread_running()

    return redirect('/manage/')


def add_or_edit_rental(request, rental):
    form = RentalForm(request.POST or None, instance=rental)
    if request.method == "POST":
        if form.is_valid():
            form.save()
            BackgroundTask.Instance().ensure_thread_running()
            return redirect('/manage/')

    context = dict(
        each_context(request, title="Add/edit Rental"),
        form=form,
    )
    return render(request, 'edit_rental.html', context)


@staff_member_required
def charge_stats(request, vehicle_id):
    context = dict(
        each_context(request, title="Stats"),
        vehicle_id=vehicle_id,
    )
    return render(request, 'charge_stats.html', context)


@staff_member_required
def charge_stats_data(request, vehicle_id, offset, limit):
    results = []
    next_d = None
    for d in VehicleData.objects\
            .filter(vehicle_id=vehicle_id)\
            .filter(data__charge_state__battery_level__isnull=False)\
            .order_by('-created_at')[offset:offset + limit]:
        if not next_d:
            next_d = d
            continue

        distance = next_d.vehicle_state__odometer - d.vehicle_state__odometer
        battery_soc_kwh_diff = d.battery_soc_kwh - next_d.battery_soc_kwh
        results.append({
            'createdAt': d.created_at,
            'batteryLevel': d.charge_state__battery_level,
            'batteryLevelKWh': d.battery_soc_kwh,
            'distance': distance,
            'speedAvg': distance / ((next_d.created_at - d.created_at).total_seconds() / 3600),
            'efficiency': battery_soc_kwh_diff * 1000 / distance if distance > 1 and battery_soc_kwh_diff > 0 else 0,
        })
        next_d = d
    return JsonResponse({'items': results})


@staff_member_required
def daily_stats_data(request, vehicle_id, offset, limit):
    # 2019-03-28 00:10
    # 2019-03-28 00:05
    # 2019-03-27 23:55
    # 2019-03-27 23:50
    # ...
    # 2019-03-27 00:10
    # 2019-03-27 00:05
    # 2019-03-27 00:00
    # 2019-03-26 23:55

    current_day = None
    results = []
    start_d = None
    newer_d = None
    charged_kwh = 0
    used_kwh = 0

    for d in VehicleData.objects\
            .filter(vehicle_id=vehicle_id)\
            .filter(data__charge_state__battery_level__isnull=False)\
            .order_by('-created_at')[offset:offset + limit]:
        if not current_day:
            current_day = d.created_at.date()
            start_d = d
            newer_d = d

        if d.created_at.date() != current_day:
            distance = start_d.vehicle_state__odometer - d.vehicle_state__odometer
            results.append({
                'date': current_day,
                'startOdo': round(d.vehicle_state__odometer, 2),
                'endOdo': round(start_d.vehicle_state__odometer, 2),
                'distance': round(distance, 2),
                'chargedKWh': round(charged_kwh, 2),
                'usedKWh': round(used_kwh, 2),
                'efficiency': round(used_kwh * 1000 / distance, 2) if distance > 1 else None,
            })
            start_d = d
            charged_kwh = 0
            used_kwh = 0
            current_day = d.created_at.date()

        if newer_d.battery_soc_kwh > d.battery_soc_kwh:
            charged_kwh += newer_d.battery_soc_kwh - d.battery_soc_kwh
        else:
            used_kwh += d.battery_soc_kwh - newer_d.battery_soc_kwh
        newer_d = d

    return JsonResponse({'items': results})


@staff_member_required
def raw_data(request, vehicle_id, offset, limit):
    results = []
    prev_d = None
    for d in VehicleData.objects\
            .filter(vehicle_id=vehicle_id)\
            .filter(data__charge_state__battery_level__isnull=False)\
            .order_by('-created_at')[offset:offset + limit]:
        if not prev_d:
            prev_d = d
            continue

        results.append({
            'createdAt': d.created_at,
            'batteryLevel': d.charge_state__battery_level,
            'batteryLevelKWh': d.battery_soc_kwh,
            'diffBatteryLevelKWh': prev_d.battery_soc_kwh - d.battery_soc_kwh,
            'odo': d.vehicle_state__odometer,
            'diffOdo': prev_d.vehicle_state__odometer - d.vehicle_state__odometer,
            'batteryRange': d.charge_state__battery_range,
            'estBatteryRange': d.charge_state__est_battery_range,
            'idealBatteryRange': d.charge_state__ideal_battery_range,
            'diffBatteryRange': prev_d.charge_state__battery_range - d.charge_state__battery_range,
            'diffEstBatteryRange': prev_d.charge_state__est_battery_range - d.charge_state__est_battery_range,
            'diffIdealBatteryRange': prev_d.charge_state__ideal_battery_range - d.charge_state__ideal_battery_range,
        })

        prev_d = d

    results.reverse()
    return JsonResponse({'items': results})
