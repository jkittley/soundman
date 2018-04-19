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

import logging
logger = logging.getLogger('custom')

from optparse import make_option
from datetime import timedelta

import numpy as np

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

from sd_store.sdutils import get_meter, NoPrimaryMeterException
from sd_store.models import SensorReading, UserProfile, Sensor, EepromSensorReading
from django.db.transaction import atomic
from datetime import datetime, timedelta
from collections import Counter

class Command(BaseCommand):
    help = 'Convert EEPROM readings into sensor readings'


    def add_arguments(self, parser):
        parser.add_argument('--sensor',
            dest='sensor',
            default=False,
            help='Select a specific sensor ID')
    
    def place_eeprom_reading(self, reading):
        
        pass
    
    @atomic
    def handle(self, *args, **options):
        sensor = Sensor.objects.get(name='Sensor 13')
        for channel in sensor.channels.all():
            readings = EepromSensorReading.objects.filter(sensor=sensor).filter(channel=channel)
            
            it = readings.iterator()
            prev = it.next()
            curr_group = [prev,]
            lens = []
            oversized = []
            try:
                while True:
                    curr = it.next()
                    print("EEPROM:",prev.timestamp)
                    if (curr.timestamp - prev.timestamp) < timedelta(minutes=2):
                        curr_group.append(curr)
                    else:
                        # process group
                        lens.append(len(curr_group))
                        print("Group size",len(curr_group))
                        if len(curr_group) <= 5:
                            # convert group & oversized to readings
                            oversized += curr_group
                            # take the timestamp of the last sample (optionally subtract len(curr_group) * 5_seconds)
                            last_ts = oversized[-1].timestamp # could correct here.
                            k = len(oversized)
                            print('k:', k, '->')
                            ##if k < 5:
                            ##    from math import ceil
                            ##    k = int((ceil(k/5)+1) * 5)
                                #k += k % 5
                            print(k)
                            # offset to take into account the last sample is the current one at time of sending
                            k -= 1
                            first_ts = last_ts - timedelta(minutes=5) * k
                            for idx, reading in enumerate(oversized):
                                ts = first_ts + timedelta(minutes=5)*idx
                                print(ts)
                                sensor_reading = SensorReading(value=reading.value, channel=reading.channel, sensor=reading.sensor, timestamp=ts)
                                sensor_reading.save()
                            oversized = []
                        else:
                            oversized += curr_group
                        curr_group = [curr,]
                    prev = curr
            except StopIteration:
                pass
            print(Counter(lens).most_common())