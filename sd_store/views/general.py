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

from django.conf import settings
from django.http import HttpResponse, HttpResponseNotFound, HttpResponseBadRequest, HttpResponseForbidden, HttpResponseRedirect,\
    HttpResponseNotAllowed, Http404
from django.contrib.auth import authenticate, login, logout
import json
from datetime import datetime, timedelta
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from basicutils.decorators import access_required
from django.db.transaction import atomic

from sd_store import sdutils
from time import mktime
from django.db.models import Min, Max, Sum

from basicutils import djutils
from django.contrib.auth.models import User
from sd_store.models import EventType, StudyInfo, SensorGroup,\
                     Sensor, Channel, SensorReading, UserProfile, EepromSensorReading,\
                     SensorChannelPair, Annotation


from basicutils.djutils import to_dict

from django.core import serializers
from django.shortcuts import get_object_or_404
from sd_store.forms import RawDataForm, SampledIntervalForm, IntervalForm, ThresholdDeltaForm
from sd_store.models import RawDataKey
from django.db.utils import IntegrityError
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
#from basicutils.decorators import log_request
from django.views.decorators.csrf import csrf_exempt
#from django.utils import timezone
json_serializer = serializers.get_serializer("json")()

from base64 import urlsafe_b64decode
import xxtea
from struct import unpack
import re

from logging import getLogger
logger = getLogger('custom')

JS_FMT = '%a %b %d %H:%M:%S %Y'

@csrf_exempt
def login_view(request):
    if request.method == "POST":
        u = request.POST['username']
        p = request.POST['password']
        user = authenticate(username=u, password=p)
        if user != None:
            login(request, user)
            return HttpResponse(json.dumps({'status' : 'success', 'user_id' : user.id}))
        else:
            return HttpResponseBadRequest(djutils.get_json_error(json.dumps({'status' : 'bad username or password'})))
    return HttpResponseBadRequest(djutils.get_json_error("NOT_POST_REQUEST"))

def logout_view(request):
    logout(request)
    return HttpResponseRedirect(settings.LOGOUT_URL)

@csrf_exempt
@access_required
def meter_view(request, meter_id=None):
    if request.method == "GET":
        if meter_id == None:
            owner = djutils.get_requested_user(request)
            meter_list = Sensor.objects.filter(user=owner)

            return HttpResponse(json.dumps([to_dict(x) for x in meter_list]))
        else:
            meter_list = (Sensor.objects.get(id=meter_id),)
            if meter_list[0].user != djutils.get_requested_user(request):
                return HttpResponse("Tried to access a meter from a different user than the authenticated user.",status=403)
            return HttpResponse(json.dumps([to_dict(m) for m in meter_list]))
    elif request.method == "POST":
        raise NotImplementedError
    else:
        return HttpResponseBadRequest(djutils.get_json_error("NOT_GET_REQUEST"))

@csrf_exempt
@access_required
def sensor_view_mac(request, sensor_mac=None):
    s = get_object_or_404(Sensor, mac=sensor_mac)
    return sensor_view(request, s.id)

@csrf_exempt
@access_required
def sensor_view(request, sensor_id=None):
    if request.method == "GET":
        if sensor_id == None:
            sensor_list = Sensor.objects.filter()
            return HttpResponse(json.dumps([to_dict(x) for x in sensor_list]))
        else:
            try:
                sensor = Sensor.objects.get(id=sensor_id)
                if sensor.user != djutils.get_requested_user(request):
                    return HttpResponse("Tried to access a sensor from a different user than the authenticated user.",status=403)
                return HttpResponse(json.dumps(to_dict(sensor)))
            except Sensor.DoesNotExist:
                return HttpResponseNotFound("Sensor with id %s not found." % (sensor_id,))
    elif request.method == "POST": # Ideally would have this PUT, but urllib sucks...
        # POST all require these three parameters. Check they are present, else 400
        try:
            mac = request.POST["mac"]
            name = request.POST["name"]
            sensor_type = request.POST["sensor_type"]
        except KeyError:
            return HttpResponseBadRequest("The request to sensor_view with the following parameters is invalid: " + repr(request))
        except ValueError:
            return HttpResponseBadRequest("The request to sensor_view had malformed parameters.")
        sensor_owner = djutils.get_requested_user(request)

        if sensor_id == None:
            # TODO: this should be replaced by dealing with Meter separately from Sensor

            # sensor_id being None may mean that the sensor was not created yet, or
            # a sync problem between the two servers.
            # get or create a sensor with these params:
            sensor, _ = Sensor.objects.get_or_create(mac=mac,
                                                   defaults={
                                                         'user': sensor_owner,
                                                         'name': name,
                                                         'sensor_type': sensor_type})
            try:
                profile = UserProfile.objects.get(user=sensor_owner)
                if profile.primary_sensor is None:
                    if sensor.name.startswith(u'Meter Reader'):
                        profile.primary_sensor = sensor
                        profile.save()
            except UserProfile.DoesNotExist:
                pass

            return HttpResponse(str(sensor.id),status=201)
        else: # Request to specific sensor_id
            # If it exists already:
            try:
                sensor = Sensor.objects.get(id=sensor_id)
            except Sensor.DoesNotExist: # If it doesn't exist, then throw 404
                return HttpResponseNotFound("The specified sensor does not exist: " + repr(sensor_id))
            # And doesn't belong to another user
            if sensor.user != sensor_owner:
                return HttpResponseForbidden("Tried to modify a sensor that doesn't belong the authenticated user.")
            else:
                try:
                    with atomic():
                        # Then we need to update it according to the request
                        sensor.mac = mac
                        sensor.sensor_type = sensor_type
                        sensor.name = name
                        sensor.save()
                except IntegrityError as e:
                    # TODO: is this the best response
                    # logger.warn('IntegrityError: %s' % (str(e)))
                    return HttpResponseForbidden("Sensor already exists.")
                return HttpResponse(str(sensor.id),status=200)


    elif request.method == "DELETE":
        if sensor_id == None:
            return HttpResponse("Not allowed to delete all sensors with a single call", status=403)
        user = djutils.get_requested_user(request)
        try:
            sensor = Sensor.objects.get(pk=sensor_id)
            if user != sensor.user:
                return HttpResponse("Cannot delete other users' meters!", status=403)
            else:
                with atomic():
                    readings = SensorReading.objects.filter(sensor=sensor)
                    for reading in readings:
                        reading.delete()
                    sensor.delete()
                return HttpResponse("Sensor %s deleted." % (sensor_id,), status=200)
        except Sensor.DoesNotExist:
            return HttpResponseNotFound("Meter with id %s not found." % (sensor_id,))
    else:
        return HttpResponseBadRequest("The sensor_view is unable to handle the given HTTP method: " + repr(request.method))

