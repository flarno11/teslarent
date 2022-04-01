import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone

from teslarent.manage_teslaapi_actions_views import refresh_credentials_do
from teslarent.models import Credentials


class Command(BaseCommand):
    help = 'Refresh expiring credentials'

    def add_arguments(self, parser):
        #parser.add_argument('poll_id', nargs='+', type=int)
        pass

    def handle(self, *args, **options):
        now = timezone.now()
        two_hours_from_now = now + datetime.timedelta(hours=2, minutes=5)
        for c in Credentials.objects.all():
            if c.token_expires_at <= two_hours_from_now:
                refresh_credentials_do(c)
