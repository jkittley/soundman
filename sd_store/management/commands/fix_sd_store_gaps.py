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

'''
Created on 8 Feb 2013

@author: ata1g11
'''
import logging
logger = logging.getLogger('custom')

from optparse import make_option

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

from sd_store.sdutils import NoPrimaryMeterException
from sd_store.models import UserProfile, Sensor
from sd_store.sdutils import fix_data_gaps


class Command(BaseCommand):
    help = 'detect events'

    def add_arguments(self, parser):
        parser.add_argument('--user',
                            dest='user',
                            default=False,
                            help='Select a specific user')

    def handle(self, *args, **options):
        try:
            self.stdout.write("Fixing data gaps..\n")
            if options['user']:
                user = User.objects.get(username=options['user'])
                all_users = [user, ]
            else:
                all_users = User.objects.all()

            for user in all_users:
                try:
                    self.stdout.write("Processing user %s.. " % user)
                    #meter, channel = get_meter(user)
                    all_sensors = Sensor.objects.filter(user=user)

                    for sensor in all_sensors:
                        for channel in sensor.channels.all():
                            fix_data_gaps(sensor, channel, self.stdout)
                    self.stdout.write(" ..done\n")
                except (NoPrimaryMeterException, UserProfile.DoesNotExist) as e:
                    self.stdout.write(str(e))
                    self.stdout.write(" ..skipping\n")

            self.stdout.write("The End!!..\n")

        except Exception as e:
            logger.exception('error in pull_protected_store')
            raise e
