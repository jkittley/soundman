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

import os
from django.core.management.base import BaseCommand
from sd_store.models import Sensor

class Command(BaseCommand):
    # args = '<poll_id poll_id ...>'
    help = 'creates a file system directory tree representing the sensors and channels'

    def handle(self, *args, **options):
        print("exporting sensors.. \n")
        basedir = 'data_export'
        
        for s in Sensor.objects.all():
            sensorDir = os.path.join(basedir,str(s.id))
            try:
                os.makedirs(sensorDir)
            except Exception:
                print (Exception)
            for ch in s.channels.all():
                channelDir = os.path.join(sensorDir, ch.name)
                try:
                    os.makedirs(channelDir)
                except Exception:
                    print (Exception)

        print("\n..done\n")

