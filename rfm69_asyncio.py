import time, datetime
from RFM69Radio import Radio, FREQ_433MHZ
import asyncio
from aiohttp import ClientSession, BasicAuth




async def call_API(session, packet):
    # post single data point to the newly created channel
    sensor_id = 3
    channel_name = "volume"
    url = 'http://raspberrypi.local/sdstore/sensor/%d/%s/data/' % (sensor_id, channel_name)

    # data needs to be expressed as a list of (dictionary) objects 
    sensor_data = [{
        'timestamp': datetime.datetime.now().strftime('%a %b %d %H:%M:%S %Y'),
        'value': 25.0
    }]
    print("Sending packet to server")
    async with session.post(url, json=packet.to_dict('%c')) as response:
        response = await response.read()
        print("Server responded", response)


async def listen_to_radio(loop):
    with Radio(FREQ_433MHZ, 1, encryptionKey="sampleEncryptKey") as radio:
        async with ClientSession() as session:

            async with session.post('http://raspberrypi.local/admin/login/', data=dict(username="sensor", password="sdstoredevice")) as response:
                response = await response.read()
                print("Server responded", response)

                while True:
                    for packet in radio.getPackets():
                        print("Packet received", packet.to_dict())
                        loop.create_task(call_API(session, packet))
                    await asyncio.sleep(0)


loop = asyncio.get_event_loop()
loop.run_until_complete(listen_to_radio(loop))
loop.close()


