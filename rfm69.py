import time
import json
from datetime import datetime
from RFM69Radio import Radio, FREQ_433MHZ
import requests

sd_store_url = 'http://raspberrypi.local/'

# login
login_url  = sd_store_url + 'admin/login/'
session    = requests.Session()
login_page = session.get(login_url)
session.post(login_url, data=dict(username="sensor", password="sdstoredevice", csrfmiddlewaretoken=login_page.cookies['csrftoken']))

def process_packet(packet):
    sensor_data = json.dumps([dict(
        timestamp=datetime.now().strftime('%a %b %d %H:%M:%S %Y'),
        value=25.0
    )])
    data_url = sd_store_url + 'sdstore/sensor/%d/%s/data/' % (1, "volume")
    post_data = { "data": sensor_data }

    r = session.post(data_url, post_data)
    print('1 sample posted, result:', r.text)

def listen_to_radio():
    with Radio(FREQ_433MHZ, 1, encryptionKey="sampleEncryptKey") as radio:
        while True:
            for packet in radio.getPackets():
                print("Packet received", packet.to_dict())
                process_packet(packet)

        time.sleep(.1)

listen_to_radio()


