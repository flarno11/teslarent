import logging
from json import encoder

from django.contrib.admin.views.decorators import staff_member_required
from django.http.response import JsonResponse
from django.shortcuts import render

from teslarent.manage_views import each_context
from teslarent.models import *

encoder.FLOAT_REPR = lambda o: format(o, '.2f')  # monkey patching https://stackoverflow.com/questions/1447287/format-floats-with-standard-json-module

log = logging.getLogger('manage')


@staff_member_required
def charge_stats(request, vehicle_id):
    context = dict(
        each_context(request),
        vehicle_id=vehicle_id,
        vehicle=Vehicle.objects.get(pk=vehicle_id),
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
