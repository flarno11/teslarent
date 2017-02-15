from django.conf.urls import include, url
from django.core import serializers
from django.contrib import admin

from teslarent import views

admin.autodiscover()


urlpatterns = [
    url(r'^$', views.index, name='index'),

    url(r'^api/(?P<uuid>[\w\-]+)', views.info),
    url(r'^api/(?P<uuid>[\w\-]+)/hvacStart$', views.hvac_start),
    url(r'^api/(?P<uuid>[\w\-]+)/hvacStop$', views.hvac_stop),
    url(r'^api/(?P<uuid>[\w\-]+)/hvac/temperature/(?P<temperature>[0-9]+)$', views.hvac_set_temperature),
]