@csrf_exempt
@access_required
def channel_view_mac(request, sensor_mac=None, channel_name=None):
    s = get_object_or_404(Sensor, mac=sensor_mac)
    return channel_view(request, s.id, channel_name)


@csrf_exempt
@access_required
def channel_view(request, sensor_id=None, channel_name=None):
    if request.method=='GET':
        user = djutils.get_requested_user(request)
        try:
            sensor = Sensor.objects.get(id=sensor_id)
            channel = sensor.channels.get(name=channel_name)
            if user != sensor.user:
                return HttpResponse("Tried to access another user's data. Forbidden.",status=403)
            return HttpResponse(json.dumps(to_dict(channel)))

        except Sensor.DoesNotExist:
            return HttpResponseNotFound()
        except Channel.DoesNotExist:
            return HttpResponseNotFound()

    elif request.method=='POST':
        user = djutils.get_requested_user(request)

        try:
            unit = request.POST['unit']
            interval = int(request.POST['reading_frequency'])
        except KeyError:
            return HttpResponseBadRequest("POST to channel_view with missing parameters.")
        except ValueError:
            return HttpResponseBadRequest("POST to channel_view with malformed parameters.")

        try:
            sensor = Sensor.objects.get(id=sensor_id)
        except Sensor.DoesNotExist:
            return HttpResponse("Tried to append a channel to a non-existent sensor.", status=404)

        if user != sensor.user:
            logger.warn("Tried to add a channel to a different user's sensor. " + 'user: %s, sensor: %s, channel_name: %s' % (str(user), str(sensor), str(channel_name)))
            return HttpResponse("Tried to add a channel to a different user's sensor. Forbidden.", status=403)

        # Create the channel if needed.
        channel, _ = Channel.objects.get_or_create(name=channel_name,
                                                   unit=unit,
                                                   reading_frequency=interval)

        # If the sensor doesn't have a channel by that name, create it:
        if not bool(sensor.channels.filter(name=channel_name)):
            try:
                sensor.channels.add(channel)
                sensor.save()
                return HttpResponse("Added channel to sensor.", status=201)
            except IntegrityError as e:
                #msg = "exception from sensor.channels.add(channel): %s; " % str(e)
                #msg += "sensor.channels.all(): %s; " % str(sensor.channels.all())
                #msg += "IDs: %s; " % str([x.id for x in sensor.channels.all()])
                #msg += "new channel id: %s; " % str(channel.id)
                #msg += "bool(sensor.channels.filter(name=%s)): %s" % (
                #      channel_name, str(bool(sensor.channels.filter(name=channel_name))) )
                #logger.error(msg)
                return HttpResponse("Could not add channel to sensor.", status=201)
        else:
            oldChannel = sensor.channels.get(name=channel_name)
            sensor.channels.remove(oldChannel)
            sensor.save()
            sensor.channels.add(channel)
            sensor.save()
            return HttpResponse("Modified existing channel on sensor.", status=200)

    elif request.method=='DELETE':
        user = djutils.get_requested_user(request)
        try:
            sensor = Sensor.objects.get(id=sensor_id)
            channel = sensor.channels.get(name=channel_name)

            if user != sensor.user:
                return HttpResponse("Tried to delete another user's data. Forbidden.", status=403)

            with atomic():
                for reading in SensorReading.objects.filter(sensor=sensor,channel=channel):
                    reading.delete()
                sensor.channels.remove(channel)
            return HttpResponse("Successfully removed channel.",status=200)
        except Sensor.DoesNotExist:
            return HttpResponse("Tried to delete a channel on a non-existent sensor.", status=404)
        except Channel.DoesNotExist:
            return HttpResponse("Tried to delete a non-existent channel.", status=404)
    else:
        return HttpResponseBadRequest("channel_view cannot serve HTTP %s." % (request.method,))

