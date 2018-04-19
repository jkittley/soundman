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

from django.test import TestCase, override_settings
from django.test.client import Client

from datetime import datetime, timedelta
from django.contrib.auth.models import User
import json
from django.db.models import Min

#from nose.tools import nottest

#from models import populate
from sd_store.models import SensorReading, Event, EventType, UserProfile, Channel, Sensor
# Booking, BatteryStatus, BatteryType,

from math import sin,pi
from numpy import std

from basicutils.general import total_seconds, moving_average
from basicutils.djutils import DATE_FMTS
from nose.tools import nottest
from sd_store.models import RawDataKey

from sd_store.sdutils import filter_according_to_interval
from sd_store.sdutils import filter_according_to_interval_gen
from sd_store.sdutils import NoPrimaryMeterException
# JavaScript date format
#JS_FMT = '%Y-%m-%dT%H:%M:%S.%f'
#JS_FMT = '%a %b %d %H:%M:%S %Y'
JS_FMT = '%Y-%m-%d %H:%M:%S'

@override_settings(ROOT_URLCONF='sd_store.test_urls', DEBUG=False)
class LocalTestCase(TestCase):
    urls = 'sd_store.test_urls'


class PushTest(LocalTestCase):
    fixtures = ['auth_users']

    def setUp(self):
        TestCase.setUp(self)
        #
        # TODO: setup the sensor & channel
        self.username = 'e.costanza@ieee.org'
        self.password = 'FigureEnergy'
        self.user = User.objects.get(username=self.username)
        self.mac = "04:0c:ce:d0:a3:aa".replace(":", '')

    def test_upload(self):
        ch = Channel(
            name = 'test_ch',
            unit = 'dec C',
            reading_frequency = 60)
        ch.save()
        s = Sensor(
            mac = self.mac,
            sensor_type = "test",
            name = "temperature",
            user = self.user
            )
        s.save()
        s.channels.add(ch)
        s.save()

        k = RawDataKey(value=s.mac)
        k.save()
        k.sensors.add(s)

        url = '/rawinput/sensor/%s/%s/data/' % (s.mac, ch.name)

        #r = self.client.get('/meters/')
        #self.assertEqual(r.status_code, 200)

        data = {"value":0.1, "key": k.value}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)

        data = {"value":0.1, "key": '1'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 401)


#TODO: test admin views?

