from django.contrib import admin
from django.urls import include, path

import teslarent.urls
from teslarent import manage_views

admin.autodiscover()


urlpatterns = [
    path('', teslarent.views.index, name='index'),
    path('metrics', manage_views.metrics, name='metrics'),
    path('rental/', include('teslarent.urls')),
    path('manage/', include(('teslarent.manage_urls', 'manage'), namespace='manage')),
    path('admin/', admin.site.urls),
]
