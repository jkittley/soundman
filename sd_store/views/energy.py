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

'''
Created on 22 Dec 2011

@author: enrico

Views related to energy data manipulation
'''
from datetime import datetime, timedelta, date
from time import mktime, time

from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.views.decorators.http import require_GET
from django.contrib.auth.models import Group
import json
from django.db.models import Sum, Min, Max

from ..models import SensorReading, Event, StudyInfo, Channel

import django.dispatch

from basicutils import djutils
from basicutils.decorators import access_required
from .. import sdutils
from basicutils.djutils import get_json_error, get_json_success
from django.views.decorators.csrf import csrf_exempt


event_created = django.dispatch.Signal(providing_args=["signal", ])

from ..forms import IntervalForm, SampledIntervalForm

from logging import getLogger
#from django.utils.datastructures import MultiValueDictKeyError
#from django.core.exceptions import ValidationError
from ..forms import EventForm
from ..models import EventType, Sensor #, Meter, SmartPlug, Button
logger = getLogger('custom')

#import logging
#logging.basicConfig(level=logging.DEBUG)
#logger = logging.getLogger()

def getSavings(weekTotal, baseline):
    weekBaseline = baseline * 7
#    if weekTotal > weekBaseline:
#        savings = -1 * (((weekTotal - weekBaseline) / weekBaseline) * 100)
#    else:
#        savings = (weekTotal / weekBaseline) * 100

    savings = (weekBaseline - weekTotal) / weekBaseline * 100

    return savings

def getRewards(ratio_savings, sum_of_weeks, baseline, other):
    if ratio_savings < 0:
        return 0

    reward = .25 * ratio_savings

    if (ratio_savings > 20) :
        reward += 5

    elif ratio_savings > 10:
        reward += 2.5

    return reward


@access_required
@require_GET
def meter_reading_view(request, data_type):
    djutils.log_request('meter_reading_view', request)

    form = SampledIntervalForm(request.GET)
    if not form.is_valid():
        return HttpResponseBadRequest(get_json_error(dict(form.errors)))

    meter_owner = djutils.get_requested_user(request)
    try:
        meter = Sensor.objects.get(id=request.GET['m_ID'])
    except KeyError:
        meter, _ = sdutils.get_meter(meter_owner)
    channel = Channel.objects.get(name='energy')

    requested_interval = form.cleaned_data['sampling_interval']
    start = form.cleaned_data['start']
    end = form.cleaned_data['end']

    if start >= end:
        return HttpResponseBadRequest(get_json_error('invalid interval requested'))

    #filter by interval

    #reading_list_gen = filter_according_to_interval_gen(meter, start, end, requested_interval, data_type)
    #reading_list_gen = list(reading_list_gen)
    #logger.debug('gen: ' + str([x.value for x in reading_list_gen[:4]]))
    #reading_list_sql = filter_according_to_interval_sql(meter, start, end, requested_interval, data_type)

    # print start, end, requested_interval
    reading_list = sdutils.filter_according_to_interval(meter, channel, start, end, requested_interval, data_type)
    result = {}
    result['data'] = [{'t': 1000 * mktime(x.timestamp.timetuple()),
                       'value': x.value} for x in list(reading_list)]

    # for d in result['data']:
    #     print d['t'], d['value']
    # print result

    if len(result['data']) == 0:
        #raise SensorReading.DoesNotExist('no sensor readings')
        result['max_datetime'] = 0
        result['min_datetime'] = 0
        return HttpResponse(json.dumps(result))

    min_datetime = SensorReading.objects.filter(sensor=meter,
                                                channel=channel
                    ).aggregate(Min('timestamp'))['timestamp__min']
    min_datetime = min_datetime.strftime(djutils.DATE_FMTS[0])
    result['min_datetime'] = min_datetime

    max_datetime = SensorReading.objects.filter(sensor=meter,
                                                channel=channel
                    ).aggregate(Max('timestamp'))['timestamp__max']
    max_datetime = max_datetime.strftime(djutils.DATE_FMTS[0])
    result['max_datetime'] = max_datetime

    return HttpResponse(json.dumps(result))