@csrf_exempt
@require_POST
def raw_batch_data_view(request):
    if request.method == 'POST':
        # TODO: this could be made more clean, using a multi-part post..
        # Check inputs are present and deserialisable
        try:
            data = json.loads(request.POST['data'])
        except KeyError:
            return HttpResponseBadRequest("The data is missing.")
        except TypeError:
            return HttpResponseBadRequest("The data is not a well formed JSON string.")


        # Add data - checking validity
        newCount = 0

        verified_data = []
        if type(data)!= list:
            return HttpResponseBadRequest("data_view requires a list of data points.")

        with atomic():
            for datum in data:
                try:
                    timestamp = datetime.strptime(str(datum['timestamp']),JS_FMT)
                    value = float(datum['value'])
                    channel_name = datum['channel']
                    sensor_mac = datum['sensor']
                    sensor_key = datum['key']
                except KeyError:
                    logger.error('error in data posted to sd_store')
                    return HttpResponseBadRequest("raw_batch_view requires data points to have a 'timestamp', 'value', 'channel', 'key', and 'sensor' key.")
                except ValueError:
                    logger.error('error in data posted to sd_store (timestamp formatting?)')
                    return HttpResponseBadRequest("Timestamps must be formatted:"+JS_FMT+', and values must be floats.')

                try:
                    sensor = Sensor.objects.get(mac=sensor_mac)
                except Sensor.DoesNotExist:
                    return HttpResponseNotFound("Sensor %s does not exist." % (sensor_mac))


                # check that the key matches the sensor
                try:
                    key = RawDataKey.objects.get(value=sensor_key)
                    if not sensor in key.sensors.all():
                        return HttpResponse('Unauthorized', status=401)
                except RawDataKey.DoesNotExist:
                    return HttpResponse('Unauthorized', status=401)

                # Check user has permission
                # if djutils.get_requested_user(request) != sensor.user:
                #     return HttpResponse("Attempted to edit another user's sensor. Forbidden.", status=403)


                try:
                    channel = sensor.channels.get(name=channel_name)
                except Channel.DoesNotExist:
                    return HttpResponseNotFound("This sensor does not appear to contain that channel.")

                try:
                    reading, created = SensorReading.objects.get_or_create(sensor=sensor,
                                                                           channel=channel,
                                                                           timestamp=timestamp,
                                                                           defaults={'value': value})
                    if not created:
                        reading.value = value
                        reading.save()
                    if created:
                        newCount += 1
                except IntegrityError as ie:
                    logger.info('integrity error from SensorReadings: ' + str(ie))
                # fix gaps in the data, if requested
                if 'fix_gaps' in request.POST:
                        sdutils.fix_data_gaps(sensor, channel)
        return HttpResponse(str(newCount),status=200)
    else:
        return HttpResponseNotAllowed(['POST'])

@csrf_exempt
@require_POST
def raw_data_view(request, sensor_mac, channel_name):
    # key: string
    # value: float

    # Get sensor and channel
    sensor = get_object_or_404(Sensor, mac=sensor_mac)
    try:
        channel = sensor.channels.get(name=channel_name)
    except Channel.DoesNotExist:
        return HttpResponseNotFound("This sensor does not appear to contain that channel.")

    form = RawDataForm(request.POST)
    if not form.is_valid():
        return HttpResponseBadRequest(djutils.get_json_error(dict(form.errors)))
    dt = datetime.now()
    if form.cleaned_data['dt'] is not None:
        dt = form.cleaned_data['dt']
    key_string = form.cleaned_data['key']
    value = form.cleaned_data['value']

    # check that the key matches the sensor
    try:
        key = RawDataKey.objects.get(value=key_string)
        if not sensor in key.sensors.all():
            return HttpResponse('Unauthorized', status=401)
    except RawDataKey.DoesNotExist:
        return HttpResponse('Unauthorized', status=401)

    if channel.name == 'history':
        history_array = []
        for x in range(0,5):
            v = (int(value) >> x * 3) & 7
            history_array.append(get_number(v))

        for i, number in enumerate(history_array):
            reading, created = SensorReading.objects.get_or_create(sensor=sensor,
                                                               channel=channel,
                                                               timestamp=dt - timedelta(seconds=(5-i)*5),
                                                               defaults={
                                                                 'value': number})
        
            #logger.debug("sensor %s, gets new sensorreading %s at time %s",sensor.name, number, dt - timedelta(seconds=(5-i)*5))
    else:
 #       logger.debug("channel from sensor %s has no history",sensor.name)
        reading, created = SensorReading.objects.get_or_create(sensor=sensor,
                                                           channel=channel,
                                                           timestamp=dt,
                                                           defaults={
                                                             'value': value})
    if not created:
        reading.value = value
        reading.save() 

    return HttpResponse(djutils.get_json_success(True))

def get_number(m):
    if m == 7:
        return -3
    if m == 6:
        return -2
    if m == 5:
        return -1
    if m == 0:
        return 0
    if m == 1:
        return 1
    if m == 2:
        return 2
    if m == 3:
        return 3

@csrf_exempt
@require_GET
def raw_data_register_view(request, sensor_id):
    sensor = get_object_or_404(Sensor, id=sensor_id)
    mac = request.GET.get('mac')
    if not mac:
        return HttpResponseBadRequest("No MAC address provided")

    if re.match(r"^([0-9A-F]{2}[-]){5}([0-9A-F]{2})$", mac, re.IGNORECASE):

        try:
            existing = Sensor.objects.get(mac=mac)
            ts = int(time())
            existing.mac = existing.mac+"_"+str(ts)
            existing.save()
        except Sensor.DoesNotExist:
            pass

        sensor.mac = mac
        sensor.save()
    else:
        return HttpResponseBadRequest("Invalid MAC address provided")
    return HttpResponse(djutils.get_json_success(True))

@csrf_exempt
@require_GET
def raw_data_signal_view(request, sensor_mac):
    sensor = get_object_or_404(Sensor, mac=sensor_mac)
    if 'rssi' not in request.GET:
        return HttpResponseBadRequest('No signal provided')
    rssi = request.GET.get('rssi')
    channel = sensor.channels.get(name='rssi')
    reading = SensorReading.objects.create(sensor=sensor, channel=channel, timestamp=datetime.now(), value=rssi)
    reading.save()
    return HttpResponse(djutils.get_json_success(True))

