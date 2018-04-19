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

from django.conf.urls import url
from sd_store.views import general, energy, annotations, external

urlpatterns = (
    url(r'^users/$', general.user_view),
    # url(r'^user/(?P<user_id>[-\w]+)/$','user_view),

    url(r'^sensors/$', general.sensor_view),
    url(r'^sensor/(?P<sensor_id>[-\d]+)/$', general.sensor_view),
    url(r'^sensor/(?P<sensor_id>[-\d]+)/(?P<channel_name>[-\w]+)/$',
        general.channel_view),
    url(r'^sensor/(?P<sensor_id>[-\d]+)/(?P<channel_name>[-\w]+)/data/$',
        general.data_view),
    url(r'^sensor/data/$', general.batch_data_view),
    url(r'^sensor/(?P<sensor_id>[-\d]+)/(?P<channel_name>[-\w]+)/last-reading/$',
        general.last_reading_view),
    url(r'^sensor/(?P<sensor_id>[-\d]+)/(?P<channel_name>[-\w]+)/integral/$',
        general.integral_view),
    url(r'^sensor/(?P<sensor_id>[-\d]+)/(?P<channel_name>[-\w]+)/baseline/$',
        general.baseline_view),

    url(r'^snapshot/$', general.snapshot_view),

    url(r'^sensor/(?P<sensor_mac>[-\w:]+)/$', general.sensor_view_mac),
    url(r'^sensor/(?P<sensor_mac>[-\w:]+)/(?P<channel_name>[-\w]+)/$',
        general.channel_view_mac),
    url(r'^sensor/(?P<sensor_mac>[-\w:]+)/(?P<channel_name>[-\w]+)/data/$',
        general.data_view_mac),
    url(r'^sensor/(?P<sensor_mac>[-\w:]+)/(?P<channel_name>[-\w]+)/last-reading/$',
        general.last_reading_view_mac),

    url(r'^sensor/(?P<sensor_id>[-\w:]+)/(?P<channel_name>[-\w]+)/most-recent-maximum/$',
        general.most_recent_maximum_view),
    url(r'^sensor/(?P<sensor_mac>[-\w:]+)/(?P<channel_name>[-\w]+)/most-recent-maximum/$',
        general.most_recent_maximum_view_mac),
    url(r'^sensor/(?P<sensor_id>[-\w:]+)/(?P<channel_name>[-\w]+)/regression/$',
        general.regression_view),
    url(r'^sensor/(?P<sensor_mac>[-\w:]+)/(?P<channel_name>[-\w]+)/regression/$',
        general.regression_view_mac),


    url(r'^rawinput/sensor/(?P<sensor_mac>[-\w:]+)/(?P<channel_name>[-\w]+)/data/',
        general.raw_data_view),
    url(r'^rawinput/sensor/(?P<sensor_mac>[-\w:]+)/data/',
        general.raw_data_packet_view),
    url(r'^rawinput/sensor/(?P<sensor_id>[\d]+)/register/',
        general.raw_data_register_view),
    url(r'^rawinput/sensor/(?P<sensor_mac>[-\w:]+)/signal/',
        general.raw_data_signal_view),
    url(r'^rawinput/sensor/data/$', general.raw_batch_data_view),

    url(r'^meters/$', general.meter_view),
    url(r'^meter/(?P<meter_id>[-\w]+)/$', general.meter_view),

    url(r'^sensorGroups/$', general.sensor_group_list_view),
    url(r'^sensorGroup(s?)/(?P<sensor_group_id>[\d]+)/$',
        general.sensor_group_detail_view),
    url(r'^sensorGroup(s?)/(?P<sensor_group_id>[\d]+)/sensors/$',
        general.sensor_group_sensors_list_view),
    url(r'^sensorGroup(s?)/(?P<sensor_group_id>[\d]+)/sensor/(?P<sensor_id>[-\d]+)/$',
        general.sensor_group_sensor_detail_view),
    url(r'^sensorGroup(s?)/(?P<sensor_group_id>[\d]+)/data/$',
        general.group_data_view),
    #url(r'^sensorGroup(s?)/(?P<sensor_group_id>[\d]+)/(?P<channel_name>[\w]+)/data/$', general.group_data_view),

    url(r'^eventTypes/$', general.event_type_view),
    url(r'^eventType/(?P<event_type_id>[\d]+)/$', general.event_type_view),

    url(r'^referenceConsumption/$', general.reference_consumption_view),
    # url(r'^goals','goal_view),
    # url(r'^goal/(?P<goal_id>[-\w]+)/$','goal_view),
)

urlpatterns += (
    # energy version
    url(r'^energy/data/$', energy.meter_reading_view, {'data_type': 'energy'}),

    url(r'^energy/alwaysOn/', energy.always_on_view, {'data_type': 'energy'}),
    url(r'^energy/total/', energy.total_energy_view),

    url(r'^energy/totalCost/', energy.total_energy_cost_view),

    # power version
    url(r'^power/data/$',  energy.meter_reading_view, {'data_type': 'power'}),

    url(r'^power/alwaysOn/$', energy.always_on_view, {'data_type': 'power'}),

    # general
    url(r'^eventNames/$', energy.event_names_view),
    url(r'^events/$', energy.event_view),
    url(r'^event/(?P<event_id>[\d]+)/$', energy.event_view),
    url(r'^event/$', energy.event_view),

    url(r'^liveStats/$', energy.live_stats_view),
    url(r'^savings/$', energy.savings_view),
)

urlpatterns += (
    url(r'^powerNow/$', external.power_now_view),
    url(r'^update/$', external.update_view),
    url(r'^checkAlertMeLogin/$', external.check_alertme_login_view),
)

urlpatterns += (
    url(r'^annotations/$', annotations.annotation_view),
    url(r'^annotation/(?P<annotation_id>[\d]+)/$',
        annotations.annotation_view),
    url(r'^annotation/$', annotations.annotation_view),
)

# TODO: the following methods are not compatible with the protected_store setup
#    url(r'^getEventLog','event_log_view),
#
#    url(r'^smartPlugOn','smartplug_on_view),
#    url(r'^smartPlugOff','smartplug_off_view),
#
#    url(r'^buttonFlashOn','button_flash_on_view),
#    url(r'^buttonFlashOff','button_flash_off_view),
#
#    url(r'^smartPlugState','smart_plug_state_view),
#    url(r'^toggleSmartPlug','toggle_smart_plug_view),
#
#    url(r'^toggleUserBattery','toggle_user_battery_view),
