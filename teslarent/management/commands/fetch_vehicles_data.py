import datetime
import time
import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from teslarent.models import Vehicle, VehicleData, Credentials
from teslarent.teslaapi.teslaapi import get_vehicle_data, ApiException, wake_up, print_vehicles, list_vehicles

log = logging.getLogger('backgroundTask')


class Command(BaseCommand):
    help = 'Update state of all linked vehicles'

    def add_arguments(self, parser):
        parser.add_argument('--wakeup',
                            action='store_true',
                            dest='wakeup',
                            default=False,
                            help='Wake up vehicle if asleep')
        parser.add_argument('--vehicleid',
                            dest='vehicle_id',
                            default=None,
                            help='Only update selected vehicle')

    def handle(self, *args, **options):
        list_vehicles_result = None
        vehicles = Vehicle.objects.filter(linked=True)
        for vehicle in vehicles:
            if 'vehicle_id' in options and options['vehicle_id'] and vehicle.id != options['vehicle_id']:
                continue

            fifteen_minutes_ago = timezone.now() - datetime.timedelta(minutes=15)  # vehicle sleeps after 10-15min of inactivity
            recent_vehicle_data = VehicleData.objects\
                .filter(vehicle=vehicle)\
                .filter(created_at__gte=fifteen_minutes_ago)\
                .order_by('-created_at')
            if not options['wakeup'] and len(recent_vehicle_data) > 0:
                all_stopped = all([d.drive_state__speed is None for d in recent_vehicle_data])
                all_online = all([d.is_online for d in recent_vehicle_data])
                all_disconnected_or_finished_charging = all([d.charge_state__charging_state != 'Charging' for d in recent_vehicle_data])
                log.debug("len={} all_stopped={} all_online={} all_disconnected_or_finished_charging={}"\
                          .format(len(recent_vehicle_data), all_stopped, all_online, all_disconnected_or_finished_charging))
                if all_stopped and all_online and all_disconnected_or_finished_charging:
                    continue

            vehicle_data = VehicleData()
            vehicle_data.vehicle = vehicle

            try:
                vehicle_data.data = get_vehicle_data(vehicle.id, vehicle.credentials)
                vehicle_data.save()
            except ApiException as e:
                print(str(e))
                if options['wakeup']:
                    try:
                        wake_up(vehicle.id, vehicle.credentials)
                        time.sleep(10)

                        vehicle_data.data = get_vehicle_data(vehicle.id, vehicle.credentials)
                        vehicle_data.save()
                    except ApiException as e:
                        print(str(e))
                else:
                    if not list_vehicles_result:
                        list_vehicles_result = list_vehicles(vehicle.credentials)  # this call shouldn't keep the vehicle awake
                    d = list(filter(lambda x: x['id'] == vehicle.id, list_vehicles_result))
                    vehicle_data.data = d[0]
                    vehicle_data.save()
