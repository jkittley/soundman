# -*- coding: UTF-8 -*-

# This file is part of sd_store
#
# sd_store is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# sd_store is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with sd_store.  If not, see <http://www.gnu.org/licenses/>.

from django.conf.urls import include, url
#from django.shortcuts import render_to_response

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = [
    url('^', include('django.contrib.auth.urls')),

    url(r'^admin/', include(admin.site.urls)),
    url(r'^', include('sd_store.urls')),
]
