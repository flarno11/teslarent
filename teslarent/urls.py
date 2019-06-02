from django.contrib import admin
from django.urls import path

from teslarent import views

admin.autodiscover()


urlpatterns = [
    path('config.js', views.config),
    path('api/<uuid:uuid>', views.info),
    path('api/<uuid:uuid>/hvacStart', views.hvac_start),
    path('api/<uuid:uuid>/hvacStop', views.hvac_stop),
    path('api/<uuid:uuid>/hvac/temperature/<int:temperature>', views.hvac_set_temperature),
    path('api/<uuid:uuid>/nearbyCharging', views.nearby_charging),
    path('api/<uuid:uuid>/navigationRequest', views.navigation_request),
    path('api/<uuid:uuid>/vehicleLock', views.vehicle_lock),
    path('api/<uuid:uuid>/vehicleOpenFrunk', views.vehicle_open_frunk),
]
