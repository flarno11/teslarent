from django.contrib import admin
from django.urls import include, path

import teslarent.urls
from teslarent import admin_views

admin.autodiscover()


urlpatterns = [
    path('', teslarent.views.index, name='index'),
    path('metrics', admin_views.metrics, name='metrics'),
    path('rental/', include('teslarent.urls')),
    path('manage/', include('teslarent.admin_urls')),
    path('admin/', admin.site.urls),
]