@csrf_exempt
@require_POST
def raw_data_packet_view(request, sensor_mac):

    # Verify sensor
    sensor = get_object_or_404(Sensor, mac=sensor_mac)
    if 'data' not in request.POST:
        return HttpResponseBadRequest('No data provided')
    data = urlsafe_b64decode(request.POST.get('data').encode("utf-8")).encode('hex')

    # This is a bit ugly, but avoids changing the model.
    rawDataKeys = RawDataKey.objects.filter(sensors__in=[sensor])

    if rawDataKeys.count() == 0:
        msg = data
    else:
        key = rawDataKeys[0].value
        msg = xxtea.decrypt(data, key)

    (temp, humi, l_value, position) = unpack('HHHH', msg)

    eeprom = False
    if position != 0xffff:
        eeprom = True
        # convert eeprom over - it's actually a 15 bit value, sent in the form:
        # xxxxxxxx < lsb
        # xxxxxxx1 < msb
        # So take position and shift it 9 to the right, to knock off the spare
        # bit. Then shift 8 to the left and OR with the right-most bits.
        position = ((position >> 9) << 8) | (position & 0xff)

    t_value = float(temp) * 165 / (2**14-1) - 40
    h_value = float(humi) * 100 / (2**14-1)

    channel_names = ['humidity', 'temperature', 'light']
    values = [h_value, t_value, l_value]
    channels = []
    dt = datetime.now()

    for channel_name in channel_names:
        try:
            channel = sensor.channels.get(name=channel_name)
        except Channel.DoesNotExist:
            return HttpResponseBadRequest("This sensor does not appear to contain a %s channel." % (channel_name))
        channels.append(channel)

    for idx, channel in enumerate(channels):
        if eeprom:
            reading, created = EepromSensorReading.objects.get_or_create(sensor=sensor, channel=channel, timestamp=dt, index=position, defaults={'value':values[idx]})
        else:
            reading, created = SensorReading.objects.get_or_create(sensor=sensor, channel=channel, timestamp=dt, defaults={
                                                             'value': values[idx]})
        if not created:
            reading.value = values[idx]
            reading.save()

        sdutils.fix_data_gaps(sensor, channel)

    return HttpResponse(djutils.get_json_success(True))

@csrf_exempt
@atomic
@access_required
def data_view_mac(request, sensor_mac=None, channel_name=None):
    s = get_object_or_404(Sensor, mac=sensor_mac)
    return data_view(request, s.id, channel_name)

@csrf_exempt
@atomic
@require_GET
@access_required
def regression_view(request, sensor_id=None, channel_name=None):
    # Get sensor and channel
    sensor = get_object_or_404(Sensor, id=sensor_id)
    try:
        channel = sensor.channels.get(name=channel_name)
    except Channel.DoesNotExist:
        return HttpResponseNotFound("This sensor does not appear to contain channel %s." % channel_name)

    # Check user has permission
    # if djutils.get_requested_user(request) != sensor.user:
    #     return HttpResponse("Attempted to edit another user's sensor. Forbidden.", status=403)

    # check the interval form
    form = SampledIntervalForm(request.GET)
    if not form.is_valid():
        return HttpResponseBadRequest(djutils.get_json_error(dict(form.errors)))

    requested_interval = form.cleaned_data['sampling_interval']
    start = form.cleaned_data['start']
    #logger.debug("this is start: %s" %(start))
    end = form.cleaned_data['end']

    if start >= end:
        return HttpResponseBadRequest(djutils.get_json_error('invalid interval requested'))

    data_type = 'generic'
    if channel.name == 'energy':
        data_type = 'energy'
    elif channel.name == 'power':
        data_type = 'power'


    result = {}

    # reading_list = SensorReading.objects.filter(sensor=sensor, channel=channel, timestamp__gte=start, timestamp__lte=end)
    #reading_list = sdutils.filter_according_to_interval(sensor, channel, start, end, requested_interval, data_type)
    if not SensorReading.objects.filter(sensor=sensor,channel=channel,timestamp__gte=start,timestamp__lt=end).count() > 0:
        #raise SensorReading.DoesNotExist('no sensor readings')
        result['max_datetime'] = 0
        result['min_datetime'] = 0
        result['max_datetime_value'] = 0
        result['min_datetime_value'] = 0
        return HttpResponse(json.dumps(result))

    reading_list = sdutils.filter_according_to_interval(sensor, channel, start, end, requested_interval, data_type)

    from scipy import stats
    # convert the data into numpy arrays
    x_list = [1000 * mktime(x.timestamp.timetuple()) for x in reading_list]
    y_list = [x.value for x in reading_list]
    slope, intercept, r_value, p_value, std_err = stats.linregress(x_list, y_list)


    queryset = SensorReading.objects.filter(sensor=sensor, channel=channel
                            ).filter(timestamp__gte=start
                            ).filter(timestamp__lt=end)
    min_datetime = queryset.aggregate(Min('timestamp'))['timestamp__min']

    max_datetime = queryset.aggregate(Max('timestamp'))['timestamp__max']

    #TODO: calculate this
    x_max_datetime = 1000 * mktime(max_datetime.timetuple())
    x_min_datetime = 1000 * mktime(min_datetime.timetuple())
    result['max_datetime_value'] = slope * x_max_datetime + intercept
    result['min_datetime_value'] = slope * x_min_datetime + intercept

    min_datetime = min_datetime.strftime(djutils.DATE_FMTS[0])
    result['min_datetime'] = min_datetime

    max_datetime = max_datetime.strftime(djutils.DATE_FMTS[0])
    result['max_datetime'] = max_datetime

    return HttpResponse(json.dumps(result))

@csrf_exempt
@atomic
@access_required
def regression_view_mac(request, sensor_mac=None, channel_name=None):
    s = get_object_or_404(Sensor, mac=sensor_mac)
    return regression_view(request, s.id, channel_name)


