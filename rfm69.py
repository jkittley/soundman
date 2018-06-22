import time
import json
from datetime import datetime
from RFM69 import Radio, FREQ_433MHZ
import requests

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
    # print(r.text)
    return r.status_code == 200

def process_packet(packet):
    
    # ts = packet.received.strftime('%a %b %d %H:%M:%S %Y')
    ts = datetime.utcnow().strftime('%a %b %d %H:%M:%S %Y')

    sensor_id = "sensor{}".format(packet.sender)

    for key, value in dict(volume=packet.data[0], battery=packet.data[1], RSSI=packet.RSSI).items():         
        
        if not save_reading(sensor_id, key, ts, value):
            if create_sensor(sensor_id):
                create_channel(sensor_id, key)
            else:
                print ("Failed to create sensor")


print ("Starting 123")
with Radio(FREQ_433MHZ, 1, isHighPower=True, power=100, verbose=True) as radio:

    print ("Starting loop")
    while True:

        print ("loop")

        while not radio.has_received_packet():
            # radio.broadcast('advert')
            # print("Advert Send")
            time.sleep(.2)

        for packet in radio.get_packets():
            print("Packet received", packet.to_dict())
            process_packet(packet)
        

