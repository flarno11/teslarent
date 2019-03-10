import time

from django.core.management.base import BaseCommand

from teslarent.models import Vehicle, VehicleData
from teslarent.teslaapi.teslaapi import get_vehicle_data, ApiException, wake_up


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
