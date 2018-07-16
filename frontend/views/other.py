from django.http import HttpResponse
from django.shortcuts import render, redirect, render_to_response
from sd_store.models import Sensor, SensorReading
from django.http import JsonResponse
from django import forms
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from datetime import datetime
from django.conf import settings


def default_context(request):
    is_device = "device" in request.GET
    return { 
        "sensors": Sensor.objects.all(), 
        "is_device": is_device, 
        "datetime": datetime.now() 
    }

def index(request):
    
    request.session['pick_selected'] = None
    del request.session['pick_selected']
    request.session.modified = True

    # Create the default user if needed
    if request.user.is_anonymous:
        new_user = authenticate(username=settings.SDSTORE_USER, password=settings.SDSTORE_PASS)
        if new_user is None:
            new_user = User.objects.create_user(settings.SDSTORE_USER, 'x@example.com', settings.SDSTORE_PASS)
            new_user.save()
        login(request, new_user)
    
    # GET Request
    if request.method != "POST":
        return render(request, "frontend/index.html", {})

    # POST request
    form = DataForm(request.POST)
    if not form.is_valid():
        return JsonResponse(dict(**form.errors, error="Request data invalid"))

    by_time = {}
    readings = SensorReading.objects\
        .filter(sensor=form.cleaned_data['sensor'])\
        .order_by("-timestamp")
        # .filter(timestamp__gte=form.cleaned_data['start'])\
        # .filter(timestamp__lte=form.cleaned_data['end'])\
   
    for r in readings[:60]:
        key = datetime.strftime(r.timestamp, "%Y-%m-%d %H:%M:%S")
        if key not in by_time:
            by_time[key] = {}
            by_time[key]['ts'] = key
        by_time[key][r.channel.name] = r.value

    return JsonResponse([ v for k, v in by_time.items() ], safe=False)


def picker(request):
    if request.method == "POST":
        request.session['pick_selected'] = {}

        if request.session['pick_channels']:
            sensor_channels = request.POST.getlist('channels')
            for sc in sensor_channels:
                sid = sc.split('_')[0]
                cid = sc.split('_')[1]
                sensor = Sensor.objects.get(id=int(sid))
                channel = sensor.channels.get(id=int(cid))
                if sensor.pk not in request.session['pick_selected']:
                    request.session['pick_selected'][sensor.pk] = []
                request.session['pick_selected'][sensor.pk].append(channel.pk)
            return redirect(request.session['pick_redirect'])

        else:
            sensors = request.POST.getlist('sensors')
            for spk in sensors:
                sensor = Sensor.objects.get(id=int(spk))
                request.session['pick_selected'][spk] = [ c.pk for c in sensor.channels.all() ]
            return redirect(request.session['pick_redirect'])

    return render(request, "frontend/picker.html")


def time(request):
    if "pick_selected" not in request.session:
        request.session['pick_redirect'] = "time"
        request.session['pick_channels'] = True
        request.session['pick_multiple'] = True
        return redirect('picker')
    return render(request, "frontend/time.html")


def vumeters(request):
    if "pick_selected" not in request.session:
        request.session['pick_redirect'] = "vumeters"
        request.session['pick_channels'] = True
        request.session['pick_multiple'] = True
        return redirect('picker')

    hide_volume = True
    hide_signal = True
    for sid, cids in request.session['pick_selected'].items():
        sensor = Sensor.objects.get(id=int(sid))
        for cid in cids:
            channel = sensor.channels.get(id=int(cid))
            if channel.name.lower() == "volume":
                hide_volume = False
            if channel.name.lower() == "rssi":
                hide_signal = False

    return render(request, "frontend/vumeters.html", dict(hide_signal=hide_signal, hide_volume=hide_volume))


def manual_refresh(request):
    if "pick_selected" not in request.session:
        request.session['pick_redirect'] = "manual_refresh"
        request.session['pick_channels'] = False
        request.session['pick_multiple'] = False
        return redirect('picker')
    return render(request, "frontend/vumeters_refresh.html")

class DataForm(forms.Form):
    start  = forms.DateTimeField(required=True, initial=datetime.now())
    end    = forms.DateTimeField(required=True)
    sensor = forms.ModelChoiceField(queryset=Sensor.objects.all())


def server_time(request):
    return JsonResponse({ 'ts': datetime.now().strftime('%Y-%m-%d %H:%M:%S') })