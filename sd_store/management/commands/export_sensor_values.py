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

import os, csv
from datetime import timedelta, datetime
from django.core.management.base import BaseCommand
from sd_store.models import Sensor, SensorReading
#from basicutils.general import total_seconds

class Command(BaseCommand):
    # args = '<poll_id poll_id ...>'
    help = 'creates a file system directory tree representing the sensors and channels'

    def handle(self, *args, **options):
        print("exporting sensors.. \n")
        #self.stdout.write("please wait, this can take few minutes\n\n")
        basedir = 'data_export'
        
        start = SensorReading.objects.first().timestamp
        start = datetime(start.year, start.month, start.day)
        end = SensorReading.objects.last().timestamp
        end = datetime(end.year, end.month, end.day)
        totalDays = int( (end - start).total_seconds() / (24*60*60.0) )
        
        #ids = [2L, 11L, 12L, 13L, 14L, 15L, 16L, 17L, 18L, 19L, 20L, 21L, 22L, 23L, 24L, 25L, 26L, 27L, 28L, 29L]
        for s in Sensor.objects.all():
            for ch in s.channels.all():
                # export one day at a time saving it in the csv file
                dirname = os.path.join(basedir, str(s.id), ch.name)
                print (dirname)
                for d in range(totalDays):
                    curr = start + timedelta(days=d)
                    currEnd = curr + timedelta(days=1)
                    selection = SensorReading.objects.filter(sensor=s,channel=ch,timestamp__gte=curr,timestamp__lt=currEnd)
                    # if the selection is empty, skip
                    if not selection.exists():
                        print('skipping (empty)')
                        continue
                    dateString = curr.strftime('%Y_%m_%d.csv')
                    print(dateString)
                    filename = os.path.join(dirname, dateString)
                    # check if we already saved this day (if so, skip)
                    if os.path.exists(filename):
                        print('skipping (file exists)')
                        continue
                    # fetch the data and dump it to a file
                    currentData = selection.values_list('timestamp','value')
                    with open(filename, 'w', newline='') as f:
                        writer = csv.writer(f)
                        writer.writerows(currentData)
                    

        print("\n..done\n")
