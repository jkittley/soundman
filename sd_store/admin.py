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

#import alertme

from django.contrib import admin
from datetime import datetime, timedelta
#from django.contrib.auth.admin import UserAdmin
#from django.contrib.auth.forms import UserCreationForm
#from django.utils.translation import ugettext_lazy as _
#from django import forms

# class AlertMeUserAdminForm(forms.ModelForm):
#    class Meta:
#        model = AlertMeUser
#    password = forms.CharField( help_text=_("Use '[algo]$[salt]$[hexdigest]' or use the <a href=\"password/\">change password form</a>."))


class StudyInfoInline(admin.StackedInline):
    model = StudyInfo
    extra = 0

# class AlertMeUserAdmin(UserAdmin):
#
#    fieldsets = [
#        ('Essentials',          {'fields': ['username', 'password', 'alertme_password']}),
#        (_('Groups'), {'fields': ('groups',)}),
#        ('Name',                {'fields': ['first_name', 'last_name'], 'classes': ['collapse']}),
#        ('AlertMe settings',    {'fields': ['user_level', 'web_version', 'registration_date', 'energy_price', 'status', 'access', 'settings', 'swingometer_shared'], 'classes': ['collapse']}),
#        ('Preferences',            {'fields': ['language', 'currency', 'timezone', 'daylight_saving', 'temperature_format', 'date_format', 'time_format'], 'classes': ['collapse']}),
#        ('Sharing',             {'fields': ['fe_sharing', 'fe_allowed_users', 'facebook_sharing', 'facebook_allowed_users'], 'classes': ['collapse']}),
#    ]
#
#    inlines = [StudyInfoInline]
#    form = AlertMeUserAdminForm
#    list_display = ('username', 'recent_data', 'no_events', 'control_group', 'baseline_consumption', 'start_date', 'last_login')


class RawDataKeyAdmin(admin.ModelAdmin):
    fields = ('value',)


class RawDataKeyInline(admin.TabularInline):
    model = RawDataKey.sensors.through
    extra = 1


class SensorAdmin(admin.ModelAdmin):

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


class SensorReadingAdmin(admin.ModelAdmin):
    fieldsets = [
        ('Fields',            {'fields': [
         'timestamp', 'sensor', 'value', 'channel']}),
    ]
    list_display = ('timestamp', 'sensor', 'channel', 'value')
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
admin.site.register(Channel)
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
