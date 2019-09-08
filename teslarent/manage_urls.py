from django.urls import path

from teslarent import manage_views, manage_teslaapi_actions_views, manage_stats_views


urlpatterns = [
    path('', manage_views.index, name='index'),
    path('addCredentials', manage_views.add_credentials),
    path('deleteCredentials/<int:credentials_id>', manage_views.delete_credentials),
    path('refreshCredentials/<int:credentials_id>', manage_teslaapi_actions_views.refresh_credentials),

    path('vehicles/loadVehicles', manage_teslaapi_actions_views.update_vehicles, name='vehicles-load'),
    path('vehicles/<int:vehicle_id>/lockVehicle', manage_teslaapi_actions_views.lock_vehicle, name='vehicle-lock'),
    path('vehicles/<int:vehicle_id>/unlockVehicle', manage_teslaapi_actions_views.unlock_vehicle, name='vehicle-unlock'),
    path('vehicles/<int:vehicle_id>/chargeStats', manage_stats_views.charge_stats, name='vehicle-charge-stats'),
    path('vehicles/<int:vehicle_id>/chargeStatsData/<int:offset>/<int:limit>', manage_stats_views.charge_stats_data, name='vehicle-charge-stats-data'),
    path('vehicles/<int:vehicle_id>/dailyStatsData/<int:offset>/<int:limit>', manage_stats_views.daily_stats_data, name='vehicle-daily-stats-data'),
    path('vehicles/<int:vehicle_id>/rawData/<int:offset>/<int:limit>', manage_stats_views.raw_data),

    path('addRental', manage_views.add_rental),
    path('editRental/<int:rental_id>', manage_views.edit_rental),
    path('deleteRental/<int:rental_id>', manage_views.delete_rental),

    path('ping', manage_views.ping),
]