@csrf_exempt
@atomic
@require_GET
@access_required
def most_recent_maximum_view(request, sensor_id=None, channel_name=None):
    # TODO: move the next part to a separate function, so that it can be reused across views
    # Get sensor and channel
    sensor = get_object_or_404(Sensor, id=sensor_id)
    try:
        channel = sensor.channels.get(name=channel_name)
    except Channel.DoesNotExist:
        return HttpResponseNotFound("This sensor does not appear to contain channel %s." % channel_name)

    # Check user has permission
    # if djutils.get_requested_user(request) != sensor.user:
    #     return HttpResponse("Attempted to edit another user's sensor. Forbidden.", status=403)

    # check the input values
    form = ThresholdDeltaForm(request.GET)
    if not form.is_valid():
        return HttpResponseBadRequest(djutils.get_json_error(dict(form.errors)))

    min_threshold = form.cleaned_data['threshold']
    # using this delta is a cheaper alternative to smoothing the data
    delta = form.cleaned_data['delta']

    reading_list = SensorReading.objects.filter(sensor=sensor, channel=channel
                                                ).order_by('-timestamp') 

    prev = SensorReading(value=0.0)
    for sr in reading_list:
        if sr.value < min_threshold:
            continue
        if sr.value < (prev.value - delta):
            # this is the most recent maximum
            return HttpResponse(json.dumps({'value': sr.value, 'timestamp': sr.timestamp.strftime(djutils.DATE_FMTS[0])}))
        prev = sr
    
    # if we exit the for loop it means there was no maximum, 
    # so we return the last sensor reading (i.e. the first)

    return HttpResponse(json.dumps({'value': sr.value, 'timestamp': sr.timestamp.strftime(djutils.DATE_FMTS[0])}))

@csrf_exempt
@atomic
@access_required
def most_recent_maximum_view_mac(request, sensor_mac=None, channel_name=None):
    s = get_object_or_404(Sensor, mac=sensor_mac)
    return most_recent_maximum_view(request, s.id, channel_name)


#TODO: test this view (modify energy test to cover it)
@access_required
@require_GET
def baseline_view(request, sensor_id=None, channel_name=None):
    # Get sensor and channel
    sensor = get_object_or_404(Sensor, id=sensor_id)
    try:
        channel = sensor.channels.get(name=channel_name)
    except Channel.DoesNotExist:
        return HttpResponseNotFound("This sensor does not appear to contain channel %s." % channel_name)

    # Check user has permission
    # if djutils.get_requested_user(request) != sensor.user:
    #     return HttpResponse("Attempted to edit another user's sensor. Forbidden.", status=403)

    form = SampledIntervalForm(request.GET)
    if not form.is_valid():
        return HttpResponseBadRequest(djutils.get_json_error(dict(form.errors)))

    requested_interval = form.cleaned_data['sampling_interval']
    start = form.cleaned_data['start']
    end = form.cleaned_data['end']

    if start >= end:
        return HttpResponseBadRequest(djutils.get_json_error('invalid interval requested'))
    sr = SensorReading.objects.filter(sensor=sensor, channel=channel)
    if not (sr.exists()):
        return HttpResponse(json.dumps({'data':[]}))

    data_start = sr.aggregate(Min('timestamp'))['timestamp__min']
    data_end = sr.aggregate(Max('timestamp'))['timestamp__max']
    data_end += timedelta(seconds=channel.reading_frequency)

    start = max(start, data_start)
    end = min(end, data_end)

    if channel.name in ('energy', 'power'):
        data_type = channel.name
    else:
        data_type = 'generic'
    
    baseline = sdutils.calculate_always_on(sensor, channel, start, end, requested_interval, data_type)
    baseline = {'data': [{'t': 1000 * mktime(x[0].timetuple()), 'value': x[1]} for x in baseline]}
    return HttpResponse(json.dumps(baseline))

#TODO: test this view (modify energy test to cover it)
@access_required
@require_GET
def integral_view(request, sensor_id=None, channel_name=None):
    # Get sensor and channel
    sensor = get_object_or_404(Sensor, id=sensor_id)
    try:
        channel = sensor.channels.get(name=channel_name)
    except Channel.DoesNotExist:
        return HttpResponseNotFound("This sensor does not appear to contain channel %s." % channel_name)

    # Check user has permission
    if djutils.get_requested_user(request) != sensor.user:
        return HttpResponse("Attempted to edit another user's sensor. Forbidden.", status=403)

    form = IntervalForm(request.GET)
    if not form.is_valid():
        return HttpResponseBadRequest(djutils.get_json_error(dict(form.errors)))

    start = form.cleaned_data['start']
    end = form.cleaned_data['end']

    if start >= end:
        return HttpResponseBadRequest(djutils.get_json_error('invalid interval requested'))

    data_start = SensorReading.objects.filter(sensor=sensor, channel=channel).aggregate(Min('timestamp'))['timestamp__min']
    data_end = SensorReading.objects.filter(sensor=sensor, channel=channel).aggregate(Max('timestamp'))['timestamp__max']
    data_end += timedelta(seconds=channel.reading_frequency)

    start = max(start, data_start)
    end = min(end, data_end)

    #filter the reading list for the selection period
    reading_list = SensorReading.objects.filter(sensor=sensor, channel=channel)
    reading_list = reading_list.filter(timestamp__gte=(start))
    reading_list = reading_list.filter(timestamp__lt=(end))

    total_energy = {'data': reading_list.aggregate(Sum('value'))['value__sum']}

    return HttpResponse(json.dumps(total_energy))

