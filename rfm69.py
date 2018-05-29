import time
import json
from datetime import datetime, timedelta
from RFM69 import Radio, FREQ_433MHZ
import requests

max_readings = 6 # number of readings that are in a packet
off_sec = 3 # seconds between the readings in one packet

# login
base_url = 'http://raspberrypi.local/'
login_url  = base_url + 'admin/login/'
sd_store_url = base_url + 'sdstore/'
session    = requests.Session()
login_page = session.get(login_url)
session.post(login_url, data=dict(username="sensor", password="sdstoredevice", csrfmiddlewaretoken=login_page.cookies['csrftoken']))

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
    print(r.text)
    return r.status_code == 200

def process_packet(packet):
    #ts = packet.received.strftime('%a %b %d %H:%M:%S %Y')
    sensor_id = "sensor{}".format(packet.sender)
    for i in range(0, max_readings):
        for key, value in dict(volume=packet.data[i], battery=packet.data[max_readings], RSSI=packet.RSSI).items():         
            ts = packet.received + timedelta(seconds=-((max_readings * off_sec) - i*off_sec))
            if not save_reading(sensor_id, key, ts.strftime('%a %b %d %H:%M:%S %Y'), value):
                if create_sensor(sensor_id):
                    create_channel(sensor_id, key)
                else:
                    print ("Failed to create sensor")


print ("Starting")
with Radio(FREQ_433MHZ, 1, isHighPower=True, verbose=False) as radio:

    while True:

        while not radio.has_received_packet():
            time.sleep(.2)

        for packet in radio.get_packets():
            print("Packet received", packet.to_dict())
            process_packet(packet)
        

