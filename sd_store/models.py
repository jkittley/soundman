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

from django.db import models
from django.db.models import Max, Min, Avg, StdDev

from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
#from django.utils import simplejson as json
#from django.core.files.storage import FileSystemStorage

from basicutils.djutils import LOCALE_DATE_FMT
from django.db.utils import DatabaseError
#from django.conf import settings
try:
    from numpy import std
    with_numpy = True
except ImportError:
    with_numpy = False

#from decimal import Decimal

#fs = FileSystemStorage()

class ChannelManager(models.Manager):
    def get_by_natural_key(self, name):
        return self.get(name=name)

class Channel(models.Model):
    objects = ChannelManager()

    name = models.CharField(max_length=32)
    unit = models.CharField(_('unit of measurement'), max_length=10)
    reading_frequency = models.IntegerField(_('reading frequency in seconds'))

    def natural_key(self):
        return self.name

    def __str__(self):
        return u'%s (%d)' % (self.name, self.pk)


class SensorManager(models.Manager):
    def get_by_natural_key(self, mac):
        return self.get(mac=mac)

# should Sensor be abstract? Not clear how Django deals with abstract
# inheritance and keys ..can I iterate over all instances inheriting from abstract?
class Sensor(models.Model):
    objects = SensorManager()

    mac = models.CharField(_('ID number'), max_length=30, unique=True, db_index=True)
    sensor_type = models.CharField(_('sensor type'), max_length=30)
    name = models.CharField(_('metering source'), max_length=30)
    user = models.ForeignKey(User)

    channels = models.ManyToManyField(Channel)

    hidden_fields = ('sensor_ptr',)

    def __str__(self):
        return u'%s [%s]' % (self.name, self.mac)

    def natural_key(self):
        return self.mac

class SensorGroup(models.Model):
    name = models.CharField(max_length=64)
    description = models.CharField(_('description'), max_length=1024, blank=True)
    sensors = models.ManyToManyField(Sensor)
    user = models.ForeignKey(User)



class EepromSensorReading(models.Model):
    timestamp = models.DateTimeField(db_index=True)
    sensor = models.ForeignKey(Sensor, db_index=True)
    channel = models.ForeignKey(Channel, db_index=True)
    value = models.FloatField(_('value'),default=0)
    index = models.IntegerField(default=0)

    class Meta:
        ordering = ['timestamp']
        unique_together = (('timestamp', 'sensor', 'channel'),)

    def __str__(self):
        return str(self.value) + ' @ ' + self.timestamp.strftime(LOCALE_DATE_FMT) + " - "+str(self.index)

    hidden_fields = ['sensor', 'channel', 'id']

class SensorReading(models.Model):
    timestamp = models.DateTimeField(db_index=True)
    sensor = models.ForeignKey(Sensor, db_index=True)
    channel = models.ForeignKey(Channel, db_index=True)
    value = models.FloatField(_('value'),default=0)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return str(self.value) + ' @ ' + self.timestamp.strftime(LOCALE_DATE_FMT)

    hidden_fields = ['sensor', 'channel', 'id']

class LatestSensorReading(SensorReading):
    pass

class RawDataKey(models.Model):
    value = models.CharField(max_length=32)
    sensors = models.ManyToManyField(Sensor)

    
    def __str__(self):
        return self.value
    
# this is the always-on energy
# rename to SensorBaseline ?
class Baseline(models.Model):
    date = models.DateField(db_index=True)
    sensor = models.ForeignKey(Sensor, db_index=True)
    channel = models.ForeignKey(Channel, db_index=True)
    value = models.FloatField()
    last_modified = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = (('date', 'sensor', 'channel'),)

class EventTypeManager(models.Manager):
    def get_by_natural_key(self, name):
        return self.get(name=name)

class EventType(models.Model):
    objects = EventTypeManager()

    name = models.CharField(_('icon name'), max_length=30, unique=True)

    icon = models.URLField()
    alt_icon = models.URLField()

    def natural_key(self):
        return self.name

    def __str__(self):
        return self.name

# Added by dpr1g09 -- to hold details of the predictions
class EventTypePrediction(models.Model):
    event_type = models.ForeignKey(EventType)
    certainty = models.FloatField()
    user_accepted = models.BooleanField(default=False)

class SensorChannelPair(models.Model):
    sensor = models.ForeignKey(Sensor)
    channel = models.ForeignKey(Channel)

    class Meta:
        unique_together = ("sensor", "channel")

    def __str__(self):
        return str(self.sensor.name) + ' ('+self.sensor.mac+') '+'-' + str(self.channel.name)

class Annotation(models.Model):
    start = models.DateTimeField()
    end = models.DateTimeField()
    pairs = models.ManyToManyField(SensorChannelPair)
    text = models.CharField("text", max_length=1024, blank=True)
    user = models.ForeignKey(User)