@csrf_exempt
@atomic
@access_required
def batch_data_view(request):
    if request.method == 'POST':
        # TODO: this could be made more clean, using a multi-part post..
        # Check inputs are present and deserialisable
        try:
            data = json.loads(request.POST['data'])
        except KeyError:
            return HttpResponseBadRequest("The data is missing.")
        except TypeError:
            return HttpResponseBadRequest("The data is not a well formed JSON string.")


        # Add data - checking validity
        newCount = 0

        verified_data = []
        if type(data)!= list:
            return HttpResponseBadRequest("data_view requires a list of data points.")

        with atomic():
            for datum in data:
                try:
                    timestamp = datetime.strptime(str(datum['timestamp']),JS_FMT)
                    value = float(datum['value'])
                    channel_name = datum['channel']
                    sensor_mac = datum['sensor']
                except KeyError:
                    logger.error('error in data posted to sd_store')
                    return HttpResponseBadRequest("batch_view requires data points to have a 'timestamp', 'value', 'channel', and 'sensor' key.")
                except ValueError:
                    logger.error('error in data posted to sd_store (timestamp formatting?)')
                    return HttpResponseBadRequest("Timestamps must be formatted:"+JS_FMT+', and values must be floats.')

                try:
                    sensor = Sensor.objects.get(mac=sensor_mac)
                except Sensor.DoesNotExist:
                    return HttpResponseNotFound("Sensor %s does not exist." % (sensor_mac))

                # Check user has permission
                if djutils.get_requested_user(request) != sensor.user:
                    return HttpResponse("Attempted to edit another user's sensor. Forbidden.", status=403)


                try:
                    channel = sensor.channels.get(name=channel_name)
                except Channel.DoesNotExist:
                    return HttpResponseNotFound("This sensor does not appear to contain that channel.")

                try:
                    reading, created = SensorReading.objects.get_or_create(sensor=sensor,
                                                                           channel=channel,
                                                                           timestamp=timestamp,
                                                                           defaults={'value': value})
                    if not created:
                        reading.value = value
                        reading.save()
                    if created:
                        newCount += 1
                except IntegrityError as ie:
                    logger.info('integrity error from SensorReadings: ' + str(ie))
                # fix gaps in the data, if requested
                if 'fix_gaps' in request.POST:
                        sdutils.fix_data_gaps(sensor, channel)
        return HttpResponse(str(newCount),status=200)
    else:
        return HttpResponseNotAllowed(['POST'])

@csrf_exempt
@atomic
@access_required
def data_view(request, sensor_id=None, channel_name=None):
    if request.method == 'GET':
        # Get sensor and channel
        sensor = get_object_or_404(Sensor, id=sensor_id)
        try:
            channel = sensor.channels.get(name=channel_name)
        except Channel.DoesNotExist:
            return HttpResponseNotFound("This sensor does not appear to contain channel %s." % channel_name)

        # Check user has permission
        # if djutils.get_requested_user(request) != sensor.user:
        #     return HttpResponse("Attempted to edit another user's sensor. Forbidden.", status=403)

        # check the interval form
        form = SampledIntervalForm(request.GET)
        if not form.is_valid():
            return HttpResponseBadRequest(djutils.get_json_error(dict(form.errors)))

        requested_interval = form.cleaned_data['sampling_interval']
        start = form.cleaned_data['start']
        #logger.debug("this is start: %s" %(start))
        end = form.cleaned_data['end']
        annotations = request.GET.get('annotations', False)


        if start >= end:
            return HttpResponseBadRequest(djutils.get_json_error('invalid interval requested'))
        
        data_type = 'generic'
        if channel.name == 'energy':
            data_type = 'energy'
        elif channel.name == 'power':
            data_type = 'power'

        # reading_list = SensorReading.objects.filter(sensor=sensor, channel=channel, timestamp__gte=start, timestamp__lte=end)
        #reading_list = sdutils.filter_according_to_interval(sensor, channel, start, end, requested_interval, data_type)
        if SensorReading.objects.filter(sensor=sensor,channel=channel,timestamp__gte=start,timestamp__lt=end).count() > 0:
            reading_list = sdutils.filter_according_to_interval(sensor, channel, start, end, requested_interval, data_type)
        else:
            reading_list = []
        # TODO: can this query be optimized?
        result = {}

        result['data'] = [{'t': 1000 * mktime(x.timestamp.timetuple()), 'value': x.value} for x in reading_list]

        if annotations:
            result['annotations'] = []
            pairs = SensorChannelPair.objects.filter(sensor=sensor, channel=channel)
            if pairs.count() == 1:
                # Get all annotations that overlap with the requested portion
                annotations = Annotation.objects.filter(pairs__in=[pairs[0].id])
                # Exclude those that end before the start of the portion
                annotations = annotations.exclude(end__lte=start)
                # And those that start after the end
                annotations = annotations.exclude(start__gte=end)
                for annotation in annotations:
                    result['annotations'].append(to_dict(annotation))
        if len(result['data']) == 0:
            #raise SensorReading.DoesNotExist('no sensor readings')
            result['max_datetime'] = 0
            result['min_datetime'] = 0
            return HttpResponse(json.dumps(result))

        queryset = SensorReading.objects.filter(sensor=sensor, channel=channel
                                ).filter(timestamp__gte=start
                                ).filter(timestamp__lt=end)
        min_datetime = queryset.aggregate(Min('timestamp'))['timestamp__min']
        min_datetime = min_datetime.strftime(djutils.DATE_FMTS[0])
        result['min_datetime'] = min_datetime

        max_datetime = queryset.aggregate(Max('timestamp'))['timestamp__max']
        max_datetime = max_datetime.strftime(djutils.DATE_FMTS[0])
        result['max_datetime'] = max_datetime

        return HttpResponse(json.dumps(result))

    elif request.method == 'POST':
        # TODO: this could be made more clean, using a multi-part post..
        # Check inputs are present and deserialisable
        try:
            data = json.loads(request.POST['data'])
        except KeyError:
            return HttpResponseBadRequest("The data is missing.")
        except TypeError:
            return HttpResponseBadRequest("The data is not a well formed JSON string.")

        # Get sensor and channel
        sensor = get_object_or_404(Sensor, id=sensor_id)
        try:
            channel = sensor.channels.get(name=channel_name)
        except Channel.DoesNotExist:
            return HttpResponseNotFound("This sensor does not appear to contain that channel.")

        # Check user has permission
        if djutils.get_requested_user(request) != sensor.user:
            return HttpResponse("Attempted to edit another user's sensor. Forbidden.", status=403)

        # Add data - checking validity
        newCount = 0
        try:
            with atomic():
                if type(data)!= list:
                    return HttpResponseBadRequest("data_view requires a list of data points.")
                for datum in data:
                    try:
                        timestamp = datetime.strptime(str(datum['timestamp']),JS_FMT)
                        value = float(datum['value'])
                    except KeyError:
                        logger.error('error in data posted to sd_store')
                        return HttpResponseBadRequest("data_view requires data points to have a 'timestamp' and 'value' key.")
                    except ValueError:
                        logger.error('error in data posted to sd_store (timestamp formatting?)')
                        return HttpResponseBadRequest("Timestamps must be formatted:"+JS_FMT+', and values must be floats.')

                    try:
                        reading, created = SensorReading.objects.get_or_create(sensor=sensor,
                                                                               channel=channel,
                                                                               timestamp=timestamp,
                                                                               defaults={'value': value})
                        if not created:
                            reading.value = value
                            reading.save()
                        if created:
                            newCount += 1
                    except IntegrityError as ie:
                        logger.info('integrity error from SensorReadings: ' + str(ie))
                # fix gaps in the data, if requested
                if 'fix_gaps' in request.POST:
                    sdutils.fix_data_gaps(sensor, channel)
        except IntegrityError as e:
            pass
        return HttpResponse(str(newCount),status=200)
    else:
        return HttpResponseNotAllowed(['GET', 'POST'])