@override_settings(ROOT_URLCONF='sd_store.test_urls')
class BasicTest(LocalTestCase):
    fixtures = ['sd_store_data', 'auth_users', 'sd_store_users']

    def setUp(self):
        TestCase.setUp(self)
        self.client = Client()
        #
        self.bscURLs =  ['/meters/', '/events/',
                         '/referenceConsumption/']
        self.argURLs = ['/energy/data/', '/power/data/', '/energy/alwaysOn/',
                        '/power/alwaysOn/', '/energy/total/',
                        '/energy/totalCost/',
                        '/liveStats/', '/savings/']
        #self.extURLs = ['/powerNow/', '/getEventLog/', '/smartPlugState/']
        self.extURLs = ['/powerNow/', ]
        self.actURLs = ['/toggleSmartPlug/', '/smartPlugOn/', '/smartPlugOff/',
                        '/buttonFlashOn/', '/buttonFlashOff/',
                        '/toggleUserBattery/']

        self.username = 'e.costanza@ieee.org'
        self.password = 'FigureEnergy'
        print("URLs",self.urls)

    def test_admin(self):
        self.client.login(username='superuser', password='F1gur3!')
        response = self.client.get('/admin/', follow=True)
        print("admin content",response.content)
        self.assertEqual(response.status_code, 200)

    def test_authentication(self):
        # without authentication we should get a forbidden access error for any view

        for u in self.bscURLs + self.argURLs + self.extURLs:
            print("URL",u)
            response = self.client.get(u, follow=False)
            self.assertEqual(response.status_code, 302)
            # TODO: check the redirection
            #print response.redirect_chain
            #self.assertRedirects(response, '/accounts/login/?next='+u)


    def test_meters(self):
        self.client.login(username=self.username, password=self.password)

        allItemsResponse = self.client.get('/meters/')
        self.assertEqual(allItemsResponse.status_code, 200)
        print(allItemsResponse.content)
        parsed = json.loads(allItemsResponse.content)
        self.assertEqual(len(parsed), 6)

        print('parsed:', parsed)
        meterResponse = self.client.get('/meter/%d/' % (parsed[0]['id']))
        self.assertEqual(meterResponse.status_code, 200)

        # test that the response can be deserialized
        json.loads(meterResponse.content)


    def test_meters_access(self):
        # test that e.costanza cannot access a meter they do not own
        self.client.login(username=self.username, password=self.password)

        otherMeters = Sensor.objects.exclude(user=User.objects.get(username=self.username))
        self.assertGreater(len(otherMeters),0,"Needs at least one meter that %s can't access." % (self.username,))
        for meter in otherMeters:
            meterResponse = self.client.get('/meter/%d/' % (meter.id))
            self.assertEqual(meterResponse.status_code, 403)

    def test_sensor_unauthenticated(self):
        # Unauthenticated user tried to use this call: 302 (Should be 403, but never mind!)
        sensorResponse = self.client.get("/sensors/")
        self.assertEqual(sensorResponse.status_code,302)
        sensorResponse = self.client.get('/sensor/0/')
        self.assertEqual(sensorResponse.status_code,302)

    def test_sensor_unsupported(self):
        # Login
        self.client.login(username=self.username, password=self.password)

        # User uses unsupported methods: 400
        sensorResponse = self.client.put("/sensors/")
        self.assertEqual(sensorResponse.status_code, 400)
        sensorResponse = self.client.put("/sensor/0/")
        self.assertEqual(sensorResponse.status_code, 400)

    def test_sensor_GET(self):
        # Get relavent data from the DB
        user = User.objects.get(username=self.username)
        sensors = Sensor.objects.filter(user=user)
        otherSensors = Sensor.objects.exclude(user=user)
        self.assertGreater(len(sensors),0)
        self.assertGreater(len(otherSensors),0)

        # Login
        self.client.login(username=self.username, password=self.password)

        # User GETs /sensors/ : 200
            # TODO: Check it returns the right objects.
        sensorResponse = self.client.get('/sensors/')
        self.assertEqual(sensorResponse.status_code,200)

        # User GETs his /sensor/X/ : 200
        sensorResponse = self.client.get("/sensor/%d/" % (sensors[0].id,))
        self.assertEqual(sensorResponse.status_code,200)

        # User GETs his /sensor/X/ : 200 via mac address
        sensorResponse = self.client.get("/sensor/%s/" % (sensors[0].mac,))
        self.assertEqual(sensorResponse.status_code,200)

        # User GETs another user's /sensor/X/: 403
        print("Get another sensor")
        sensorResponse = self.client.get('/sensor/%d/' % (otherSensors[0].id,))
        print(sensorResponse.content)
        self.assertEqual(sensorResponse.status_code,403)
        # User GETs a non-existing /sensor/X/: 404
        # Sorry this is a tad evil. It basically finds the first integer that doesn't have a matching sensor with that PK
        x = 0
        while x in [sensor.id for sensor in sensors or otherSensors]:
            x += 1
        else: # else for a while loop executes after the condition evaluates False
            # And then runs this test:
            sensorResponse = self.client.get('/sensor/%d/' % (x,))
            self.assertEqual(sensorResponse.status_code,404)

    def test_sensor_POST(self):
        # Get relavent data from the DB
        user = User.objects.get(username=self.username)
        sensors = Sensor.objects.filter(user=user)
        otherSensors = Sensor.objects.exclude(user=user)
        self.assertGreater(len(sensors),0)
        self.assertGreater(len(otherSensors),0)

        testSensor = {
            "mac":"FF-FF-FF-FF-FF-FF-FF-FF",
            'name':'My Test Meter',
            'sensor_type':'MeterReader'
        }

        invalidParams = {
            'mac':'FF-FF-FF-FF-FF-FF-FF-FE',
            'name':"My Broken Test Meter"
        }

        # Login
        self.client.login(username=self.username, password=self.password)

        # User POSTs to /sensors/ with new sensor: 201
        sensorResponse = self.client.post('/sensors/',testSensor)
        self.assertEqual(sensorResponse.status_code,201)
        # User POSTs to /sensors/ with invalid params: 400
        sensorResponse = self.client.post('/sensors/',invalidParams)
        self.assertEqual(sensorResponse.status_code,400)
        # User POSTs to /sensors/ with existing sensor: ???
        # TODO: ???
        # User POSTs to /sensor/X/ with existing sensor: 403
        sensorResponse = self.client.post('/sensor/%d/' % (sensors[0].id,),testSensor)
        self.assertEqual(sensorResponse.status_code,403)
        # User POSTs to /sensor/X/ with invalid params: 400
        print( "Try with invalid params", invalidParams)
        sensorResponse = self.client.post('/sensor/%d/' % (sensors[0].id,),invalidParams)
        self.assertEqual(sensorResponse.status_code,400)
        # User POSTs to /sensor/X/ with another user's X: 403
        sensorResponse = self.client.post('/sensor/%d/' % (otherSensors[0].id,), testSensor)
        self.assertEqual(sensorResponse.status_code,403)
        # User POSTs to /sensor/X/ with nonexistent X: 404
        x = 0
        while x in [sensor.id for sensor in sensors or otherSensors]:
            x += 1
        else: # else for a while loop executes after the condition evaluates False
            # And then runs this test:
            sensorResponse = self.client.post('/sensor/%d/' % (x,), testSensor)
            self.assertEqual(sensorResponse.status_code,404)

    def test_sensor_DELETE(self):
        # Get relevant data from the DB
        user = User.objects.get(username=self.username)
        sensors = Sensor.objects.filter(user=user)
        count = Sensor.objects.count()
        otherSensors = Sensor.objects.exclude(user=user)

        self.assertGreater(len(sensors),0)
        self.assertGreater(len(otherSensors),0)
        # Login
        self.client.login(username=self.username, password=self.password)

        # User DELETEs to /sensors/ : 403 <== This can be changed later
        sensorResponse = self.client.delete('/sensors/')
        self.assertEqual(sensorResponse.status_code,403)
        # User DELETEs to /sensor/X/ with his X: 200
        sensorResponse = self.client.delete('/sensor/%d/' % sensors[0].id)
        self.assertEqual(sensorResponse.status_code,200)
        self.assertEqual(Sensor.objects.count(),count-1)
        # User DELETEs to /sensor/X/ with another user's X: 403
        sensorResponse = self.client.delete('/sensor/%d/' % otherSensors[0].id)
        self.assertEqual(sensorResponse.status_code,403)
        self.assertEqual(Sensor.objects.count(),count-1)
        # User DELETEs to /sensor/X/ with nonexistent X: 404
        x = 0
        while x in [sensor.id for sensor in sensors or otherSensors]:
            x += 1
        else: # else for a while loop executes after the condition evaluates False
            # And then runs this test:
            sensorResponse = self.client.delete('/sensor/%d/' % (x,))
            self.assertEqual(sensorResponse.status_code,404)
            self.assertEqual(Sensor.objects.count(),count-1)

    def test_channel_unauthenticated(self):
        user = User.objects.get(username=self.username)
        sensor = Sensor.objects.filter(user=user,sensor_type="MeterReader").first()
        channelResponse = self.client.get('/sensor/%d/%s/' % (sensor.id,'energy'))
        self.assertEqual(channelResponse.status_code, 302)

    def test_channel_unsupported(self):
        user = User.objects.get(username=self.username)
        sensor = Sensor.objects.filter(user=user,sensor_type="MeterReader").first()

        # Login
        self.client.login(username=self.username, password=self.password)

        channelResponse = self.client.put('/sensor/%d/%s/' % (sensor.id,'energy'))
        self.assertEqual(channelResponse.status_code,400)

    def test_channel_GET(self):
        user = User.objects.get(username=self.username)
        sensor = Sensor.objects.filter(user=user,sensor_type="MeterReader").first()
        button = Sensor.objects.filter(user=user,sensor_type="Button").first()
        otherSensor = Sensor.objects.exclude(user=user).filter(sensor_type="MeterReader").first()
        allSensorIDs = [x.id for x in Sensor.objects.all()]

        # Login
        self.client.login(username=self.username,password=self.password)

        # Begin tests for GET calls
        # User GETs correct channel: 200
        channelResponse = self.client.get('/sensor/%d/%s/' % (sensor.id,'energy'))
        self.assertEqual(channelResponse.status_code,200)
        # User GETs channel for another user: 403
        channelResponse = self.client.get('/sensor/%d/%s/' % (otherSensor.id,'energy'))
        self.assertEqual(channelResponse.status_code,403)
        # User GETs valid sensor with incorrect channel: 404
        channelResponse = self.client.get('/sensor/%d/%s/' % (sensor.id,'foo'))
        self.assertEqual(channelResponse.status_code,404)
        # User GETs valid sensor with valid, but unconnected channel: 404
        channelResponse = self.client.get('/sensor/%d/%s/' % (button.id,'energy'))
        self.assertEqual(channelResponse.status_code,404)
        # User GETs incorrect sensor: 404
        x = 0
        while x in allSensorIDs:
            x += 1
        else:
            channelResponse = self.client.get('/sensor/%d/%s/' % (x,'energy'))
            self.assertEqual(channelResponse.status_code,404)

    def test_channel_POST(self):
        user = User.objects.get(username=self.username)
        sensor = Sensor.objects.filter(user=user,sensor_type="MeterReader").first()
        otherSensor = Sensor.objects.exclude(user=user).filter(sensor_type="MeterReader").first()
        allSensorIDs = [x.id for x in Sensor.objects.all()]
        sensorChannelCount = sensor.channels.count()
        otherSensorChannelCount = otherSensor.channels.count()
        globalChannelCount = Channel.objects.count()

        soundChannel = {"unit":"dB",
                   "reading_frequency": 1}

        # Nonsense, malformed parameters.
        fishChannel = {'unit':'cod',
                       'reading_frequency':'haddock'}

        # Login
        self.client.login(username=self.username,password=self.password)

        # Begin Tests
        # User POSTs a channel with incorrect parameters: 400
        channelResponse = self.client.post('/sensor/%d/%s/' % (sensor.id,'energy'))
        self.assertEqual(channelResponse.status_code,400)
        # User POSTs a channel with malformed parameters: 400
        channelResponse = self.client.post('/sensor/%d/%s/' % (sensor.id,'fish'), fishChannel)
        self.assertEqual(channelResponse.status_code,400)
        # User POSTs a new channel with correct parameters: 201
        channelResponse = self.client.post('/sensor/%d/%s/' % (sensor.id,'volume'), soundChannel)
        self.assertEqual(channelResponse.status_code,201)
        self.assertEqual(sensor.channels.count(),sensorChannelCount+1)
        # User POSTs an existing channel with correct parameters: 200
        channelResponse = self.client.post('/sensor/%d/%s/' % (sensor.id,'volume'), soundChannel)
        self.assertEqual(channelResponse.status_code,200)
        self.assertEqual(sensor.channels.count(),sensorChannelCount+1)
        # User POSTs a channel to another user's sensor: 403
        channelResponse = self.client.post('/sensor/%d/%s/' % (otherSensor.id,'volume'), soundChannel)
        self.assertEqual(channelResponse.status_code,403)
        self.assertEqual(otherSensor.channels.count(),otherSensorChannelCount)
        # User POSTs a channel to a non-existent sensor: 404
        x=0
        while x in allSensorIDs:
            x+=1
        else:
            channelResponse = self.client.post('/sensor/%d/%s/' % (x,'volume'), soundChannel)
            self.assertEqual(channelResponse.status_code,404)

        # Verify that only one additional global channel has been created
        self.assertEqual(Channel.objects.count(), globalChannelCount+1)

    def test_channel_DELETE(self):
        user = User.objects.get(username=self.username)
        sensor = Sensor.objects.filter(user=user,sensor_type="MeterReader").first()
        otherSensor = Sensor.objects.exclude(user=user).filter(sensor_type="MeterReader").first()
        allSensorIDs = [x.id for x in Sensor.objects.all()]
        sensorChannelCount = sensor.channels.count()
        otherSensorChannelCount = otherSensor.channels.count()
        globalChannelCount = Channel.objects.count()

        # Login
        self.client.login(username=self.username,password=self.password)

        # Begin Tests
        # User DELETEs an existing channel: 200
        channelResponse = self.client.delete('/sensor/%d/%s/' % (sensor.id,'energy'))
        self.assertEqual(channelResponse.status_code, 200)
        self.assertEqual(sensor.channels.count(),sensorChannelCount-1)
        # User DELETEs another user's existing channel: 403
        channelResponse = self.client.delete('/sensor/%d/%s/' % (otherSensor.id,'energy'))
        self.assertEqual(channelResponse.status_code, 403)
        self.assertEqual(otherSensor.channels.count(),otherSensorChannelCount)
        # User DELETEs a real sensor's non-existent channel: 404
        channelResponse = self.client.delete('/sensor/%d/%s/' % (sensor.id,'foo'))
        self.assertEqual(channelResponse.status_code, 404)
        self.assertEqual(sensor.channels.count(),sensorChannelCount-1)
        # User DELETEs a non-existent sensor's channel: 404
        x = 0
        while x in allSensorIDs:
            x += 1
        else:
            channelResponse = self.client.delete('/sensor/%d/%s/' % (x,'energy'))
            self.assertEqual(channelResponse.status_code, 404)

        # Verify that none of the global channels have been deleted
        self.assertEqual(Channel.objects.count(),globalChannelCount)

    def test_data_unauthenticated(self):
        # Unauthenticated user tried to use this call: 302 (Should be 403, but never mind!)
        dataResponse = self.client.post("/sensor/0/energy/data/", {})
        self.assertEqual(dataResponse.status_code,302)

    def test_data_unsupported(self):
        user = User.objects.get(username=self.username)
        sensor = Sensor.objects.filter(user=user,sensor_type="MeterReader").first()

        # Login
        self.client.login(username=self.username,password=self.password)

        # PUT should fail
        dataResponse = self.client.put('/sensor/%d/%s/data/' % (sensor.id,'energy'))
        self.assertEqual(dataResponse.status_code,405)

    # @nottest
    # def test_data_GET(self):
    #     user = User.objects.get(username=self.username)
    #     sensor = Sensor.objects.filter(user=user,sensor_type="MeterReader").first()
    #     sensor.save()
    #     channel = sensor.channels.get(name="energy")
    #     channel.save()
    #     sensor.channels.add(channel)
    #     sensor.save()

    #     r = SensorReading(timestamp=datetime(2012, 12, 6, 18, 0, ),
    #                       value = 0.1,
    #                       sensor=sensor,
    #                       channel=channel)
    #     r.save()
    
    #     # Login
    #     self.client.login(username=self.username,password=self.password)

    #     dataResponse = self.client.get('/sensor/%d/%s/data/' % (sensor.id,'energy'))
    #     self.assertEqual(dataResponse.status_code,405)

    def test_data_POST(self):
        user = User.objects.get(username=self.username)
        sensor = Sensor.objects.filter(user=user,sensor_type="MeterReader").first()
        channel = sensor.channels.get(name="energy")
        otherSensor = Sensor.objects.exclude(user=user).filter(sensor_type="MeterReader").first()
        allSensorIDs = [x.id for x in Sensor.objects.all()]

        # Login
        self.client.login(username=self.username,password=self.password)

        # Begin Test
        # With no data: 400
        dataResponse = self.client.post('/sensor/%d/%s/data/' % (sensor.id,'energy'))
        self.assertEqual(dataResponse.status_code,400)
        # TODO: this test fails -- check why
        # With invalid data: 400
        #dataResponse = self.client.post('/sensor/%d/%s/data/' % (sensor.id,'energy'), badReadingString)
        #self.assertEqual(dataResponse.status_code,400)
        # With correct data: 200

        readings = [{"timestamp":"Wed Aug 01 12:00:00 2012",
                     "value":0.1},
                    {"timestamp":"Wed Aug 01 12:05:00 2012",
                     "value":0.2}]
        readingString = {"data":json.dumps(readings)}
        #badReadingString = {"data": "haddock"}

        dataResponse = self.client.post('/sensor/%d/%s/data/' % (sensor.id,'energy'), readingString)
        print( dataResponse)
        self.assertEqual(dataResponse.status_code,200)
        self.assertEqual(dataResponse.content.decode("utf-8") ,str(len(readings)))

        readings = [{"timestamp":"2012-08-01 12:00:00",
                     "value":0.1},
                    {"timestamp":"2012-08-01 12:05:00",
                     "value":0.2}]

        for reading in readings:
            fromDB = SensorReading.objects.get(sensor=sensor,channel=channel,timestamp=datetime.strptime(reading['timestamp'],JS_FMT))
            self.assertEqual(fromDB.value,reading['value'])
        # To another user's sensor: 403
        dataResponse = self.client.post('/sensor/%d/%s/data/' % (otherSensor.id,'energy'), readingString)
        self.assertEqual(dataResponse.status_code,403)
        # To a valid sensor and incorrect channel: 404
        dataResponse = self.client.post('/sensor/%d/%s/data/' % (sensor.id,'fish'), readingString)
        self.assertEqual(dataResponse.status_code,404)
        # To an invalid sensor: 404
        print("** POST TO INVALID SENSOR")
        x=0
        while x in allSensorIDs:
            x+=1
        else:
            tmp_url = '/sensor/%d/%s/data/' % (x,'energy')
            print (tmp_url)
            dataResponse = self.client.post(tmp_url, readingString)
            self.assertEqual(dataResponse.status_code,404)

    def test_data_POST_mac(self):
        user = User.objects.get(username=self.username)
        sensor = Sensor.objects.filter(user=user,sensor_type="MeterReader").first()
        channel = sensor.channels.get(name="energy")
        otherSensor = Sensor.objects.exclude(user=user).filter(sensor_type="MeterReader").first()

        # Login
        self.client.login(username=self.username,password=self.password)

        # Begin Test
        # With no data: 400
        dataResponse = self.client.post('/sensor/%s/%s/data/' % (sensor.mac,'energy'))
        self.assertEqual(dataResponse.status_code,400)
        # TODO: this test fails -- check why
        # With invalid data: 400
        #dataResponse = self.client.post('/sensor/%d/%s/data/' % (sensor.id,'energy'), badReadingString)
        #self.assertEqual(dataResponse.status_code,400)
        # With correct data: 200

        readings = [{"timestamp":"Wed Aug 01 12:00:00 2012",
                     "value":0.1},
                    {"timestamp":"Wed Aug 01 12:05:00 2012",
                     "value":0.2}]
        readingString = {"data":json.dumps(readings)}
        #badReadingString = {"data": "haddock"}

        dataResponse = self.client.post('/sensor/%s/%s/data/' % (sensor.mac,'energy'), readingString)
        print( dataResponse)
        self.assertEqual(dataResponse.status_code,200)
        self.assertEqual(dataResponse.content.decode("utf-8") ,str(len(readings)))

        readings = [{"timestamp":"2012-08-01 12:00:00",
                     "value":0.1},
                    {"timestamp":"2012-08-01 12:05:00",
                     "value":0.2}]

        for reading in readings:
            fromDB = SensorReading.objects.get(sensor=sensor,channel=channel,timestamp=datetime.strptime(reading['timestamp'],JS_FMT))
            self.assertEqual(fromDB.value,reading['value'])
        # To another user's sensor: 403
        dataResponse = self.client.post('/sensor/%s/%s/data/' % (otherSensor.mac,'energy'), readingString)
        self.assertEqual(dataResponse.status_code,403)
        # To a valid sensor and incorrect channel: 404
        dataResponse = self.client.post('/sensor/%s/%s/data/' % (sensor.mac,'fish'), readingString)
        self.assertEqual(dataResponse.status_code,404)

    def test_data_DELETE(self):
        user = User.objects.get(username=self.username)
        sensor = Sensor.objects.filter(user=user,sensor_type="MeterReader").first()

        # Login
        self.client.login(username=self.username,password=self.password)

        # Should, at present 501
        dataResponse = self.client.delete('/sensor/%d/%s/data/' % (sensor.id,'energy'))
        self.assertEqual(dataResponse.status_code,405)


    def test_last_reading_view(self):
        user = User.objects.get(username=self.username)
        sensor = Sensor.objects.filter(user=user,sensor_type="MeterReader").first()
        otherSensor = Sensor.objects.exclude(user=user).filter(sensor_type="MeterReader").first()
        allSensorIDs = [x.id for x in Sensor.objects.all()]

        # Test unauthenticated
        readingResponse = self.client.get('/sensor/%d/%s/last-reading/' % (sensor.id,'energy'))
        self.assertEqual(readingResponse.status_code,302)

        # Login
        self.client.login(username=self.username,password=self.password)

        # Begin Tests
        # Method not GET: 400
        readingResponse = self.client.post('/sensor/%d/%s/last-reading/' % (sensor.id,'energy'))
        self.assertEqual(readingResponse.status_code,405)
        # User GETs correctly: 200
        readingResponse = self.client.get('/sensor/%d/%s/last-reading/' % (sensor.id,'energy'))
        self.assertEqual(readingResponse.status_code,200)
        # User GETs for another user's sensor: 403
        readingResponse = self.client.get('/sensor/%d/%s/last-reading/' % (otherSensor.id,'energy'))
        self.assertEqual(readingResponse.status_code,403)
        # User GETs non-existent channel of existent sensor: 404
        readingResponse = self.client.get('/sensor/%d/%s/last-reading/' % (sensor.id,'fish'))
        self.assertEqual(readingResponse.status_code,404)
        # User GETs non-existent sensor: 404
        x=0
        while x in allSensorIDs:
            x+=1
        else:
            readingResponse = self.client.get('/sensor/%d/%s/last-reading/' % (x,'energy'))
            self.assertEqual(readingResponse.status_code,404)

    def test_sensorGroup(self):
        self.client.login(username=self.username, password=self.password)

        allItemsResponse = self.client.get('/sensorGroups/')
        self.assertEqual(allItemsResponse.status_code, 200)

        parsed = json.loads(allItemsResponse.content)
        self.assertEqual(len(parsed), 0)
        print("Create sensor group")
        # create sensor group
        createdResponse = self.client.post('/sensorGroups/', {
                              'name': '1stFloor',
                              'description': 'all sensors on the 1st floor'
                                                              })
        self.assertEqual(createdResponse.status_code, 200)
        print("Get all sensor groups")
        allItemsResponse = self.client.get('/sensorGroups/')
        self.assertEqual(allItemsResponse.status_code, 200)
        parsed = json.loads(allItemsResponse.content)
        self.assertEqual(len(parsed), 1)
        groupID = parsed[0]['id']
        print("Get a sensor")
        # get the first available sensor:
        sensorsResponse = self.client.get('/sensors/')
        parsed = json.loads(sensorsResponse.content)
        sensorID = parsed[0]['id']
        print("Add to sensor group")
        # add some sensors to group
        addedResponse = self.client.post('/sensorGroup/%d/sensors/' % (groupID,), {
                              'sensorID': sensorID
                              })
        self.assertEqual(addedResponse.status_code, 200)
        print("Check group")
        # check the group contains 1 sensor, the one we just added
        groupSensorsResponse = self.client.get('/sensorGroup/%d/sensors/' % (groupID,))
        self.assertEqual(groupSensorsResponse.status_code, 200)
        parsed = json.loads(groupSensorsResponse.content)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]['id'], sensorID)
        print("Delete sensor")
        # delete sensor from group
        addedResponse = self.client.delete('/sensorGroup/%d/sensor/%d/' % (groupID, sensorID))
        self.assertEqual(addedResponse.status_code, 200)
        print("Check count")
        # check the group contains 0 sensors
        groupSensorsResponse = self.client.get('/sensorGroup/%d/sensors/' % (groupID,))
        self.assertEqual(groupSensorsResponse.status_code, 200)
        parsed = json.loads(groupSensorsResponse.content)
        self.assertEqual(len(parsed), 0)
        print("Try to delete again")
        # trying to delete the sensor from the group again should fail
        addedResponse = self.client.delete('/sensorGroup/%d/sensor/%d/' % (groupID, sensorID))
        self.assertEqual(addedResponse.status_code, 404)

    def test_referenceConsumption(self):
        self.client.login(username=self.username, password=self.password)

        response = self.client.get('/referenceConsumption/')
        self.assertEqual(response.status_code, 200)

        consumption = json.loads(response.content)
        self.assertEqual(consumption['baseline_consumption'], 4.0)

    # TODO: implement the following
