from django.http import HttpResponse
from django.shortcuts import render
from sd_store.models import Sensor, SensorReading
from django.http import JsonResponse
from django import forms
from datetime import datetime

def index(request):
    sensors = Sensor.objects.all()
    
    if request.method != "POST":
        return render(request, "frontend/index.html", { "sensors": sensors })

    form = DataForm(request.POST)
    if not form.is_valid():
        return JsonResponse(dict(**form.errors, error="Request data invalid"))

    by_time = {}
    readings = SensorReading.objects\
        .filter(sensor=form.cleaned_data['sensor'])\
        .order_by("-timestamp")
        # .filter(timestamp__gte=form.cleaned_data['start'])\
        # .filter(timestamp__lte=form.cleaned_data['end'])\
   
    for r in readings[:25]:
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