@access_required
@require_GET
def event_names_view(request):
    djutils.log_request('event_names_view', request)

    owner = djutils.get_requested_user(request)

    # if the user is part of the control group return no events
    # if Group.objects.get(name='control') in request.user.groups.all():
    #     return HttpResponse(json.dumps([]))

    # filter by user
    events = Event.objects.filter(sensor__user=owner).values_list('name').distinct()

    events = [x[0] for x in events]

    return HttpResponse(json.dumps(events))

@csrf_exempt
@access_required
def event_view(request, event_id=None):
    djutils.log_request('event_view %s' % (str(event_id)), request)

    logger.debug('event_view')

    owner = djutils.get_requested_user(request)
    #startTime = time.clock()
    if request.method == "GET":
        # if the user is part of the control group return no events
        # if Group.objects.get(name='control') in request.user.groups.all():
        #     return HttpResponse(json.dumps([]))

        if event_id != None:
            event = Event.objects.get(id = event_id)

            # augment json with baseline, max, consumption and data
            event_dict = sdutils.calculate_event(event)

            return HttpResponse(json.dumps(event_dict))
        else:
            logger.debug('entered else')
            # event_id not specified
            # get all events within interval
            form = IntervalForm(request.GET)
            if not form.is_valid():
                return HttpResponseBadRequest(get_json_error(dict(form.errors)))

            start = form.cleaned_data['start']
            end = form.cleaned_data['end']

            if start >= end:
                return HttpResponseBadRequest(get_json_error('invalid interval requested'))

            # filter by user
            events = Event.objects.filter(sensor__user=owner)
            events = events.filter(end__gte=start)
            events = events.filter(start__lte=end)

            # exclude suggestions overlapping events
            sugg_type = EventType.objects.get(name='question mark')
            # check that there are no overlapping events from the same user
            manual_events = Event.objects.filter(sensor__user=owner
                             ).filter(end__gte=start
                             ).filter(start__lte=end
                             ).exclude(event_type=sugg_type)

            # TODO: fix this!
            logger.debug('about to enter for loop')
            for ev in manual_events:
                # start < sugg.start < end
                events = events.exclude(event_type=sugg_type, start__gte=ev.start, start__lte=ev.end)
                # start < sugg.end < end
                events = events.exclude(event_type=sugg_type, end__gte=ev.start, end__lte=ev.end)
                # start < sugg.start < sugg.end < end
                events = events.exclude(event_type=sugg_type, start__lte=ev.start, end__gte=ev.end)
                events = events.exclude(event_type=sugg_type, start__gte=ev.start, end__lte=ev.end)

            logger.debug('about to call sdutils.calculate_event')
            events = [sdutils.calculate_event(ev) for ev in events]
            logger.debug('sdutils.calculate_event returned')

            return HttpResponse(json.dumps(events))

    elif request.method == "POST":
        event = None
        if event_id != None:
            event = Event.objects.get(id = event_id)
        # TODO: use a form for validation
        form = EventForm(request.POST, instance=event)
        if not form.is_valid():
            return HttpResponseBadRequest(get_json_error(dict(form.errors)))

        event = form.save(commit=False)
        #event.user = owner
        #sensor = Sensor.objects.get(id=request)
        event.event_type = EventType.objects.get(id=form.cleaned_data['event_type_id'])

        # check that there are no overlapping events from the same user
        dupes = Event.objects.filter(sensor__user=owner).exclude(id=event.id)
        # except suggestions!
        dupes = dupes.exclude(event_type=EventType.objects.get(name='question mark'))
        dupes1 = dupes.filter(start__gte=event.start).filter(start__lte=event.end)
        dupes2 = dupes.filter(end__gte=event.start).filter(end__lte=event.end)
        if dupes1.count() + dupes2.count() > 0:
            return HttpResponseBadRequest(get_json_error('overlapping event exists'))
        event.save()

        #FigureEnergy.recognition.data_interface.extractFeaturesFromDBEvent(event)
        event_created.send(Event.objects, event=event)

        #event.start = datetime.utcfromtimestamp(int(float(request.POST['start'])))
        #event.end = datetime.utcfromtimestamp(int(float(request.POST['end'])))
        #event.name = request.POST['name']
        #event.description = request.POST['description']

        #typeID = request.POST.get('event_type')
        #event.type = EventType.objects.get(id=typeID)

        #event.consumption = 0
        #event.baseline = 0
        #event.save()
