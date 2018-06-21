import time
import json
from datetime import datetime
import requests
import serial

# login
base_url = 'http://raspberrypi.local/'
login_url  = base_url + 'admin/login/'
sd_store_url = base_url + 'sdstore/'
session    = requests.Session()
login_page = session.get(login_url)
session.post(login_url, data=dict(username="sensor", password="sdstoredevice", csrfmiddlewaretoken=login_page.cookies['csrftoken']))

SERIAL_PORT = '/dev/ttyACM0'

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

def create_sensor(sensor_id):
    # print("Creating sensor")
    r = session.post(
        sd_store_url + 'sensors/', 
        dict(mac=sensor_id, name=sensor_id, sensor_type="sound-node")
    )
    return r.status_code == 200 or r.status_code == 201

def create_channel(sensor_id, channel_name):
    # print("Creating channel")
    r = session.post(
        sd_store_url + 'sensor/{}/{}/'.format(sensor_id, channel_name), 
        {"reading_frequency": freqs[channel_name], "unit": units[channel_name] }
    )
    return r.status_code == 200

def save_reading(sensor_id, channel_id, ts, value):
    # print("Creating reading")
    r = session.post(
        sd_store_url + 'sensor/{}/{}/data/'.format(sensor_id, channel_id), 
        { "data": json.dumps([dict(timestamp=ts, value=value)]) }
    )
    # print(r.text)
    return r.status_code == 200

def process_line(line):
    if line.startswith("{"):
        print(line)
        # try:
        data = json.loads(line)
        print(data)
        
        ts = datetime.utcnow().strftime('%a %b %d %H:%M:%S %Y')

        sensor_id = "sensor{}".format(data['sender'])
        for key, value in dict(volume=data['pay_volume'], battery=data['pay_battery'], RSSI=data['rssi']).items():      
            if not save_reading(sensor_id, key, ts, value):
                if create_sensor(sensor_id):
                    create_channel(sensor_id, key)
                else:
                    print ("Failed to create sensor")
            else:
                print ("Saved")
        # except:
        #     pass


print ("Starting Serial Monitor")
with serial.Serial(SERIAL_PORT, 115200, timeout=10) as ser:
    print ("Starting loop")
    while True:
        line = ser.readline().decode("utf-8").strip()
        process_line(line)
        # transmit(ser, verbose)
        if not ser.is_open:
            ser.open()
