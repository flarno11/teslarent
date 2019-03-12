from django.core.management.base import BaseCommand, CommandError

from teslarent.teslaapi.teslaapi import update_all_vehicles, print_vehicles


class Command(BaseCommand):
    help = 'Tesla API List and Print Vehicles'

    def add_arguments(self, parser):
        #parser.add_argument('poll_id', nargs='+', type=int)
        pass

    def handle(self, *args, **options):
        print_vehicles()
