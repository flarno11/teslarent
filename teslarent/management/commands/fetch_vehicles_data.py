import datetime
import time
import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from teslarent.models import Vehicle, VehicleData
from teslarent.teslaapi.teslaapi import ApiException, wake_up, list_vehicles, fetch_and_save_vehicle_state

log = logging.getLogger('manage')


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
        list_vehicles_result = {}
        vehicles = Vehicle.get_all_active_vehicles()
        for vehicle in vehicles:
            if 'vehicle_id' in options and options['vehicle_id'] and vehicle.id != options['vehicle_id']:
                continue

            log.debug("vehicle.tesla_id={} vehicle={}".format(vehicle.tesla_id, vehicle))
            fifteen_minutes_ago = timezone.now() - datetime.timedelta(minutes=15)  # vehicle sleeps after 10-15min of inactivity
            recent_vehicle_data = VehicleData.objects\
                .filter(vehicle=vehicle)\
                .filter(created_at__gte=fifteen_minutes_ago)\
                .order_by('-created_at')
            if not options['wakeup'] and len(recent_vehicle_data) > 0:
                all_stopped = all([d.drive_state__speed is None for d in recent_vehicle_data])
                all_locked = all([d.vehicle_state__locked == True for d in recent_vehicle_data])
                all_online = all([d.is_online for d in recent_vehicle_data])
                all_disconnected_or_finished_charging = all([d.charge_state__charging_state != 'Charging' for d in recent_vehicle_data])
                log.debug("vehicle.tesla_id={} len={} all_stopped={} all_locked={} all_online={} all_disconnected_or_finished_charging={}"\
                          .format(vehicle.tesla_id, len(recent_vehicle_data), all_stopped, all_locked, all_online, all_disconnected_or_finished_charging))
                if all_stopped and all_online and all_disconnected_or_finished_charging:
                    log.debug("vehicle='{}' vehicle.tesla_id={} skip".format(vehicle, vehicle.tesla_id))
                    continue

            try:
                fetch_and_save_vehicle_state(vehicle)
            except ApiException as e:
                log.debug("vehicle.tesla_id={} exception={}".format(vehicle.tesla_id, str(e)))
                if options['wakeup']:
                    try:
                        wake_up(vehicle.tesla_id, vehicle.credentials)
                        time.sleep(10)

                        fetch_and_save_vehicle_state(vehicle)
                    except ApiException as e:
                        log.debug("vehicle.tesla_id={} exception={}".format(vehicle.tesla_id, str(e)))
                else:
                    if not vehicle.credentials.email in list_vehicles_result:
                        list_vehicles_result[vehicle.credentials.email] = list_vehicles(vehicle.credentials)  # this call shouldn't keep the vehicle awake
                    d = list(filter(lambda x: x['id'] == vehicle.tesla_id, list_vehicles_result[vehicle.credentials.email]))

                    vehicle_data = VehicleData()
                    vehicle_data.vehicle = vehicle
                    vehicle_data.data = d[0]
                    vehicle_data.save()
