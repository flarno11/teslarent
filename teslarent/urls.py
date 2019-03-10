from django.contrib import admin
from django.urls import path

from teslarent import views

admin.autodiscover()


urlpatterns = [
    path('api/<uuid:uuid>', views.info),
    path('api/<uuid:uuid>/hvacStart', views.hvac_start),
    path('api/<uuid:uuid>/hvacStop', views.hvac_stop),
    path('api/<uuid:uuid>/hvac/temperature/<int:temperature>', views.hvac_set_temperature),
]
