import logging
import uuid
import datetime

from django.conf import settings
from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse
from django.http.response import Http404, JsonResponse
from django.shortcuts import redirect, render
from jsonview.decorators import json_view

from teslarent.forms import CredentialsForm, RentalForm
from teslarent.management.commands.rental_start_end import BackgroundTask
from teslarent.models import *
from teslarent.teslaapi import teslaapi

log = logging.getLogger('manage')

@json_view
def ping(request):
    #t = BackgroundTask.Instance()
    #t.ensure_thread_running()
    #return JsonResponse({'initialized_at': t.initialized_at})
    return JsonResponse({'initialized_at': None})


def each_context(request):
    return {
        'title': "Title",
        'site_title': "Tesla Rental Admin",
        'site_header': "Tesla Rental Admin",
        'has_permission': admin.site.has_permission(request),
    }


def metrics(request):
    content = []

    vehicles = Vehicle.objects.all()
    for vehicle in vehicles:
        latest_vehicle_data = VehicleData.objects.filter(vehicle=vehicle).order_by('-created_at')[0]

        content.append('vehicle_updated_at{vehicle="' + str(vehicle.id) + '"} ' + str(latest_vehicle_data.created_at.timestamp()))

        if latest_vehicle_data.is_offline:
            content.append('vehicle_offline{vehicle="' + str(vehicle.id) + '"} 1')
        else:
            content.append('vehicle_offline{vehicle="' + str(vehicle.id) + '"} 0')

    content.append('')
    return HttpResponse("\n".join(content), content_type='text/plain')


@staff_member_required
def index(request):
    now = timezone.now()

    vehicles = Vehicle.objects.all()
    context = dict(
        each_context(request),
        debug=bool(settings.DEBUG),
        active_rentals=Rental.objects.filter(start__lte=now, end__gte=now).order_by('start'),
        upcoming_rentals=Rental.objects.filter(start__gt=now).order_by('start'),
        past_rentals=Rental.objects.filter(end__lt=now).order_by('-start'),
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
        each_context(request),
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
        each_context(request),
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

    teslaapi.update_all_vehicles()
    return redirect('/manage/')


@staff_member_required
def add_rental(request):
    vehicles = Vehicle.get_all_active_vehicles()
    if len(vehicles) == 0:
        # TODO show error message to user
        log.warn("Cannot add rental, there is no active vehicle")
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
        each_context(request),
        form=form,
    )
    return render(request, 'edit_rental.html', context)


@staff_member_required
def charge_stats(request, vehicle_id):
    context = dict(
        each_context(request),
        vehicle_id=vehicle_id,
    )
    return render(request, 'charge_stats.html', context)


@staff_member_required
def charge_stats_data(request, vehicle_id, offset, limit):
    results = []
    previous_battery_level = None
    for d in VehicleData.objects\
            .filter(vehicle_id=vehicle_id)\
            .filter(data__charge_state__battery_level__isnull=False)\
            .order_by('created_at')[offset:offset + limit]:
        if not previous_battery_level or d.charge_state__battery_level != previous_battery_level:
            results.append({
                'createdAt': d.created_at,
                'batteryLevel': d.charge_state__battery_level,
                'odometer': d.vehicle_state__odometer,
            })
            previous_battery_level = d.charge_state__battery_level
    return JsonResponse({'items': results})
