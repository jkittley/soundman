from django.http import HttpResponse
from django.shortcuts import render, redirect
from sd_store.models import Sensor, SensorReading
from django.http import JsonResponse
from django import forms
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from datetime import datetime
from django.conf import settings

def index(request):
    sensors = Sensor.objects.all()
    is_device = "device" in request.GET

    # Create the default user if needed
    if request.user.is_anonymous:
        new_user = authenticate(username=settings.SDSTORE_USER, password=settings.SDSTORE_PASS)
        if new_user is None:
            new_user = User.objects.create_user(settings.SDSTORE_USER, 'x@example.com', settings.SDSTORE_PASS)
            new_user.save()
        login(request, new_user)
    
    # GET Request
    if request.method != "POST":
        return render(request, "frontend/index.html", { "sensors": sensors, "is_device": is_device, "datetime": datetime.now() })

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
   
    for r in readings[:30]:
        key = datetime.strftime(r.timestamp, "%Y-%m-%d %H:%M:%S")
        if key not in by_time:
            by_time[key] = {}
            by_time[key]['ts'] = key
        by_time[key][r.channel.name] = r.value

    return JsonResponse([ v for k, v in by_time.items() ], safe=False)



class DataForm(forms.Form):
    start  = forms.DateTimeField(required=True, initial=datetime.now())
    end    = forms.DateTimeField(required=True)
    sensor = forms.ModelChoiceField(queryset=Sensor.objects.all())


def server_time(request):
    return JsonResponse({ 'ts': datetime.now().strftime('%Y-%m-%d %H:%M:%S') })