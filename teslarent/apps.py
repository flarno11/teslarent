import sys
import logging
from django.apps import AppConfig


class TeslaRentConfig(AppConfig):
    name = 'teslarent'
    verbose_name = "Tesla Rent"

    # TODO not used and not needed anymore? runserver also trigger wsgi.py
    def ready(self):
        # prevent running from tests and other commands
        # if len(sys.argv) == 1 and (sys.argv[0] == 'mod_wsgi' or sys.argv[0] == 'runserver'):
        if len(sys.argv) == 1 and sys.argv[0] == 'runserver':
            from teslarent.management.commands.rental_start_end import BackgroundTask
            logging.getLogger('manage').debug('init teslarent, ensure background task is running')
            BackgroundTask.Instance().ensure_thread_running()
