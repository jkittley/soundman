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

from random import random
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from ...models import Sensor, Channel, SensorGroup, SensorReading
from django.db.transaction import atomic


@atomic
class Command(BaseCommand):
    #args = '<poll_id poll_id ...>'
    help = 'Populates the db for the pricing applications'

    def handle(self, *args, **options):
        self.stdout.write("populating sd_store.. \n")
        self.stdout.write("please wait, this can take few minutes\n\n")

        # create a normal user
        u = User(username="demo")
        u.set_password('demo')
        try:
            u.save()
        except:
            pass

        # create some sensors for this user
        s1 = Sensor(mac='04:0c:ce:d0:a3:aa',
                    sensor_type='demo sensor type',
                    name='demo sensor 1',
                    user=u)
        s1.save()
        s2 = Sensor(mac='04:0c:ce:d0:a3:ab',
                    sensor_type='demo sensor type',
                    name='demo sensor 2',
                    user=u)
        s2.save()

        t_ch = Channel(name='temperature',
                       unit='degree C',
                       reading_frequency='120')
        t_ch.save()

        s1.channels.add(t_ch)
        s1.save()
        s2.channels.add(t_ch)
        s2.save()

        g = SensorGroup(name='demo',
                        description='demo group',
                        user=u)
        g.save()
        g.sensors.add(s1)
        g.sensors.add(s2)
        g.save()

        # generate some random-ish data
        end = datetime(2017, 10, 9, 14, 00, 00)
        start = end - timedelta(days=14)
        for i in range(14 * 24 * 30):
            msg = "%4d out of %d\r" % (i, 14 * 24 * 30)
            self.stdout.write(msg)

            delta_t = i * timedelta(minutes=2)
            t = start + delta_t

            value = 21 + random()
            r = SensorReading(sensor=s1,
                              channel=t_ch,
                              timestamp=t,
                              value=value)
            r.save()
            r = SensorReading(sensor=s2,
                              channel=t_ch,
                              timestamp=t,
                              value=value)
            r.save()

        self.stdout.write("\n..done\n")
