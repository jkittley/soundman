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
from datetime import timedelta, datetime

import numpy as np

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

from sd_store.sdutils import get_meter, NoPrimaryMeterException
from sd_store.models import SensorReading, UserProfile, Sensor, EepromSensorReading, Channel
from django.db.transaction import atomic
from datetime import datetime, timedelta
import csv

class Command(BaseCommand):
    help = 'Import utilita data'
    
    def add_arguments(self, parser):
        parser.add_argument('--filename',
                            dest='filename',
                            default=False,
                            help='CSV file')
        parser.add_argument('--channel',
                            dest='channel',
                            default=False,
                            help='type')
        parser.add_argument('--sensor',
                            dest='sensor',
                            default=False,
                            help='sensor')

    @atomic
    def handle(self, *args, **options):
        sensor = Sensor.objects.get(name=options['sensor'])
        channel = Channel.objects.get(name=options['channel'])
        with open(options['filename'], 'rU') as csvfile:
            csvreader = csv.reader(csvfile)
            headers = csvreader.next()
            times = headers[5:]
            print (times)
            print ("--")
            for row in csvreader:
                date = row[0]
                values = row[5:]
                
                for idx, value in enumerate(values):
                    timestamp = datetime.strptime(date+" "+times[idx], "%d/%m/%y %H:%M")
                    print (timestamp, value)
                    sensor_reading = SensorReading.objects.create(value=value, sensor=sensor, channel=channel, timestamp=timestamp)
                    sensor_reading.save()