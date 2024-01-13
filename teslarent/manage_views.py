import base64
import logging
import uuid
from json import encoder

from django.conf import settings
from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse, HttpResponseForbidden
from django.http.response import JsonResponse
from django.shortcuts import redirect, render
from jsonview.decorators import json_view


from teslarent.forms import CredentialsForm, RentalForm, TeslaAuthForm
from teslarent.management.commands.rental_start_end import BackgroundTask
from teslarent.models import *
from teslarent.teslaapi import teslaapi
from teslarent.teslaapi.teslaapi import get_auth_url, generate_code_verifier, generate_oauth_state, get_code_challenge

encoder.FLOAT_REPR = lambda o: format(o, '.2f')  # monkey patching https://stackoverflow.com/questions/1447287/format-floats-with-standard-json-module


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
        content.append('vehicle{{id="{}", vehicle_id="{}", mobile_enabled="{}"}} 1'.format(vehicle.tesla_id, vehicle.vehicle_id, int(vehicle.mobile_enabled is True)))

        latest_vehicle_data_any = VehicleData.objects.filter(vehicle=vehicle).order_by('-created_at').first()
        if not latest_vehicle_data_any:
            continue

        latest_vehicle_data_online = VehicleData.objects.filter(vehicle=vehicle).filter(data__state='online').order_by('-created_at').first()

        content.append('vehicle_updated_at{vehicle="' + str(vehicle.vehicle_id) + '"} ' + str(latest_vehicle_data_any.created_at.timestamp()))
        content.append('vehicle_offline{vehicle="' + str(vehicle.vehicle_id) + '"} ' + ('1' if latest_vehicle_data_any.is_offline else '0'))

        if latest_vehicle_data_online:
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

    earnings_total_price_netto = 0
    earnings_total_price_charging = 0
    earnings_total_distance_driven = 0
    for r in rentals:
        if r.price_netto and r.distance_driven:  # only sum up if a price and distance is set
            earnings_total_price_netto += r.price_netto
            if r.price_charging:
                earnings_total_price_netto -= r.price_charging
                earnings_total_price_charging += r.price_charging

            earnings_total_distance_driven += r.distance_driven

    earnings_per_km = round(earnings_total_price_netto/earnings_total_distance_driven, 2) if earnings_total_distance_driven != 0 else 0

    totals = {
        'distance_driven_all': sum_non_null(lambda r: r.distance_driven, rentals),
        'distance_driven_paid': earnings_total_distance_driven,
        'price_brutto': sum_non_null(lambda r: r.price_brutto, rentals),
        'price_netto': sum_non_null(lambda r: r.price_netto, rentals),
        'price_charging_all': round(sum_non_null(lambda r: r.price_charging, rentals), 2),
        'price_charging_paid': round(earnings_total_price_charging, 2),
        'earnings_per_km': earnings_per_km,
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
def add_credentials_step1(request):
    if request.method == "POST":
        form = CredentialsForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            return redirect('manage:add-credentials-step2', email=email)
    else:
        form = CredentialsForm()

    context = dict(
        each_context(request, title="Add Credentials"),
        form=form,
    )
    return render(request, 'add_credentials_step1.html', context)


@staff_member_required
def add_credentials_step2(request, email):
    if request.method == "POST":
        form = TeslaAuthForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            c = Credentials.objects.filter(email=email).first()
            if not c:
                c = Credentials(email=email)

            auth_code = form.cleaned_data['auth_code']
            code_verifier = form.cleaned_data['code_verifier']
            teslaapi.login_and_save_credentials(c, auth_code, code_verifier)

            teslaapi.load_vehicles(c, wake_up_vehicle=True)
            return redirect('manage:index')
        tesla_auth_url = ''
    else:
        code_verifier = generate_code_verifier()
        tesla_auth_url = get_auth_url(get_code_challenge(code_verifier), generate_oauth_state(), email)
        form = TeslaAuthForm(initial={'email': email, 'code_verifier': code_verifier})

    context = dict(
        each_context(request, title="Add Credentials"),
        form=form,
        tesla_auth_url=tesla_auth_url,
    )
    return render(request, 'add_credentials_step2.html', context)


@staff_member_required
def delete_credentials(request, credentials_id):
    c = Credentials.objects.get(id=credentials_id)
    if request.method == "POST":
        c.delete()
        return redirect('/manage/')
    context = dict(
        each_context(request, title="Delete Credentials"),
        credential=c,
    )
    return render(request, 'delete_credentials.html', context)


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
