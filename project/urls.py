from django.conf.urls import include, url

from django.contrib import admin
import teslarent.admin_urls
import teslarent.urls

admin.autodiscover()


urlpatterns = [
    url(r'^$', teslarent.views.index, name='index'),
    url(r'^rental/', include(teslarent.urls)),
    url(r'^manage/', include(teslarent.admin_urls)),
    url(r'^admin/', include(admin.site.urls)),
]
