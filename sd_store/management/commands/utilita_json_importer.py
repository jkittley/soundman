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

from django.db.transaction import atomic

elec = {
    '2200015431214': 'UA',
    '2200016708730': 'UC',
    '2200016635151': 'UD',
    '2200015416829': 'UE',
    '2200015445750': 'UH',
    '2200017807760': 'UM',
    '2200017474948': 'UL',
    '2200017461683': 'UJ',
    '2200015423862': 'UN',
    '2200017431847': 'UK',
}

# Steele UJ
# Semaine UL
# Soares UM
# Nixon UN
# Lovell UK

gas = {
    '8841363402': 'UA',
    '4174159601': 'UC',
    '9206153200': 'UE',
    '4184851002': 'UM',
    '4174730702': 'UJ',
    '4199997702': 'UN',
    '4171434200': 'UK',
}

datastore = '/tmp/data'
datasource = 'chariot@rollins.mrl.nottingham.ac.uk:/home/chariot/*.zip'

class Command(BaseCommand):
    help = 'Import utilita data'
    
    def load_data(self, obj):
        spn = obj['ServicePointNo']
        st = obj['SupplyType']

        if 'Electricity' in st:
            if not spn in elec:
                print( "Unknown elec spn",spn)
                return
            sensor = Sensor.objects.get(mac=elec[spn])
            channel = Channel.objects.get(name='ELEC')
        elif 'Gas' in st:
            if not spn in gas:
                print( "Unknown gas spn",spn)
                return
            sensor = Sensor.objects.get(mac=gas[spn])
            channel = Channel.objects.get(name='GASS')
        valid_deployments = SensorDeploymentDetails.objects.filter(sensor=sensor, active=True)
        if len(valid_deployments) == 0:
            return

        deployment_details = SensorDeploymentDetails.objects.filter(sensor=sensor, active=True)[0] 
        for reading in obj['ProfileData']:
            timestamp = datetime.strptime(reading['Time'], '%Y-%m-%dT%H:%M:%SZ')
            value = float(reading['Value'])*2.0
            try:
                sensor_reading = SensorReading.objects.create(value=value, sensor=sensor, channel=channel, timestamp=timestamp)
                sensor_reading.save()
                deployment_details.sensor_readings.add(sensor_reading)
            except:
                continue

    @atomic
    def handle(self, *args, **options):
        output = check_output(["rsync", "-a", datasource, datastore, "--itemize-changes"])
        lines = output.split("\n")

        r = re.compile(r'^(\S+)\s((\d+)\.zip)$')

        for line in lines:
            line = line.strip()
            if r.match(line):
                result = r.match(line)
                zipname = result.groups()[1]
                path = os.path.join(datastore, zipname)
                zf = zipfile.ZipFile(path)
                files = zf.namelist()
                for filename in files:
                    f= zf.open(filename)
                    contents = f.read()
                    f.close()
                    try:
                        obj = json.loads(contents)
                    except:
                        obj = json.loads('{'+contents)
                    self.load_data(obj)