import datetime
import os

from django.urls import path
from django.contrib import admin

from teslarent import admin_views
from teslarent.models import Rental, Credentials


urlpatterns = [
    #url(r'^$', admin.site.admin_view(admin.site.app_index), {'app_label': 'teslarent', 'extra_context': {
    #    'rentals': Rental.objects.filter(end__gte=datetime.datetime.now()),
    #    'past_rentals': Rental.objects.filter(end__lt=datetime.datetime.now()),
    #    'credentials': Credentials.objects.all(),
    #}}),
    path('', admin_views.index),
    path('addCredentials', admin_views.add_credentials),
    path('deleteCredentials/<int:credentials_id>', admin_views.delete_credentials),
    path('refreshCredentials/<int:credentials_id>', admin_views.refresh_credentials),
    path('addRental', admin_views.add_rental),
    path('editRental/<int:rental_id>', admin_views.edit_rental),
    path('deleteRental/<int:rental_id>', admin_views.delete_rental),
    path('updateVehicles', admin_views.update_vehicles),

    path('ping', admin_views.ping),
]
