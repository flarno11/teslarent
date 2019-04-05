import datetime
import threading
import logging
import time
import queue

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from teslarent.models import Rental, VehicleData
from teslarent.teslaapi import teslaapi
from teslarent.utils.Singleton import Singleton


log = logging.getLogger('backgroundTask')


@Singleton
class BackgroundTask:
    thread = None
    _initialized_at = None

    def __init__(self):
        log.debug('BackgroundTask created')
        self.queue = queue.Queue()

    def ensure_thread_running(self):
        if not self.thread:
            self.thread = threading.Thread(target=self.background_process, args=(), kwargs={})
            self.thread.setDaemon(False)  # allow Django to exit while background thread is still running
            self.thread.start()

            self._initialized_at = timezone.now()
        else:
            self.queue.put(None)

    def background_process(self):
        log.debug('background_process self.thread.name=' + self.thread.name)

        while True:
            next_rental_at = Rental.get_next_rental_start_or_end_time(timezone.now())
            if not next_rental_at:
                log.debug('no next rental found, leaving for now')
                break

            now = timezone.now()
            if next_rental_at < now:
                log.error('next rental is in the past. now=%s, next_rental_at=%s' % (str(now), str(next_rental_at)))
                break

            diff = (next_rental_at - now).total_seconds()
            log.info('next rental at %s, sleeping for %d secs' % (str(next_rental_at), diff))

            try:
                self.queue.get(timeout=diff)
                log.debug('interrupted by external event')
            except queue.Empty:
                log.debug('interrupted by timeout')

            Command().update_rentals(timezone.now())

        log.debug('exiting thread')
        self.thread = None

    @property
    def initialized_at(self):
        return self._initialized_at


class Command(BaseCommand):
    help = 'Update started and ended rentals'

    def add_arguments(self, parser):
        #parser.add_argument('poll_id', nargs='+', type=int)
        pass

    def handle(self, *args, **options):
        self.update_rentals(timezone.now())

    @staticmethod
    def update_rentals(date):
        five_minutes_ago = date - datetime.timedelta(minutes=5)
        rentals_start = list(Rental.objects.filter(start__gte=five_minutes_ago, start__lte=date))
        rentals_end = list(Rental.objects.filter(end__gte=five_minutes_ago, end__lte=date))

        vehicles = set()
        for rental in rentals_start:
            if not rental.odometer_start:
                vehicles.add(rental.vehicle)

        for rental in rentals_end:
            if not rental.odometer_end:
                vehicles.add(rental.vehicle)

        vehicles = {vehicle.id: {'vehicle': vehicle} for vehicle in vehicles}
        log.debug('update rentals for vehicles=%s rentals_start=%s rentals_end=%s' % (str(vehicles), str(rentals_start), str(rentals_end)))
        for d in vehicles.values():
            vehicle = d['vehicle']
            call_command('fetch_vehicles_data', wakeup=True, vehicle_id=vehicle.id)
            latest_vehicle_data = VehicleData.objects.filter(vehicle=vehicle).order_by('-created_at')[0]
            diff = (timezone.now() - latest_vehicle_data.created_at).total_seconds()
            if diff < 20:
                d['latest_vehicle_data'] = latest_vehicle_data
            else:
                log.error('no latest vehicle data for rental %d diff=%s' % (rental.id, str(diff)))

        for rental in rentals_start:
            if not rental.odometer_start and 'latest_vehicle_data' in vehicles[rental.vehicle.id]:
                latest_vehicle_data = vehicles[rental.vehicle.id]['latest_vehicle_data']
                rental.odometer_start = latest_vehicle_data.vehicle_state__odometer
                rental.odometer_start_updated_at = date
                log.info('update rentals for rental %d start=%s' % (rental.id, str(rental.start)))
                rental.save()

        for rental in rentals_end:
            if not rental.odometer_end and 'latest_vehicle_data' in vehicles[rental.vehicle.id]:
                latest_vehicle_data = vehicles[rental.vehicle.id]['latest_vehicle_data']
                rental.odometer_end = latest_vehicle_data.vehicle_state__odometer
                rental.odometer_end_updated_at = date
                log.info('update rentals for rental %d end=%s' % (rental.id, str(rental.end)))
                rental.save()
