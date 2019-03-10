from django.contrib import admin
from django.urls import include, path

import teslarent.urls

admin.autodiscover()


urlpatterns = [
    path('', teslarent.views.index, name='index'),
    path('rental/', include('teslarent.urls')),
    path('manage/', include('teslarent.admin_urls')),
    path('admin/', admin.site.urls),
]