#    def test_live_stats(self):
#        raise NotImplementedError

    # TODO: implement the following
#    def test_savings(self):
#        raise NotImplementedError


def energy_f(x):
    return 0.2 + 1.0 + sin(2*pi*x/60.0)

def generate_energy_data(user, current_dt):
    profile = UserProfile.objects.get(user=user)
    meterOne = profile.primary_sensor
    channel = next(filter(lambda x: x.name == 'energy', meterOne.channels.all()))

    data_days = 10
    s = current_dt - timedelta(days=data_days)

    from itertools import cycle
    # create sinusoidal data
    hourData = [energy_f(x) for x in range(0,60,2)]
    dataSource = cycle(hourData)
    all_values = []
    for t in (s + timedelta(minutes=m) for m in range(0, 60*24*data_days, 2)):
        v = next(dataSource)
        dataPoint = SensorReading(timestamp=t, sensor=meterOne, channel=channel, value=v)
        dataPoint.save()
        all_values.append(v)

    from sd_store.sdutils import ALWAYS_ON_WINDOW_SIZE
    smoothed = moving_average(all_values, ALWAYS_ON_WINDOW_SIZE)


    always_on = min(smoothed)
    return always_on


class DataTest(LocalTestCase):
    #fixtures = ['sd_store_data', 'sd_store_users', 'sd_store_energy']
    fixtures = ['sd_store_data', 'auth_users', 'sd_store_users']

    def setUp(self):
        TestCase.setUp(self)
        #

        self.username = 'e.costanza@ieee.org'
        self.password = 'FigureEnergy'

        #print User.objects.all()
        user = User.objects.get(username=self.username)

        self.now = datetime(2013, 4, 4, 18)

        self.always_on = generate_energy_data(user, self.now)

        user_sensors = Sensor.objects.filter(user=user)
        self.energy_sensor = next(filter(lambda x: x.sensor_type == 'MeterReader', user_sensors))
        self.energy_channel = Channel.objects.get(name='energy')

        loggedIn = self.client.login(username=self.username, password=self.password)
        print( 'loggedIn:', loggedIn)

    def test_energy_data(self):
        url = '/sensor/%d/%s/data/' % (self.energy_sensor.id, self.energy_channel.name)

        # with no arguments, it should fail
        response = self.client.get(url)
        print (url)

        print (response)
        self.assertEqual(response.status_code, 400)
        parsed = json.loads(response.content)
        self.assertEqual(len(parsed['error']['reason'].keys()), 3)

        # pass bad arguments
        start = 'str((self.now - timedelta(days=7)))'
        end = 'str(self.now)'
        samplingInterval = 120
        response = self.client.get(url, {'start': start, 'end': end, 'sampling_interval': samplingInterval})
        self.assertEqual(response.status_code, 400)
        parsed = json.loads(response.content)
        self.assertEqual(len(parsed['error']['reason'].keys()), 2)

        # pass correct arguments
        start = self.now-timedelta(days=7)
        end = self.now
        # use JavaScript date format
        start = start.strftime(JS_FMT)
        end = end.strftime(JS_FMT)
        samplingInterval = 120
        response = self.client.get(url, {'start': start, 'end': end, 'sampling_interval': samplingInterval})

        self.assertEqual(response.status_code, 200)
        parsed = json.loads(response.content)
        data = parsed['data']
        self.assertEqual(len(data), 7 * 24 * 30)
        for i, m in enumerate(range(0, 60, 2)):
            self.assertEqual(data[i]['value'], energy_f(m))

        min_value = min([x['value'] for x in data])
        self.assertGreaterEqual(min_value, 0.0)

        # test re-sampling
        start = self.now - timedelta(hours=8)
        end = self.now - timedelta(hours=2)
        # use JavaScript date format
        samplingInterval = 60 * 60
        response = self.client.get(url,
                                   {'start': start.strftime(JS_FMT),
                                    'end': end.strftime(JS_FMT),
                                    'sampling_interval': samplingInterval})

        self.assertEqual(response.status_code, 200)
        parsed = json.loads(response.content)
        data = parsed['data']

        min_value = min([x['value'] for x in data])
        self.assertGreaterEqual(min_value, 0.0)

        print (data)
        self.assertEqual(len(data), 6)
        self.assertEqual(len(data), total_seconds(end-start)/samplingInterval)
        # assert the data is constant
        for i in range(1,len(data)):
            self.assertEqual(data[i-1]['value'], data[i]['value'])
        self.assertAlmostEqual(data[0]['value'], sum([energy_f(m) for m in range(0, 60, 2)]))


    def test_group_data(self):
        self.client.login(username=self.username, password=self.password)

        # create sensor group
        createdResponse = self.client.post('/sensorGroups/', {
                              'name': '1stFloor',
                              'description': 'all sensors on the 1st floor'
                                                   })
        self.assertEqual(createdResponse.status_code, 200)

        # get the groupID
        allItemsResponse = self.client.get('/sensorGroups/')
        self.assertEqual(allItemsResponse.status_code, 200)
        parsed = json.loads(allItemsResponse.content)
        groupID = parsed[0]['id']

        # get the first 2 available sensors:
        sensorsResponse = self.client.get('/sensors/')
        parsed = json.loads(sensorsResponse.content)
        self.assertGreaterEqual(len(parsed), 2)
        #sensorID =

        # add some sensors to group
        addedResponse = self.client.post('/sensorGroup/%d/sensors/' % (groupID,), {
                              'sensorID': parsed[0]['id']
                              })
        self.assertEqual(addedResponse.status_code, 200)

        addedResponse = self.client.post('/sensorGroup/%d/sensors/' % (groupID,), {
                              'sensorID': parsed[1]['id']
                              })
        self.assertEqual(addedResponse.status_code, 200)

        # get data from the group
        start = self.now-timedelta(days=7)
        end = self.now
        # use JavaScript date format
        start = start.strftime(JS_FMT)
        end = end.strftime(JS_FMT)
        samplingInterval = 120
        groupDataResponse = self.client.get('/sensorGroup/%d/data/' % (groupID,), {'start': start, 'end': end, 'sampling_interval': samplingInterval})
        self.assertEqual(groupDataResponse.status_code, 200)
        parsed = json.loads(groupDataResponse.content)
        self.assertEqual(len(parsed), 2)


