import sys
from django.apps import AppConfig


class TeslaRentConfig(AppConfig):
    name = 'teslarent'
    verbose_name = "Tesla Rent"

    def ready(self):
        # prevent running from tests and other commands
        # if len(sys.argv) == 1 and (sys.argv[0] == 'mod_wsgi' or sys.argv[0] == 'runserver'):
        if len(sys.argv) == 2 and sys.argv[1] == 'runserver':
            pass
