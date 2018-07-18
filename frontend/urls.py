from django.conf.urls import url
from . import views

urlpatterns = [
    url('server/time/$', views.server_time, name='server_time'),
    url('picker/$', views.picker, name='picker'),

    url('plot/vu/$', views.vumeters, name='vumeters'),

    url('plot/refresh/vu/$', views.vu_refresh, name='vu_refresh'),
    url('plot/refresh/numbers/$', views.num_refresh, name='num_refresh'),

    url('plot/time/$', views.time, name='time'),
    url('plot/timeseries/$', views.timeseries, name='timeseries'),
    url('plot/calendar/$', views.CalendarView.as_view(), name='calendar'),
    url('$', views.index, name='index'),
]