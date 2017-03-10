import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings_prod")

from django.core.wsgi import get_wsgi_application
from whitenoise.django import DjangoWhiteNoise

application = get_wsgi_application()
application = DjangoWhiteNoise(application)


# import must be after get_wsgi_application() call
from teslarent.management.commands.rental_start_end import BackgroundTask
BackgroundTask.Instance().ensure_thread_running()