class EnergyTest(LocalTestCase):
    #fixtures = ['sd_store_data', 'sd_store_users', 'sd_store_energy']
    fixtures = ['sd_store_data', 'auth_users', 'sd_store_users']

    def setUp(self):
        TestCase.setUp(self)

        self.username = 'e.costanza@ieee.org'
        self.password = 'FigureEnergy'

        #print User.objects.all()
        user = User.objects.get(username=self.username)

        self.now = datetime(2013, 4, 4, 18)
        self.always_on = generate_energy_data(user, self.now)

        user_sensors = Sensor.objects.filter(user=user)
        sensor = next(filter(lambda x: x.sensor_type == 'MeterReader', user_sensors))
        channel = Channel.objects.get(name='energy')

        eType = EventType.objects.get(name='generic')
        start_dt = SensorReading.objects.aggregate(Min('timestamp'))['timestamp__min']
        start_dt = datetime(start_dt.year, start_dt.month, start_dt.day, start_dt.hour, 2)
        start = start_dt + timedelta(hours=3)
        end = start + timedelta(minutes=18)
        eventOne = Event(sensor=sensor, channel=channel, name='event_one', event_type=eType, start=start, end=end)
        eventOne.save()

        start = start + timedelta(hours=2, minutes=10)
        end = start + timedelta(minutes=30)
        eventTwo = Event(sensor=sensor, channel=channel, name='event two', event_type=eType, start=start, end=end)
        eventTwo.save()

        loggedIn = self.client.login(username=self.username, password=self.password)

        # This is for the always_on test, but can be used elsewhere.
        self.opClient = Client()
        print( self.opClient)
        print( "EC:", User.objects.filter(username="e.costanza@ieee.org").count())
        print( "OP:", User.objects.filter(username="op106@soton.ac.uk").count())
        for user in User.objects.all():
            print( repr(user))
        opLoggedIn = self.opClient.login(username="op106@soton.ac.uk",password="mariokart")
        print(opLoggedIn)

        print( 'loggedIn:', loggedIn, "OP Logged in:", opLoggedIn)

        self.longMessage = True

    def test_energy_data(self):
        # with no arguments, it should fail
        response = self.client.get('/energy/data/')

        self.assertEqual(response.status_code, 400)
        parsed = json.loads(response.content)
        self.assertEqual(len(parsed['error']['reason'].keys()), 3)

        # pass bad arguments
        start = 'str((self.now - timedelta(days=7)))'
        end = 'str(self.now)'
        samplingInterval = 120
        response = self.client.get('/energy/data/', {'start': start, 'end': end, 'sampling_interval': samplingInterval})
        self.assertEqual(response.status_code, 400)
        parsed = json.loads(response.content)
        self.assertEqual(len(parsed['error']['reason'].keys()), 2)

        # pass correct arguments
        now = self.now - timedelta(hours=1)
        start = now - timedelta(days=7)
        end = now
        # use JavaScript date format
        start = start.strftime(JS_FMT)
        end = end.strftime(JS_FMT)
        samplingInterval = 120
        response = self.client.get('/energy/data/',
                                   {'start': start,
                                    'end': end,
                                    'sampling_interval': samplingInterval})

        self.assertEqual(response.status_code, 200)
        parsed = json.loads(response.content)
        data = parsed['data']
        self.assertEqual(len(data), 7 * 24 * 30)
        min_value = min([x['value'] for x in data])

        #print [x['value'] for x in data]
       # from matplotlib import pyplot as plt
       # plt.figure()
       # plt.plot([x['value'] for x in data])
       # plt.show()
        self.assertGreaterEqual(min_value, 0.0)
        for i, m in enumerate(range(0, 60, 2)):
            self.assertEqual(data[i]['value'], energy_f(m), 'm: %d, i: %d' %(m, i))

        # test re-sampling
        start = self.now - timedelta(hours=8)
        end = self.now - timedelta(hours=2)
        # use JavaScript date format
        samplingInterval = 60 * 60
        response = self.client.get('/energy/data/',
                                   {'start': start.strftime(JS_FMT),
                                    'end': end.strftime(JS_FMT),
                                    'sampling_interval': samplingInterval})

        self.assertEqual(response.status_code, 200)
        parsed = json.loads(response.content)
        data = parsed['data']

        min_value = min([x['value'] for x in data])
        self.assertGreaterEqual(min_value, 0.0)

        self.assertEqual(len(data), 6)
        self.assertEqual(len(data), total_seconds(end-start)/samplingInterval)
        for i in range(1,len(data)):
            self.assertEqual(data[i-1]['value'], data[i]['value'])
        self.assertAlmostEqual(data[0]['value'], sum([energy_f(t) for t in range(0,60,2)]))

    def test_power_data(self):
        # pass correct arguments
        start = self.now-timedelta(days=7)
        end = self.now
        # use JavaScript date format
        start = start.strftime(JS_FMT)
        end = end.strftime(JS_FMT)
        samplingInterval = 120
        response = self.client.get('/power/data/', {'start': start, 'end': end, 'sampling_interval': samplingInterval})

        self.assertEqual(response.status_code, 200)
        parsed = json.loads(response.content)
        data = parsed['data']
        self.assertEqual(len(data), 7 * 24 * 30)
        power_factor = 60 * 60 / samplingInterval
        for i, m in enumerate(range(0, 60, 2)):
            self.assertEqual(data[i]['value'], energy_f(m) * power_factor)

        # test re-sampling
        start = self.now - timedelta(hours=8)
        end = self.now - timedelta(hours=2)
        # use JavaScript date format
        samplingInterval = 60*60
        response = self.client.get('/power/data/',
                                   {'start': start.strftime(JS_FMT),
                                    'end': end.strftime(JS_FMT),
                                    'sampling_interval': samplingInterval})

        self.assertEqual(response.status_code, 200)
        parsed = json.loads(response.content)
        data = parsed['data']

        self.assertEqual(len(data), 6)
        self.assertEqual(len(data), total_seconds(end-start)/samplingInterval)
        for i in range(1,len(data)):
            self.assertEqual(data[i-1]['value'], data[i]['value'])

        power_factor = 60 * 60.0 / 120
        avg_power = power_factor * sum([energy_f(t) for t in range(0,60,2)]) / 30.0
        self.assertAlmostEqual(data[0]['value'], avg_power )

        #print ["%s -> %.2f"%(datetime.fromtimestamp(t), v) for t, v in data]

    def test_always_on(self):

        # without parameters it should fail
        response = self.client.get('/energy/alwaysOn/')
        self.assertEqual(response.status_code, 400)
        parsed = json.loads(response.content)
        self.assertEqual(len(parsed['error']['reason'].keys()), 3)

        # with incorrect parameters it should fail
        response = self.client.get('/energy/alwaysOn/',
                                   {'start': str(datetime.now()),
                                    'end': 'end',
                                    'sampling_interval': 120})
        self.assertEqual(response.status_code, 400)
        parsed = json.loads(response.content)
        self.assertEqual(len(parsed['error']['reason'].keys()), 2)

        # pass correct parameters (energy)
        start = self.now - timedelta(days=2)
        end = self.now

        # use JavaScript date format
        start = start.strftime(JS_FMT)
        end = end.strftime(JS_FMT)

        # user with no primary meter:
        self.assertRaises(NoPrimaryMeterException, lambda:
            self.opClient.get('/energy/alwaysOn/',
                                         {'start': start,
                                          'end': end,
                                          'sampling_interval': 120})
                      )

        # user with primary meter:
        response = self.client.get('/energy/alwaysOn/',
                                   {'start': start,
                                    'end': end,
                                    'sampling_interval': 120})
        self.assertEqual(response.status_code, 200)

        parsed = json.loads(response.content)

        self.assertEqual(len(parsed), 2 * 24 * 30)
        values = [p['value'] for p in parsed]
        for v in values:
            self.assertAlmostEqual(v, parsed[0]['value'], 5)

        self.assertAlmostEqual(parsed[0]['value'], self.always_on)

        # get energy at half resolution
        response = self.client.get('/energy/alwaysOn/', {'start': start, 'end': end, 'sampling_interval': 240})
        self.assertEqual(response.status_code, 200)

        parsed = json.loads(response.content)
        #print 'parsed:', parsed
        self.assertEqual(len(parsed), 2 * 24 * 15)
        self.assertAlmostEqual(parsed[0]['value'], 2 * self.always_on)


        # get power
        response = self.client.get('/power/alwaysOn/', {'start': start, 'end': end, 'sampling_interval': 120})
        self.assertEqual(response.status_code, 200)

        parsed = json.loads(response.content)
        #print 'parsed:', parsed
        self.assertEqual(len(parsed), 2 * 24 * 30)
        self.assertAlmostEqual(parsed[0]['value'], self.always_on * 30.0)

        # get power at half resolution
        response = self.client.get('/power/alwaysOn/', {'start': start, 'end': end, 'sampling_interval': 240})
        self.assertEqual(response.status_code, 200)

        parsed = json.loads(response.content)
        #print 'parsed:', parsed
        self.assertEqual(len(parsed), 2 * 24 * 15)
        self.assertAlmostEqual(parsed[0]['value'], self.always_on * 30.0)

    def test_total(self):
        print ('test_total')

        start = self.now-timedelta(days=3)
        end = self.now-timedelta(days=1)
        # use JavaScript date format
        start = start.strftime(JS_FMT)
        end = end.strftime(JS_FMT)
        response = self.client.get('/energy/total/', {'start': start, 'end': end})
        self.assertEqual(response.status_code, 200)

        parsed = json.loads(response.content)
        #print 'parsed:', parsed
        self.assertAlmostEqual(parsed, 2*24*sum([energy_f(t) for t in range(0,60,2)]))

    def test_total_cost(self):
        print( 'test_total_cost')

        start = self.now-timedelta(days=3)
        end = self.now-timedelta(days=1)
        # use JavaScript date format
        start = start.strftime(JS_FMT)
        end = end.strftime(JS_FMT)
        response = self.client.get('/energy/totalCost/', {'start': start, 'end': end})
        self.assertEqual(response.status_code, 200)

        parsed = json.loads(response.content)
        print( '** parsed:', parsed)
        #self.assertAlmostEqual(parsed['total'], 2*24*36.0)
        total = parsed['total_cost']
        always_on = parsed['always_on_cost']
        variable = parsed['variable_load_cost']
        self.assertGreaterEqual(total, 0.0)
        self.assertGreaterEqual(always_on, 0.0)
        self.assertGreaterEqual(variable, 0.0)
        self.assertEqual(variable, total - always_on)


    def test_events(self):
        # without parameters it should fail
        response = self.client.get('/events/')
        self.assertEqual(response.status_code, 400)
        print("Received",response.content)
        parsed = json.loads(response.content)
        self.assertEqual(len(parsed['error']['reason'].keys()), 2)

        # with incorrect parameters it should fail
        response = self.client.get('/events/', {'start': str(33), 'end': 'end'})
        self.assertEqual(response.status_code, 400)
        parsed = json.loads(response.content)
        self.assertEqual(len(parsed['error']['reason'].keys()), 2)

        # pass correct parameters
        start = self.now-timedelta(days=11)
        end = self.now
        # use JavaScript date format
        start = start.strftime(JS_FMT)
        end = end.strftime(JS_FMT)
        allItemsResponse = self.client.get('/events/', {'start': start, 'end': end})
        self.assertEqual(allItemsResponse.status_code, 200)

        parsed = json.loads(allItemsResponse.content)
        self.assertEqual(len(parsed), 2)

        for event in parsed:
            start = event['start']
            end = event['end']
            start = datetime.strptime(start, DATE_FMTS[0])
            end = datetime.strptime(end, DATE_FMTS[0])
            duration = end - start
            duration = total_seconds(duration) / 60
            self.assertGreater(duration, 0)

            evRange = range(int(start.minute), int(start.minute+duration), 2)
            consumption = sum([energy_f(x) for x in evRange])
            alwaysOn = self.always_on * (duration/2)

            print( 'consumption:', consumption)
            print( 'alwaysOn:', alwaysOn, event['total_always_on'])

            import logging
            logger = logging.getLogger()
            logger.info('event:' + str(event))

            #self.assertAlmostEqual(event['net_consumption'], consumption - alwaysOn)
            self.assertAlmostEqual(event['net_consumption'], consumption - event['total_always_on'])

            #self.assertGreaterEqual(event['cost'], 0)

        meterResponse = self.client.get('/event/%d/' % (parsed[0]['id']))
        self.assertEqual(meterResponse.status_code, 200)

        # test that the response can be deserialized
        json.loads(meterResponse.content)

        # try to create a new event

        # without arguments it should fail
        response = self.client.post('/event/')
        self.assertEqual(response.status_code, 400)
        parsed = json.loads(response.content)
        self.assertEqual(len(parsed['error']['reason'].keys()), 6)

        evData = {'start': 'now', 'end': 'end', 'name': 'test1', 'event_type_id': '3'}

        # with bad arguments it should fail
        response = self.client.post('/event/', evData)
        self.assertEqual(response.status_code, 400)
        parsed = json.loads(response.content)
        self.assertEqual(len(parsed['error']['reason'].keys()), 4)

        # with good arguments it should work

        # get the sensor and channel
        all_meters_response = self.client.get('/meters/')
        self.assertEqual(all_meters_response.status_code, 200)

        all_meters = json.loads(all_meters_response.content)