@csrf_exempt
@access_required
@require_GET
def group_data_view(request, sensor_group_id, channel_name=None):
    # Get sensor and channel
    group = get_object_or_404(SensorGroup, id=sensor_group_id)

    # Check user has permission
    if request.user != group.user:
        return HttpResponse("Attempted to edit another user's data. Forbidden.", status=403)

    # check the interval form
    form = SampledIntervalForm(request.GET)
    if not form.is_valid():
        return HttpResponseBadRequest(djutils.get_json_error(dict(form.errors)))

    requested_interval = form.cleaned_data['sampling_interval']
    start = form.cleaned_data['start']
    end = form.cleaned_data['end']

    if start >= end:
        return HttpResponseBadRequest(djutils.get_json_error('invalid interval requested'))

    result = []
    for sensor in group.sensors.all():
        #if channel_name is None:
        #    selected_channels = sensor.channels.all()
        #else:
        #    selected_channels = sensor.channel.filter(name=channel_name)
        sensor_data = {}
        sensor_data['sensor'] = to_dict(sensor)
        sensor_data['channels_data'] = []
        selected_channels = sensor.channels.all()
        for channel in selected_channels:
            # TODO: using 'power' here as an argument is a hack, it should be fixed
            reading_list = sdutils.filter_according_to_interval(sensor, channel, start, end, requested_interval, 'generic')

            current = {}
            current['data'] = [{'t': 1000 * mktime(x.timestamp.timetuple()),
                               'value': x.value} for x in reading_list]

            if len(current['data']) == 0:
                #raise SensorReading.DoesNotExist('no sensor readings')
                current['max_datetime'] = 0
                current['min_datetime'] = 0
            else:
                min_datetime = SensorReading.objects.filter(sensor=sensor,
                                                            channel=channel
                                ).aggregate(Min('timestamp'))['timestamp__min']
                min_datetime = min_datetime.strftime(djutils.DATE_FMTS[0])
                current['min_datetime'] = min_datetime

                max_datetime = SensorReading.objects.filter(sensor=sensor,
                                                            channel=channel
                                ).aggregate(Max('timestamp'))['timestamp__max']
                max_datetime = max_datetime.strftime(djutils.DATE_FMTS[0])
                current['max_datetime'] = max_datetime

            current['channel'] = to_dict(channel)

            sensor_data['channels_data'].append(current)
        result.append(sensor_data)

    return HttpResponse(json.dumps(result))

@require_GET
@access_required
def last_reading_view_mac(request, sensor_mac=None, channel_name=None):
    s = get_object_or_404(Sensor, mac=sensor_mac)
    return last_reading_view(request, s.id, channel_name)

@csrf_exempt
def snapshot_view(request):
    user = djutils.get_requested_user(request)
    if request.user == user or request.user.is_superuser:
        sensor_list = Sensor.objects.filter(user=user)
        result = []
        for sensor in sensor_list:
            for channel in sensor.channels.all():
                readings = SensorReading.objects.filter(channel=channel,sensor=sensor)
                if not readings.exists():
                    readings = EepromSensorReading.objects.filter(channel=channel, sensor=sensor)
                if readings.exists():
                    lastReading = readings.order_by("-timestamp")[0]
                    current = {'mac':sensor.mac,
                            'channel':channel.name,
                            'unit': channel.unit,
                            'timestamp':lastReading.timestamp.strftime(JS_FMT),
                            'value': lastReading.value}
                    result.append(current)
        return HttpResponse(json.dumps(result))
    else:
        return HttpResponseForbidden()

