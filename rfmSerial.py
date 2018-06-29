import time, sys, glob, os
import json
from datetime import datetime
import serial

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
            ts = timezone.now()

            sensor_id = "S{}".format(data['sender'])
            for key, value in dict(volume=data['pay_volume'], battery=data['pay_battery'], RSSI=data['rssi']).items():      
                save_reading(sensor_id, key, ts, value)

        except Exception as e:
            print ("Error", e)


def serial_ports():
    """ Lists serial port names

        :raises EnvironmentError:
            On unsupported or unknown platforms
        :returns:
            A list of the serial ports available on the system
    """
    if sys.platform.startswith('win'):
        ports = ['COM%s' % (i + 1) for i in range(256)]
    elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        # this excludes your current terminal "/dev/tty"
        ports = glob.glob('/dev/tty[A-Za-z]*')
    elif sys.platform.startswith('darwin'):
        ports = glob.glob('/dev/tty.*')
    else:
        raise EnvironmentError('Unsupported platform')

    result = []
    for port in ports:
        try:
            s = serial.Serial(port)
            s.close()
            result.append(port)
        except (OSError, serial.SerialException):
            pass
    return result


# 
# Main function 
# 
def run():
    print ("Searching for serial port")
    ports = serial_ports()
    for i, p in enumerate(ports): 
        print ("Testing port {} of {}: {}".format(i, len(ports), p))
        if ports[i] is None:
            print("- Port is None")
            continue

        print ("- Connecting...")
        with serial.Serial(ports[i], 115200, timeout=10) as ser:
            
            attempt = 1
            max_attempts = 4

            while not ser.is_open:
                print ("Retry attempt {} of {}".format(attempt, max_attempts))
                ser.open()
                attempt += 1
                time.sleep(2)
                if attempt > max_attempts:
                    break
            
            if ser.is_open:
                print("Connected")

            while ser.is_open:
                line = ser.readline().decode("utf-8").strip()
                print(line)
                process_line(line)
            
                
                    

        print ("- Connection failed")

run()