class Event(models.Model):

    # null=True because auto_detected won't initially have a type -- dpr1g09
    # TODO: change this, I am sure there is a better alternative,
    # e.g. set the type to undefined
    event_type = models.ForeignKey(EventType, null=True)
    name = models.CharField(_('unique name'), max_length=1024)
    description = models.CharField(_('description'), max_length=1024, blank=True)
    start = models.DateTimeField()
    end = models.DateTimeField()
    # user = models.ForeignKey(User)
    sensor = models.ForeignKey(Sensor)
    channel = models.ForeignKey(Channel)

    auto_detected = models.BooleanField(default=False, blank=True)

    @property
    def duration(self):
        return (self.end - self.start).total_seconds() / 60.0

    def get_readings_list(self):
        return SensorReading.objects.filter(sensor=self.sensor,
                                                    channel=self.channel,
                                                    timestamp__gte=(self.start),
                                                    timestamp__lt=(self.end))

    _maximum_power = models.FloatField(null=True, blank=True)
    @property
    def maximum_power(self):
        if self._maximum_power is None:
            #power_factor = 60 * 60.0 / self.channel.reading_frequency
            power_factor = 1.0
            self._maximum_power = power_factor * self.get_readings_list().aggregate(Max('value'))['value__max']
            self.save()
        return self._maximum_power

    _minimum_power = models.FloatField(null=True, blank=True)
    @property
    def minimum_power(self):
        if self._minimum_power is None:
            power_factor = 60 * 60.0 / self.channel.reading_frequency
            self._minimum_power = power_factor * self.get_readings_list().aggregate(Min('value'))['value__min']
            self.save()
        return self._minimum_power

    _mean_power = models.FloatField(null=True, blank=True)
    @property
    def mean_power(self):
        if self._mean_power is None:
            power_factor = 60 * 60.0 / self.channel.reading_frequency
            self._mean_power = power_factor * self.get_readings_list().aggregate(Avg('value'))['value__avg']
            self.save()
        return self._mean_power

    def __calculate_sqllite_stdev(self):
        # TODO: check the following!
        # from http://stackoverflow.com/questions/2298339/standard-deviation-for-sqlite
        # SELECT AVG((t.row-sub.a)*(t.row-sub.a)) as var from t, (SELECT AVG(row) AS a FROM t) AS sub;
#        query = """ \
#        SELECT
#            AVG((value - sub.a)*(value - sub.a)) AS value__stddev
#        FROM sd_store_sensorreading, (SELECT AVG(value) AS a FROM sd_store_sensorreading) AS sub
#        WHERE
#            sensor_id = %s AND
#            channel_id = %s AND
#            timestamp > %s AND
#            timestamp <= %s,
#
#        """
#        params = (self.sensor.pk, self.channel.pk,
#                    self.start, self.end)
#        return SensorReading.objects.raw( query, params )['value__stddev']
        readings = self.get_readings_list()
        
        if with_numpy:
            return std([x.value for x in readings])
        else:
            raise NotImplementedError

    _standard_deviation = models.FloatField(null=True, blank=True)
    @property
    def standard_deviation(self):
        if self._standard_deviation is None:
            try:
                self._standard_deviation = self.get_readings_list().aggregate(StdDev('value'))['value__stddev']
            except DatabaseError:
                self._standard_deviation = self.__calculate_sqllite_stdev()
            self.save()
        return self._standard_deviation

    @property
    def total_consumption(self):
        #return self.mean_power * self.duration * 60.0 / self.channel.reading_frequency
        return self.mean_power * self.duration / 60.0

    @property
    def hour_of_day(self): return self.start.hour

    @property
    def day_of_week(self): return self.start.weekday()

    extra_fields = ('maximum_power', 'minimum_power', 'mean_power',
                    'standard_deviation', 'total_consumption',
                    'hour_of_day', 'day_of_week')

    # the following field is for automatic detection
    # null=True should make it retro-compatible
    predictions = models.ManyToManyField(EventTypePrediction, blank=True)

    def __str__(self):
        return self.name


class Goal(models.Model):
    name = models.CharField(_('name'), max_length=30)
    description = models.CharField(_('description'), max_length=30, blank=True)
    start = models.DateTimeField()
    end = models.DateTimeField()
    user = models.ForeignKey(User)
    consumption = models.FloatField(_('total consumption during event'))

    def __unic__str__ode__(self):
        return self.name


class UserProfile(models.Model):
    user = models.ForeignKey(User)

    primary_sensor = models.ForeignKey('Sensor', blank=True, null=True)
    phone_number = models.CharField(max_length=32, blank = True, null = True)

    def baseline_consumption(self):
        return StudyInfo.objects.get(user=self).baseline_consumption

    def start_date(self):
        return StudyInfo.objects.get(user=self).start_date

    def __str__(self):
        return u"%s" % (self.user,)

        
        
class StudyInfo(models.Model):
    user = models.OneToOneField(User)
    baseline_consumption = models.FloatField()
    start_date = models.DateTimeField()
    last_modified = models.DateTimeField(auto_now=True)
    initial_credit = models.FloatField()