@require_GET
@access_required
def last_reading_view(request, sensor_id=None, channel_name=None):
    user = djutils.get_requested_user(request)

    sensor = get_object_or_404(Sensor, id=sensor_id)
    try:
        channel = sensor.channels.get(name=channel_name)
    except Channel.DoesNotExist:
        raise Http404('Requested channel does not exist.')

    if user != sensor.user:
        return HttpResponse("Tried to access data belonging to another user. Forbidden.", status=403)

    readings = SensorReading.objects.filter(channel=channel,sensor=sensor)
    if not readings.exists():
        readings = EepromSensorReading.objects.filter(channel=channel, sensor=sensor)

    if readings.exists():
        lastReading = readings.order_by("-timestamp")[0]
        lastReading.timstamp = lastReading.timestamp.strftime(JS_FMT)
        return HttpResponse(json.dumps(to_dict(lastReading)))
    else:
        msg = 'sensor: %s, channel: %s, readings.count(): %d' % (
                 str(sensor), str(channel), readings.count())
        logger.info(msg)
        return HttpResponse(None)

@csrf_exempt
@access_required
def sensor_group_list_view(request):
    if request.method == "GET":
        groups = SensorGroup.objects.filter(user = request.user)
        return HttpResponse(json.dumps([to_dict(x) for x in groups]))
    elif request.method == "POST":
        # create sensor group
        # TODO: change this to use a form
        sensor_group = SensorGroup(
                                   name=request.POST.get('name'),
                                   description=request.POST.get('description'),
                                   user=request.user
                                   )
        sensor_group.save()
        return HttpResponse(djutils.get_json_success(sensor_group.id))

@csrf_exempt
@access_required
def sensor_group_detail_view(request, sensor_group_id):
    sensor_group = get_object_or_404(SensorGroup, id=sensor_group_id)
    # if sensor_group.user != request.user:
        # return HttpResponse(djutils.get_json_error("ACCESS_DENIED"), status=403)

    if request.method == "GET":
        return HttpResponse(json.dumps(to_dict(sensor_group)))
    elif request.method == "POST":
        # TODO: change this to use a form
        sensor_group_name = request.POST.get('sensorGroupName', None)
        sensor_group_description = request.POST.get('sensorGroupDescription', None)

        if sensor_group_name is not None:
            sensor_group.name = sensor_group_name
        if sensor_group_name is not None:
            sensor_group.description = sensor_group_description

        sensor_group.save()
        return HttpResponse(djutils.get_json_success(sensor_group.id))

    elif request.method == "DELETE":
        sensor_group.delete()
        return HttpResponse(djutils.get_json_success(sensor_group_id))

    return HttpResponseBadRequest(djutils.get_json_error("NOT_GET_POST_OR_DELETE_REQUEST"))


@csrf_exempt
@access_required
@require_http_methods(["GET", "POST"])
def sensor_group_sensors_list_view(request, sensor_group_id):

    logger.warning('sensor_group_sensors_list_view ' + request.method)

    sensor_group = get_object_or_404(SensorGroup, id=sensor_group_id)
    if sensor_group.user != request.user:
        return HttpResponse(djutils.get_json_error("ACCESS_DENIED"), status=403)

    if request.method == "GET":
        sensors = sensor_group.sensors.all()
        return HttpResponse(json.dumps([to_dict(x) for x in sensors]))
    elif request.method == "POST":
        # TODO: change this to use a form
        sensor_id = request.POST.get('sensorID', None)

        if sensor_id is not None:
            sensor = get_object_or_404(Sensor, id=sensor_id)
            sensor_group.sensors.add(sensor)
            sensor_group.save()
            return HttpResponse(djutils.get_json_success(sensor_group.id))
        else:
            return HttpResponseBadRequest("missing parameters")
    else:
        raise NotImplementedError

@csrf_exempt
@access_required
@require_http_methods(["DELETE",])
def sensor_group_sensor_detail_view(request, sensor_group_id, sensor_id):
    sensor_group = get_object_or_404(SensorGroup, id=sensor_group_id)
    if sensor_group.user != request.user:
        return HttpResponse(djutils.get_json_error("ACCESS_DENIED"), status=403)

    if request.method == "DELETE":
        # TODO: change this to use a form
        #sensor_id = request.POST.get('sensorID', None)

        #sensor = get_object_or_404(Sensor, id=sensor_id)
        try:
            sensor = sensor_group.sensors.get(id=sensor_id)
            sensor_group.sensors.remove(sensor)
            #sensor_group.save()
            return HttpResponse(djutils.get_json_success(sensor_group.id))
        except Sensor.DoesNotExist:
            raise Http404
    else:
        raise NotImplementedError

@require_GET
def event_type_view(request, event_type_id=None):
    #log_request('event_type_view %s' % (event_type_id), request)

    if event_type_id != None:
        event = EventType.objects.get(id=event_type_id)
        return HttpResponse(json.dumps(to_dict(event)))
    else:
        events = EventType.objects.all().exclude(name__startswith='question')
        #return HttpResponse(utils.to_json_list(events))
        return HttpResponse(json.dumps([to_dict(x) for x in events]))


@access_required
@require_GET
def reference_consumption_view(request):
    #log_request('reference_consumption_view', request)

    owner_id = request.GET.get('user_id')
    if owner_id in (None, request.user.id):
        owner = request.user
    else:
        owner = User.objects.get(id=owner_id)

    # TODO: add a try except and return undefined if appropriate
    # filter the reading list for the selection period
    result = StudyInfo.objects.get(user=owner)

    return HttpResponse( json.dumps(to_dict(result)) )


@login_required
@require_GET
def user_view(request):
    if not request.user.is_staff:
        raise PermissionDenied

    users_list = User.objects.all()
    dict_list = [to_dict(x) for x in users_list]
    for d, u in zip(dict_list, users_list):
        d['sensors'] = [to_dict(x) for x in u.sensor_set.all().distinct()]
        #print u, '-- ', u.sensor_set.all()
    return HttpResponse(json.dumps(dict_list))