#        print
#        print 'all_meters:', all_meters
#        print
        meter = next(filter(lambda x: x['sensor_type'] == 'MeterReader', all_meters))
#        print
#        print 'meter:', meter
#        print
        channel = next(filter(lambda x: x['name'] == 'energy', meter['channels']))


        start = SensorReading.objects.aggregate(Min('timestamp'))['timestamp__min'] + timedelta(hours=48)
        end = start + timedelta(minutes=45)
        # use JavaScript date format
        start = start.strftime(JS_FMT)
        end = end.strftime(JS_FMT)
        evData = {'start': start,
                  'end': end,
                  'name': 'test1',
                  'event_type_id': '3',
                  'sensor': meter['id'],
                  'channel': channel['id']}

        response = self.client.post('/event/', evData)
        print (json.loads(response.content))
        self.assertEqual(response.status_code, 200)
        parsed = json.loads(response.content)

        evID = parsed['id']

        # duplication should fail
        start = SensorReading.objects.aggregate(Min('timestamp'))['timestamp__min'] + timedelta(hours=3)
        end = start + timedelta(minutes=18)
        # use JavaScript date format
        start = start.strftime(JS_FMT)
        end = end.strftime(JS_FMT)
        evData = {'start': start, 'end': end, 'name': 'test1', 'event_type_id': '3'}

        response = self.client.post('/event/', evData)
        self.assertEqual(response.status_code, 400)


        # check that there is one more event
        start = self.now-timedelta(days=11)
        end = self.now

        # use JavaScript date format
        start = start.strftime(JS_FMT)
        end = end.strftime(JS_FMT)
        allItemsResponse = self.client.get('/events/', {'start': start, 'end': end})
        print (json.loads(allItemsResponse.content))
        self.assertEqual(allItemsResponse.status_code, 200)

        parsed = json.loads(allItemsResponse.content)
        self.assertEqual(len(parsed), 3)

        # remove the event
        response = self.client.delete('/event/%d/' % (evID))
        self.assertEqual(response.status_code, 200)
        json.loads(response.content)

        # check that there is one less event
        allItemsResponse = self.client.get('/events/', {'start': start, 'end': end})
        self.assertEqual(allItemsResponse.status_code, 200)

        parsed = json.loads(allItemsResponse.content)
        self.assertEqual(len(parsed), 2)

    def test_live_stats(self):
        response = self.client.get('/liveStats/')

        self.assertEqual(response.status_code, 200)
        parsed = json.loads(response.content)
        self.assertEqual(len(parsed), 6)

    def test_backwards_events(self):
        # Should fail if an event with a negative duration passed without producing a 400 error.

        # Set main bounds for the test
        mainStartDatetime = self.now-timedelta(days=11)
        mainEndDatetime = self.now
        # use JavaScript date format
        mainStart = mainStartDatetime.strftime(JS_FMT)
        mainEnd = mainEndDatetime.strftime(JS_FMT)

        # Find how many events are in the DB to begin with
        allItemsResponse = self.client.get('/events/', {'start': mainStart, 'end': mainEnd})
        self.assertEqual(allItemsResponse.status_code, 200)
        parsed = json.loads(allItemsResponse.content)
        initialCount = len(parsed)

        # get the sensor and channel
        all_meters_response = self.client.get('/meters/')
        self.assertEqual(all_meters_response.status_code, 200)

        all_meters = json.loads(all_meters_response.content)
        meter = next(filter(lambda x: x['sensor_type'] == 'MeterReader', all_meters))
        channel = next(filter(lambda x: x['name'] == 'energy', meter['channels']))


        start = mainStartDatetime - timedelta(hours=48)
        end = start - timedelta(minutes=45) # End is before start
        # use JavaScript date format
        start = start.strftime(JS_FMT)
        end = end.strftime(JS_FMT)
        evData = {'start': start,
                  'end': end,
                  'name': 'test1',
                  'event_type_id': '3',
                  'sensor': meter['id'],
                  'channel': channel['id']}

        response = self.client.post('/event/', evData)
        parsed = json.loads(response.content)
        print( parsed['error']['reason'])
        self.assertEqual(response.status_code, 400)

        # Find how many events are in the DB at the end
        allItemsResponse = self.client.get('/events/', {'start': mainStart, 'end': mainEnd})
        self.assertEqual(allItemsResponse.status_code, 200)
        parsed = json.loads(allItemsResponse.content)
        finalCount = len(parsed)

        # Check there are as many events at beginning as end
        print( "Initial count:", initialCount, "Final count:", finalCount)
        self.assertEqual(initialCount,finalCount)

    def test_stdev(self):
        eType = EventType.objects.get(name='generic')
        start_dt = SensorReading.objects.aggregate(Min('timestamp'))['timestamp__min']
        #start_dt = datetime(start_dt.year, start_dt.month, start_dt.day, start_dt.hour, 2)
        start = start_dt + timedelta(hours=3)
        end = start + timedelta(minutes=60)

        user = User.objects.get(username=self.username)

        user_sensors = Sensor.objects.filter(user=user)
        sensor = next(filter(lambda x: x.sensor_type == 'MeterReader', user_sensors))
        channel = Channel.objects.get(name='energy')

        event = Event(sensor=sensor, channel=channel, name='event_one', event_type=eType, start=start, end=end)
        event.save()

        expected = std([energy_f(m) for m in range(0, 60, 2)])

        self.assertEqual(event.standard_deviation, expected)


