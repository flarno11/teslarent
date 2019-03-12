import datetime
import time
import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from teslarent.models import Vehicle, VehicleData
from teslarent.teslaapi.teslaapi import get_vehicle_data, ApiException, wake_up

log = logging.getLogger('backgroundTask')


class Command(BaseCommand):
    help = 'Update state of all linked vehicles'

    def add_arguments(self, parser):
        parser.add_argument('--wakeup',
                            action='store_true',
                            dest='wakeup',
                            default=False,
                            help='Wake up vehicle if asleep')

    def handle(self, *args, **options):
        vehicles = Vehicle.objects.filter(linked=True)
        for vehicle in vehicles:
            sixty_minutes_ago = timezone.now() - datetime.timedelta(minutes=60)
            recent_vehicle_data = VehicleData.objects.filter(vehicle=vehicle).filter(created_at__gte=sixty_minutes_ago).order_by('-created_at')[:3]
            if len(recent_vehicle_data) > 0:
                all_stopped = all([d.drive_state__speed is None for d in recent_vehicle_data])
                all_disconnected_or_finished_charging = all([d.charge_state__charging_state != 'Charging' for d in recent_vehicle_data])
                log.debug("len={} all_stopped={} all_disconnected_or_finished_charging={}".format(len(recent_vehicle_data), all_stopped, all_disconnected_or_finished_charging))

                if all_stopped and all_disconnected_or_finished_charging:
                    continue

            vehicle_data = VehicleData()
            vehicle_data.vehicle = vehicle
            try:
                vehicle_data.data = get_vehicle_data(vehicle.id, vehicle.credentials)
                vehicle_data.save()
            except ApiException as e:
                if options['wakeup']:
                    try:
                        wake_up(vehicle.id, vehicle.credentials)
                        time.sleep(10)

                        vehicle_data.data = get_vehicle_data(vehicle.id, vehicle.credentials)
                        vehicle_data.save()
                    except ApiException as e:
                        print(str(e))
                else:
                    print(str(e))
