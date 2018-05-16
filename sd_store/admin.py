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

from sd_store.models import SensorChannelPair, Annotation, StudyInfo, SensorReading, Event, Goal,\
    EventType, Channel, Sensor, UserProfile, RawDataKey, EepromSensorReading, Baseline, SensorGroup

from django.contrib import admin
from datetime import datetime, timedelta
from import_export import resources
from import_export.admin import ImportExportModelAdmin

# Export Resources - http://django-import-export.readthedocs.io/
class SensorReadingResource(resources.ModelResource):
    class Meta:
        model = SensorReading

class SensorResource(resources.ModelResource):
    class Meta:
        model = Sensor

class ChannelResource(resources.ModelResource):
    class Meta:
        model = Channel


# Model Admin
class StudyInfoInline(admin.StackedInline):
    model = StudyInfo
    extra = 0

class RawDataKeyAdmin(admin.ModelAdmin):
    fields = ('value',)


class RawDataKeyInline(admin.TabularInline):
    model = RawDataKey.sensors.through
    extra = 1


class SensorAdmin(ImportExportModelAdmin):

    def has_recent_data(self, obj):
        recently = datetime.now() - timedelta(hours=24)
        readings = SensorReading.objects.filter(
            sensor=obj).filter(timestamp__gte=recently)
        return readings.count() > 0
    has_recent_data.boolean = True

    inlines = [RawDataKeyInline, ]
    fieldsets = [
        ('Fields',            {'fields': [
         'mac', 'user', 'sensor_type', 'name', 'channels']}),
    ]
    list_display = ('name', 'user', 'mac', 'has_recent_data')
    search_fields = ('user__username',)
    ordering = ('name',)

class ChannelAdmin(ImportExportModelAdmin):
    list_display = ('name', 'unit')

class SensorReadingAdmin(ImportExportModelAdmin):
    resource_class = SensorReadingResource
    fieldsets = [
        ('Fields',            {'fields': [
         'timestamp', 'sensor', 'value', 'channel']}),
    ]
    list_display = ('timestamp', 'sensor', 'channel', 'value')
    list_filter = ('timestamp', 'sensor', 'channel')
    search_fields = ('sensor__user__username', 'channel')


class EepromSensorReadingAdmin(admin.ModelAdmin):
    fieldsets = [
        ('Fields',            {'fields': [
         'timestamp', 'sensor', 'value', 'index', 'channel']}),
    ]
    list_display = ('timestamp', 'sensor', 'channel', 'value', 'index')
    search_fields = ('sensor__user__username', 'channel')


class EventTypeAdmin(admin.ModelAdmin):
    fieldsets = [
        ('Fields',              {'fields': ['name', 'icon', 'alt_icon']}),
    ]


class EventAdmin(admin.ModelAdmin):
    fieldsets = [
        ('Fields',
         {
             'fields': ['event_type', 'name', 'description', 'sensor', 'start', 'end']
         }),
    ]
    list_display = ('name', 'sensor', 'start', 'end')


class GoalAdmin(admin.ModelAdmin):
    fieldsets = [
        ('Fields',            {'fields': [
         'name', 'description', 'user', 'start', 'end', 'consumption']}),
    ]


class StudyInfoAdmin(admin.ModelAdmin):
    # fieldsets = [
    #    ('Fields',              {'fields': ['user', 'baseline_consumption', 'start_date']}),
    #]
    # , 'calculate_reward')
    list_display = ('user', 'initial_credit',
                    'baseline_consumption', 'start_date')


# class BookingAdmin(admin.ModelAdmin):
#    fieldsets = [
#        ('Fields',              {'fields': ['user', 'name', 'start', 'load', 'price', 'duration']}),
#    ]
#    list_display = ('user', 'name', 'start', 'duration', 'price', 'load')

#admin.site.register(AlertMeUser, AlertmeUserAdmin)
admin.site.register(Sensor, SensorAdmin)
admin.site.register(Channel, ChannelAdmin)
admin.site.register(SensorReading, SensorReadingAdmin)
admin.site.register(EepromSensorReading, EepromSensorReadingAdmin)
admin.site.register(Event, EventAdmin)
admin.site.register(Goal, GoalAdmin)
admin.site.register(EventType, EventTypeAdmin)
admin.site.register(RawDataKey, RawDataKeyAdmin)
admin.site.register(StudyInfo, StudyInfoAdmin)
admin.site.register(UserProfile)
admin.site.register(Baseline)
admin.site.register(SensorGroup)
admin.site.register(Annotation)
admin.site.register(SensorChannelPair)