class ExternalTest(LocalTestCase):
    #fixtures = ['sd_store_data', 'auth_users', 'sd_store_users', 'sd_store_energy']
    fixtures = ['sd_store_data', 'auth_users', 'sd_store_users', ]

    def setUp(self):
        TestCase.setUp(self)

        print( '--- setUp ---')
        import subprocess, time

        # TODO: delete the other server db file
        #try:
        #    os.remove('../../../adt/test.db')
        #except OSError:
        #    pass
        # TODO: reset the other server db
        #subprocess.call(['../../../adt/src/adt/manage.py', 'syncdb', '--noinput'])
        #subprocess.call(['../../../adt/src/adt/manage.py', 'syncdb', '--noinput'])


        # launch the other server
        # manage.py runserver 8001
        import os
        fe_protected_path = os.path.join('..', '..', 'fe_protected', 'src')
        fe_protected_manage = os.path.join(fe_protected_path, 'manage.py')
        pve_python = os.path.join(os.path.expanduser('~'),
                                'pve',
                                'django4',
                                'bin',
                                'python')

        self._other_server = subprocess.Popen(
                                    [
                                    pve_python,
                                    fe_protected_manage,
                                    'runserver',
                                    '8001'],
                                    cwd=fe_protected_path,
                                    env={'DJANGO_SETTINGS_MODULE': 'fe_protected.settings'})

        # sleep few seconds to make sure the server is up and running when we need it
        time.sleep(2)

        self.username = 'e.costanza@ieee.org'
        self.password = 'FigureEnergy'

        loggedIn = self.client.login(username=self.username, password=self.password)
        print( 'loggedIn:', loggedIn)

    def tearDown(self):
        print( '--- tearDown ---')

        # close the other server
        # this is a dirty hack
        #import os
        #pid = int(self._other_server.pid) + 1
        #os.kill(pid, signal.SIGINT)

        # this is the proper way (even though it requires an extra lib)
        # from http://stackoverflow.com/questions/4554767/terminating-subprocess-in-python
        import psutil, signal
        pp = psutil.Process(self._other_server.pid)
        for child in pp.get_children():
            child.send_signal(signal.SIGINT)
            child.wait()

        TestCase.tearDown(self)

    @nottest
    def test_power_now(self):
        response = self.client.get('/powerNow/')

        self.assertEqual(response.status_code, 200)
        # check that the result can be parsed as number
        float(response.content)


