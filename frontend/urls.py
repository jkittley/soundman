from django.conf.urls import url
from . import views

urlpatterns = [
    url('server/time/$', views.server_time, name='server_time'),
    url('plot/timeseries/$', views.timeseries, name='timeseries'),
    url('plot/calendar/$', views.CalendarView.as_view()),
    url('$', views.index, name='index'),
]