#                if request.POST.get('metering_points_array', None) != None:
#                    metering_point_ids = eval(request.POST.get('metering_points_array', None))
#                    metering_points_found = []
#                    for metering_point_id in metering_point_ids:
#                        try:
#                            metering_point = MeteringPoint.objects.get(id = metering_point_id)
#                            metering_points_found.append(metering_point)
#                        except MeteringPoint.DoesNotExist:
#                            pass
#                    event.metering_points = metering_points_found
#                event.save()
        return HttpResponse(get_json_success(event.id))
    elif request.method == "DELETE":
        event = Event.objects.get(id = event_id)
        if event.sensor.user == owner:
            event_id = event.id
            event.delete()
            return HttpResponse(get_json_success(event_id))
        return HttpResponseForbidden(get_json_error("ACCESS_DENIED"))
    else:
        return HttpResponseBadRequest(get_json_error("NOT_GET_POST_OR_DELETE_REQUEST"))


@access_required
@require_GET
def always_on_view(request, data_type):
    meter_owner = djutils.get_requested_user(request)
    print("Request params:",request.GET.keys())

    if request.GET.get('m_ID',None) == None:
        meter, _ = sdutils.get_meter(meter_owner)
    else:
        meter = Sensor.objects.get(id=request.GET['m_ID'])
        
    channel = Channel.objects.get(name='energy')

    form = SampledIntervalForm(request.GET)
    if not form.is_valid():
        return HttpResponseBadRequest(get_json_error(dict(form.errors)))

    requested_interval = form.cleaned_data['sampling_interval']
    start = form.cleaned_data['start']
    end = form.cleaned_data['end']

    if start >= end:
        return HttpResponseBadRequest(get_json_error('invalid interval requested'))
    sr = SensorReading.objects.filter(sensor=meter, channel=channel)
    if not (sr.exists()):
        return HttpResponse(json.dumps([]))

    data_start = sr.aggregate(Min('timestamp'))['timestamp__min']
    data_end = sr.aggregate(Max('timestamp'))['timestamp__max']
    data_end += timedelta(seconds=channel.reading_frequency)

    start = max(start, data_start)
    end = min(end, data_end)

    baseline = sdutils.calculate_always_on(meter, channel, start, end, requested_interval, data_type)
    baseline = [{'t': 1000 * mktime(x[0].timetuple()), 'value': x[1]} for x in baseline]
    return HttpResponse(json.dumps(baseline))

@access_required
@require_GET
def total_energy_view(request):
    owner = djutils.get_requested_user(request)
    meter, channel = sdutils.get_meter(owner)

    form = IntervalForm(request.GET)
    if not form.is_valid():
        return HttpResponseBadRequest(get_json_error(dict(form.errors)))

    start = form.cleaned_data['start']
    end = form.cleaned_data['end']

    if start >= end:
        return HttpResponseBadRequest(get_json_error('invalid interval requested'))

    data_start = SensorReading.objects.filter(sensor=meter, channel=channel).aggregate(Min('timestamp'))['timestamp__min']
    data_end = SensorReading.objects.filter(sensor=meter, channel=channel).aggregate(Max('timestamp'))['timestamp__max']
    data_end += timedelta(seconds=channel.reading_frequency)

    start = max(start, data_start)
    end = min(end, data_end)

    #filter the reading list for the selection period
    reading_list = SensorReading.objects.filter(sensor=meter, channel=channel)
    reading_list = reading_list.filter(timestamp__gte=(start))
    reading_list = reading_list.filter(timestamp__lt=(end))

    total_energy = reading_list.aggregate(Sum('value'))['value__sum']

    return HttpResponse(json.dumps(total_energy))