class PopulateTest(LocalTestCase):

    def setUp(self):
        pass

    def test_populate(self):
        userDataText = """acr@ecs.soton.ac.uk, OliverParson, 123,
        e.costanza@ieee.org, FigureEnergy, 123, time_priority"""

        userData = []
        lines = iter( userDataText.split("\n") )
        for line in lines:
            if len(line) < 8:
                continue
            try:
                info = line.split(',')
                info = [x.strip().rstrip() for x in info]
                userData.append(info)
            except StopIteration:
                pass

        import populatedb as backend
        backend.populate(userData, [], [])

class ResamplingTest(LocalTestCase):
    fixtures = ['sd_store_data', 'auth_users', 'sd_store_users', ]

    def setUp(self):
        self.meter = Sensor.objects.filter(name__startswith='Meter')[0]
        self.channel = self.meter.channels.get(name='energy')

    def test_gap_14(self):
        # create samples with a gap

        start = datetime(2013, 3, 1)
        # 30 hours of data
        for minutes in range(0, 60*30, 2):
            dt = start + timedelta(minutes=minutes)
            sr = SensorReading(timestamp=dt, value=1.0, sensor=self.meter, channel=self.channel)
            sr.save()

        # 14 hours gap
        restart = start + timedelta(hours=30+14)

        # 30 more hours of data
        for minutes in range(0, 60*30, 2):
            dt = restart + timedelta(minutes=minutes)
            sr = SensorReading(timestamp=dt, value=1.0, sensor=self.meter, channel=self.channel)
            sr.save()


        # now try to resample
        readings = filter_according_to_interval(self.meter, self.channel,
                                     start, start + timedelta(hours=72),
                                     12*60*60, 'energy')

        readings = list(readings)
        print( [x.timestamp for x in readings])
        self.assertEqual(len(readings), 72 / 12)

        for r in readings:
            print( r.timestamp)

        #diff_list = [x1.timestamp - x0.timestamp for (x0, x1) in zip(readings[:-1], readings[1:])]
        #self.assertListEqual(diff_list, [timedelta(hours=12) for _ in diff_list])

    def test_gap_26(self):
        print( "Begin of test")
        # create samples with a bigger gap
        start = datetime(2013, 3, 1)
        # 30 hours of data
        for minutes in range(0, 60*30, 2):
            dt = start + timedelta(minutes=minutes)
            sr = SensorReading(timestamp=dt, value=1.0, sensor=self.meter, channel=self.channel)
            sr.save()
            # print( "--",dt)

        # 24 hours gap
        restart = start + timedelta(hours=30+24)

        # 60 more hours of data
        for minutes in range(0, 60*60, 2):
            dt = restart + timedelta(minutes=minutes)
            sr = SensorReading(timestamp=dt, value=1.0, sensor=self.meter, channel=self.channel)
            sr.save()
            # print( "--",dt)

        # now try to resample 96
        readings = filter_according_to_interval(self.meter, self.channel,
                                     start, start + timedelta(hours=96),
                                     12*60*60, 'energy')


        """for r in readings:
            print r.timestamp"""
        readings = list(readings)
        print( "====================")
        for i in readings:
            print( i)
        print( "====================")

        print (len(readings))
        self.assertEqual(len(readings), 96 / 12 - 1)

        print( "End of test")

