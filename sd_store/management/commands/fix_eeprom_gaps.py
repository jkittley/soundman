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

from sd_store.sdutils import get_meter, NoPrimaryMeterException, find_reading_position
from sd_store.models import SensorReading, UserProfile, Sensor, EepromSensorReading
from django.db.transaction import atomic
from datetime import datetime, timedelta

class Command(BaseCommand):
    help = 'Convert EEPROM readings into sensor readings'


    def add_arguments(self, parser):
        parser.add_argument('--sensor',
            dest='sensor',
            default=False,
            help='Select a specific sensor ID')
    
    @atomic
    def handle(self, *args, **options):
        sensor = Sensor.objects.get(id=options['sensor'])
        freq = 300
        eeprom_readings = EepromSensorReading.objects.filter(sensor=sensor).order_by('timestamp')
        
        since = None
        for eeprom_reading in eeprom_readings:
            ts = find_reading_position(eeprom_reading, freq, since)
            if not ts:
                print( "Can't insert EEPROM value",eeprom_reading.timestamp)
            else:
                since = ts
                position = ts + timedelta(seconds=freq)
                print( "Inserting EEPROM value at",position)
                # raw_input("Continue?")
                (created, sensor_reading) = SensorReading.objects.get_or_create(sensor=eeprom_reading.sensor, channel=eeprom_reading.channel, value=eeprom_reading.value, timestamp=position)
                if not created:
                    print( "Already exists")
       