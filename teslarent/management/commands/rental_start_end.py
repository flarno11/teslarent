import datetime

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db.models import Q

from teslarent.models import Rental
from teslarent.teslaapi import teslaapi


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
        rentals_start = Rental.objects.filter(start__gte=five_minutes_ago, start__lte=date)
        rentals_end = Rental.objects.filter(end__gte=five_minutes_ago, end__lte=date)

        vehicles = set()
        for rental in rentals_start:
            if not rental.odometer_start:
                vehicles.add(rental.vehicle)

        for rental in rentals_end:
            if not rental.odometer_end:
                vehicles.add(rental.vehicle)

        vehicles = {vehicle.id: {'vehicle': vehicle} for vehicle in vehicles}
        for d in vehicles.values():
            d['state'] = teslaapi.get_vehicle_state(d['vehicle'])

        for rental in rentals_start:
            if not rental.odometer_start:
                rental.odometer_start = vehicles[rental.vehicle.id]['state']['odometer']
                rental.odometer_start_updated_at = date
                rental.save()

        for rental in rentals_end:
            if not rental.odometer_end:
                rental.odometer_end = vehicles[rental.vehicle.id]['state']['odometer']
                rental.odometer_end_updated_at = date
                rental.save()