class GapTest(LocalTestCase):

    fixtures = ['sd_store_data', 'auth_users', 'sd_store_users', ]

    def setUp(self):
        self.meter = Sensor.objects.filter(sensor_type="MeterReader")[0]
        self.ch = self.meter.channels.get(name="energy")
        self.start = datetime(2013,3,3)
        self.end = datetime(2013,3,5)

    def test_3_days(self):
        for m in range(0,60*24*3,2):
            td= timedelta(minutes=m)
            ts= self.start+td
            sr =SensorReading(timestamp=ts, sensor=self.meter, channel=self.ch, value =1.0)
            sr.save()
        requested_interval= 6*60*60

        reading_list = filter_according_to_interval_gen(self.meter, self.ch, self.start, self.end, requested_interval, "energy")

        reading_list = list(reading_list)
        self.assertEqual(len(reading_list), 2*24/6)

    def test_2_days(self):
        for m in range(0,60*24*2+2,2):
            td= timedelta(minutes=m)
            ts= self.start+td
            sr =SensorReading(timestamp=ts, sensor=self.meter, channel=self.ch, value =1.0)
            sr.save()
        requested_interval= 6*60*60

        reading_list = filter_according_to_interval_gen(self.meter, self.ch, self.start, self.end, requested_interval, "energy")

        reading_list = list(reading_list)
        self.assertEqual(len(reading_list), 2*24/6)


class DuplicateTest(LocalTestCase):

    #fixtures = ['sd_store_data', 'auth_users', 'sd_store_users', ]
    fixtures = ['auth_users' ]

    def setUp(self):
        TestCase.setUp(self)
        #self.meter = Meter.objects.filter(sensor_type="MeterReader")[0]
        #self.ch = self.meter.channels.get(name="energy")
        #self.start = datetime(2013,3,3)
        #self.end = datetime(2013,3,5)

    def test_timestamp(self):
        u = User.objects.all()[0]
        ch = []
        for i in range(4):
            tmp = Channel(name='test' + str(i), reading_frequency=120)
            tmp.save()
            ch.append(tmp)

        s1 = Sensor(user=u,
                   mac='test',
                   sensor_type='test type')
        s1.save()
        s1.channels.add(ch[0])
        s1.channels.add(ch[1])
        s1.save()

        from copy import copy
        s2 = copy(s1)
        s2.id = None
        s2.mac = 'test2'
        s2.save()
        s2.channels.add(ch[2])
        s2.channels.add(ch[3])
        s2.save()

        dt = datetime(2013, 7, 25, 8, 15)
        v = 0.0
        sr1 = SensorReading(sensor=s1,
                           channel=ch[0],
                           timestamp=dt,
                           value=v)
        sr1.save()

        sr2, created = SensorReading.objects.get_or_create(sensor=s1,
                           channel=ch[0],
                           timestamp=dt,
                           defaults={'value': v})
        print (created)
        sr2.save()


