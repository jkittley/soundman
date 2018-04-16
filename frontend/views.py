from django.http import HttpResponse
from django.shortcuts import render
from sd_store.models import Sensor 

def index(request):

    sensors = Sensor.objects.all()

    return render(request, "frontend/index.html", { "sensors": sensors })