@access_required
@require_GET
def total_energy_cost_view(request):
    owner = djutils.get_requested_user(request)
    meter, channel = sdutils.get_meter(owner)

    form = IntervalForm(request.GET)
    if not form.is_valid():
        return HttpResponseBadRequest(get_json_error(dict(form.errors)))

    start = form.cleaned_data['start']
    end = form.cleaned_data['end']

    if start >= end:
        return HttpResponseBadRequest(get_json_error('invalid interval requested'))

    data_start = SensorReading.objects.filter(sensor=meter, channel=channel).aggregate(Min('timestamp'))['timestamp__min']
    data_end = SensorReading.objects.filter(sensor=meter, channel=channel).aggregate(Max('timestamp'))['timestamp__max']
    data_end += timedelta(seconds=channel.reading_frequency)

    start = max(start, data_start)
    end = min(end, data_end)

    #filter the reading list for the selection period
    reading_list = SensorReading.objects.filter(sensor=meter, channel=channel)
    reading_list = reading_list.filter(timestamp__gte=(start))
    reading_list = reading_list.filter(timestamp__lte=(end))

    total_energy = reading_list.aggregate(Sum('value'))['value__sum']

    always_on_readings = sdutils.calculate_always_on(meter, channel, start, end, 120, 'energy')
    always_on = sum([x[1] for x in always_on_readings])

#    logger.debug('energy count: %d, always_on count: %d' % (reading_list.count(), len(always_on_readings)))
#    logger.debug('start: %s, end: %s' % (start, end))
#    logger.debug('data_start: %s, data_end: %s' % (data_start, data_end))

    # TODO: this introduces a dependency -- this is to be considered
    # a temporary implementation and a cleaner solution should be found
    # to make the code more properly modular
    try:
        from pricing import combined #@UnresolvedImport
        prices = combined.get_actual_prices(start, end, 0.5, 0.5)
        # TODO make this more precise
        avg_price = sum(prices) / float(len(prices))
        total_cost = total_energy * avg_price
        always_on_cost = always_on * avg_price
    except Exception as e:
        logger.error('pricing exception: ' + str(e))
        total_cost = 0
        always_on_cost = 0


    result = {}
    result['total_cost'] = total_cost
    result['always_on_cost'] = always_on_cost
    result['variable_load_cost'] = result['total_cost'] - result['always_on_cost']

    return HttpResponse(json.dumps(result))


@access_required
@require_GET
def savings_view(request):
    logger.debug('savings_view')

    owner = djutils.get_requested_user(request)
    meter, channel = sdutils.get_meter(owner)
    #Grab data we need
    #meter_data = SensorReading.objects.filter(meter = meter)
    study_data = StudyInfo.objects.filter(user=owner)

    baseline = study_data.values('baseline_consumption')[0]['baseline_consumption']
    start_time = study_data.values('start_date')[0]['start_date']
    #end_time = datetime.today()

    #Identify the week we are in.
    no_days_since_start = (datetime.today() - start_time).days;
    in_week = no_days_since_start / 7
    in_week = min(in_week, 4)

    no_days_from_week_start = no_days_since_start % 7
    start_from_sunday = date.today() - timedelta(days=no_days_from_week_start)

    end_from_yesterday = datetime.now()

    logger.debug("no_days_from_week_start, " + str(no_days_from_week_start))
    logger.debug("start_from_sunday, " + str(start_from_sunday))
    logger.debug("end_from_yesterday, " + str(end_from_yesterday))

    savings = ["na", "na", "na", "na"]
    rewards = [0, 0, 0 , 0]

    for week in range(0,in_week):
        weekStart = start_time + timedelta(days = 7 * week)
        weekEnd = start_time + timedelta(days = 7 * (week + 1))
        weekEnd = min(weekEnd, datetime.now())
        # Calculate sum from start to now.
        weekSum = SensorReading.objects.filter(sensor=meter, channel=channel
                                             ).filter(timestamp__gte = weekStart
                                             ).filter(timestamp__lte=weekEnd
                                             ).aggregate(Sum('value'))['value__sum']
        if weekSum is not None:
            week_savings = getSavings(weekSum, baseline)
            savings[week] = "%.2f" % (week_savings,)
            rewards[week] = getRewards(float(savings[week]), 1, 2 , 3)
            logger.debug('savings[%d]: %s' % (week, savings[week]))
            logger.debug('weekSum: %3.2f, baseline: %3.2f' % (weekSum, baseline))
            logger.debug('weekStart: %s, weekEnd: %s' % (weekStart, weekEnd))
        else:
            savings[week] = "n / a"
            rewards[week] = -1

        # TODO: integrate the rewards here..

    response = []
    jsonData = json.dumps({
                                    'week1_savings': savings[0],
                                    'week2_savings': savings[1],
                                    'week3_savings': savings[2],
                                    'week4_savings': savings[3],

                                    'week1_rewards': rewards[0],
                                    'week2_rewards': rewards[1],
                                    'week3_rewards': rewards[2],
                                    'week4_rewards': rewards[3]

                                    }, sort_keys=True, indent=4)
    response.append(jsonData)

    msg = '"user": "%s", "view": "%s", "response": {%s}' % (owner, 'savings_view', jsonData)
    logger.info(msg)

    return HttpResponse(response)

