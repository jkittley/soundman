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
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

from sd_store.models import SensorReading, UserProfile, Sensor, EepromSensorReading, Channel
from sensors.models import *
from datetime import datetime, timedelta

import zipfile
import os
from subprocess import check_output
import re
import json
import csv
from django.db.transaction import atomic

class Command(BaseCommand):
    help = 'Convert utilita data to CSV'
    
    def export_data(self, obj, filename):
        outfilename = filename.replace(".txt",".csv")
        with open(outfilename, 'wb') as csvfile:
            csvwriter = csv.writer(csvfile)

            header = ['ServicePointNo', 'SupplyType', 'DeviceNo', 'ProfileType', 'ParameterCode', 'IntervalPeriod', 'Timestamp', 'Value']


            spn = obj['ServicePointNo']
            st = obj['SupplyType']
            dn = obj['DeviceNo']
            pt = obj['ProfileType']
            pc = obj['ParameterCode']
            ip = obj['IntervalPeriod']
            
            csvwriter.writerow(header)

            for reading in obj['ProfileData']:
                timestamp = datetime.strptime(reading['Time'], '%Y-%m-%dT%H:%M:%SZ')
                if 'Value' in reading:
                    value = float(reading['Value'])
                    csvwriter.writerow([spn,st,dn,pt,pc,ip,timestamp,value])


    def add_arguments(self, parser):
        parser.add_argument('file', nargs='+', type=str)

    @atomic
    def handle(self, *args, **options):
        for filename in options['file']:
            outname = filename.replace('.txt','.csv')
            if os.path.isfile(outname):
                continue

            print(filename)
            f= open(filename)
            contents = f.read().strip()
            if contents.endswith(','):
                contents = contents[:-1]
            contents = '{'+contents
            contents = contents +']}'
            f.close()
            obj = json.loads(contents)

            self.export_data(obj, filename)