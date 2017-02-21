import datetime
from django.conf.urls import include, url
from django.contrib import admin

from teslarent import admin_views
from teslarent.models import Rental, Credentials

urlpatterns = [
    #url(r'^$', admin.site.admin_view(admin.site.app_index), {'app_label': 'teslarent', 'extra_context': {
    #    'rentals': Rental.objects.filter(end__gte=datetime.datetime.now()),
    #    'past_rentals': Rental.objects.filter(end__lt=datetime.datetime.now()),
    #    'credentials': Credentials.objects.all(),
    #}}),
    url(r'^$', admin_views.index),
    url(r'^addCredentials$', admin_views.add_credentials),
    url(r'^deleteCredentials/(?P<credentials_id>\d+)$', admin_views.delete_credentials),
    url(r'^refreshCredentials/(?P<credentials_id>\d+)$', admin_views.refresh_credentials),
    url(r'^addRental$', admin_views.add_rental),
    url(r'^editRental/(?P<rental_id>\d+)$', admin_views.edit_rental),
    url(r'^deleteRental/(?P<rental_id>\d+)$', admin_views.delete_rental),
    url(r'^updateVehicles$', admin_views.update_vehicles),
]
