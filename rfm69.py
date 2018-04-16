import time
import json
from datetime import datetime
from RFM69 import Radio, FREQ_433MHZ
import requests

sd_store_url = 'http://raspberrypi.local/'

# login
login_url  = sd_store_url + 'admin/login/'
session    = requests.Session()
login_page = session.get(login_url)
session.post(login_url, data=dict(username="sensor", password="sdstoredevice", csrfmiddlewaretoken=login_page.cookies['csrftoken']))

def process_packet(packet):
    ts = packet.received.strftime('%a %b %d %H:%M:%S %Y')
    for key, value in dict(volume=packet.data[0], battery=packet.data[1], RSSI=packet.RSSI).items(): 

        post_data = { "data":  json.dumps([dict(timestamp=ts, value=value)]) }
        data_url  = sd_store_url + 'sdstore/sensor/%d/%s/data/' % (1, key)

        r = session.post(data_url, post_data)
        print(r.text)


print ("Starting")
with Radio(FREQ_433MHZ, 1, isHighPower=True, verbose=True) as radio:

    while True:

        while not radio.has_received_packet():
            time.sleep(.2)

        for packet in radio.get_packets():
            print("Packet received", packet.to_dict())
            process_packet(packet)
        

