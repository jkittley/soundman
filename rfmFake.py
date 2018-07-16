import time, sys, glob, os, math
import json, random
from datetime import datetime
import serial
import arrow

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "soundman.settings")
import django
django.setup()
from sd_store.models import Channel, SensorReading, Sensor
from django.utils import timezone
from django.contrib.auth.models import User
from soundman.settings import SDSTORE_USER, SDSTORE_PASS

# login
freqs = {
    "volume": 1,
    "battery": 1,
    "RSSI": 1,
}

units = {
    "volume": "db",
    "battery": "v",
    "RSSI": 'db',
}


def save_reading(sensor_id, channel_id, ts, value):
    print("Creating reading for ", channel_id)
    
    # Get or create the user
    u, created = User.objects.get_or_create(username=SDSTORE_USER)
    if created:
        u.set_password(SDSTORE_PASS)

    # Get of create the sensor
    try:
        s = Sensor.objects.get(mac=sensor_id)
    except Sensor.DoesNotExist:
        s = Sensor(mac=sensor_id, user=u, name=sensor_id, sensor_type="sensor-node")
        s.save()

    # Get the channel
    try:
        c = Channel.objects.get(name=channel_id)
    except Channel.DoesNotExist:
        c = Channel(name=channel_id, unit=units[channel_id], reading_frequency=freqs[channel_id])
        c.save()

    except Channel.MultipleObjectsReturned:
        if s.channels.filter(name=channel_id).count() > 1:
            c = s.channels.filter(name=channel_id).first()
        else:
            c = Channel.objects.filter(name=channel_id).first()

    if s.channels.filter(name=channel_id).count() == 0:
        s.channels.add(c)
        s.save()
    
    r = SensorReading(timestamp=ts, sensor=s, channel=c, value=value)
    r.save()
    return True

def process_line(line):
    if line.startswith("{"):

        try:
            data = json.loads(line)
            print(data)       

            ts =  arrow.get(data['ts']).datetime
            
            sensor_id = "S{}".format(data['sender'])
            for key, value in dict(volume=data['pay_volume'], battery=data['pay_battery'], RSSI=data['rssi']).items():      
                save_reading(sensor_id, key, ts, value)

        except Exception as e:
            print ("Error", e)


# 
# Main function 
# 
def run():
    print ("Starting")
    
    # num_days = 14
    # reading_interval_in_seconds = 8

    # ts = arrow.get('2010-02-01T00:00:00.000000+00:00')

    # for day in range(num_days):

    #     for interval in range( math.floor(86400.0 / reading_interval_in_seconds) ):

    #         ts = ts.shift(seconds=reading_interval_in_seconds)

    #         process_line(json.dumps(dict(
    #             sender=101,
    #             pay_volume=random.randint(40,107),
    #             pay_battery=random.randint(1,5),
    #             rssi=random.randint(30,90),
    #             ts=ts.format()
    #         )))
   
    while True:
        ts = arrow.now()
        process_line(json.dumps(dict(
                sender=111,
                pay_volume=random.randint(40,107),
                pay_battery=random.randint(1,5),
                rssi=random.randint(30,90),
                ts=ts.format()
        )))

        time.sleep(1)

run()