@access_required
@require_GET
def live_stats_view(request):
    owner = djutils.get_requested_user(request)
    meter, channel = sdutils.get_meter(owner)
    prediction_weekly = 0

    # TODO: spawn separate thread?
    recentTime = datetime.now() - timedelta(minutes=25)
    testList = SensorReading.objects.filter(sensor=meter, channel=channel)
    testList = testList.filter(timestamp__gte=recentTime)
    testList = testList.filter(timestamp__lte=datetime.now())
    if testList.count() == 0:
        pass
        # TODO TODO TODO -- Work out what this code did and decide what needs to happen.
        #try:
            #amUser = AlertMeUser.objects.get(user=owner)
            #alertme.update_user(amUser, sensor=meter, quick=True)
        #except AlertMeUser.DoesNotExist:
            #pass
        #except URLError:
            #pass
        #except Exception, e:
            #logger.error(str(e))
            #logger.error(str(e.__class__.__name__))

    # Grab the data we need
    reading_list = SensorReading.objects.filter(sensor=meter, channel=channel)

    # Todays total energy
    today = date.fromtimestamp(time())
    startTime = datetime(today.year, today.month, today.day, 0, 0, 0) # 12AM today

    reading_list_todays = reading_list
    reading_list_todays = reading_list_todays.filter(timestamp__gte = startTime).filter(timestamp__lte = datetime.now())

    if reading_list_todays.count() < 1:
        todays_total_energy = -1
    else:
        todays_total_energy = reading_list_todays.aggregate(Sum('value'))['value__sum']
    # End todays total energy

    # Average daily consumption (since the start of the users presence on system)
    min_date = reading_list.aggregate(Min('timestamp'))['timestamp__min']
    no_days = (datetime.now() - min_date).days

    if no_days == 0:
        average_energy_consumption = 0
    else:
        sum_daily_consumption = reading_list
        sum_daily_consumption = sum_daily_consumption.filter(timestamp__lte = datetime.now())

        if sum_daily_consumption.count() < 1:
            average_energy_consumption = -1
        else:
            sum_daily_consumption = sum_daily_consumption.aggregate(Sum('value'))['value__sum']
            average_energy_consumption = sum_daily_consumption / no_days
    # End average daily consumption

    # Consumed this week
    studyInfo = StudyInfo.objects.get(user = owner)
    delta = datetime.now() - studyInfo.start_date
    no_days_from_week_start = delta.days % 7
    startTime = date.today() - timedelta(days=no_days_from_week_start)

    week_consumption = reading_list
    week_consumption = week_consumption.filter(timestamp__gte = startTime).filter(timestamp__lte = datetime.now())

    if week_consumption.count() < 1:
        week_consumption = -1
    else:
        week_consumption = week_consumption.aggregate(Sum('value'))['value__sum']
    # End consumed this week

    # Prediction for the week
    if no_days_from_week_start > 0:
        prediction_weekly = (week_consumption / no_days_from_week_start) * 7
    else:
        # TODO: shall we say "n/a" ?
        #prediction_weekly = (week_consumption / startTime.hour) * 7 * 24
        prediction_weekly = -1
    # End prediction for the week.

    # Reference Consumption (i.e. StudyInfo baseline)
    baseline = studyInfo.baseline_consumption

    response = []
    jsonData = json.dumps({
                            'todays_total': todays_total_energy,
                            'average_daily': average_energy_consumption,
                            'consumed_weekly': week_consumption,
                            'prediction_weekly': prediction_weekly,
                            'baseline': baseline,
                            'week_start': startTime.strftime('%A')
                            }, sort_keys=True, indent=4)
    response.append(jsonData)

    msg = '"user": "%s", "view": "%s", "response": {%s}' % (owner, 'live_stats_view', jsonData)
    logger.info(msg)

    return HttpResponse(response)


