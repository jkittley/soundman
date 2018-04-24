from django.conf.urls import url
from . import views

urlpatterns = [
    url('server/time/$', views.server_time, name='server_time'),
    url('$', views.index, name='index'),
]