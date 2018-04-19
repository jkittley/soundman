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

views that simply call external services (e.g. AlertMe)
'''
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.http import require_GET
from urllib.request import urlopen, Request
from urllib.error import URLError

from django.conf import settings

from .. import sdutils
from basicutils import djutils
from basicutils.decorators import access_required

import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger()


@require_GET
def check_alertme_login_view(request):
    theurl = 'https://api.alertme.com/v5/login'
#    if liveServers:
#        theurl = 'https://secure.alertme.com/myhome/login/'

    username = request.GET['username']
    password = request.GET['password']
    import urllib
    import urllib2
    urlopen = urllib2.urlopen
    Request = urllib2.Request

    txdata = urllib.urlencode(
        {"username": username, "password": password, "caller": "op106"})
    txheaders = {
        'User-agent': 'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)'}

    try:
        #f = opener.open(theurl, txdata)
        req = Request(theurl, txdata, txheaders)
        f = urlopen(req)
        # print repr(f)
        response = f.read()
        # print response
        f.close()
        return HttpResponse(str(response))

    except urllib2.HTTPError as he:
        logging.error('exception %s from request: %s; %s' %
                      (he, theurl, txdata))
        return HttpResponseBadRequest(str(he))


@access_required
@require_GET
def power_now_view(request):
    user = djutils.get_requested_user(request)
    meter, _ = sdutils.get_meter(user)

    url = settings.PROTECTED_SERVER_URL
    url += "power_now?fe_username=" + user.username
    url += "&meter_type=" + meter.sensor_type
    url += "&meter_mac=" + meter.mac
    #url += "&escrow_password=" + FE_ESCROW_PASSWORD

    request = Request(url)
    try:
        response = urlopen(request).read()
    except URLError as e:
        logger.error(
            "protected server not answering requests. Is it turned on? Is settings.PROTECTED_SERVER_URL correct?")
        return HttpResponse(e, status="502")
    return HttpResponse(str(response))

######


@access_required
@require_GET
def update_view(request):
    user = djutils.get_requested_user(request)
    meter, _ = sdutils.get_meter(user)

    url = settings.PROTECTED_SERVER_URL
    url += "update?fe_username=" + user.username
    url += "&meter_mac=" + meter.mac

    request = Request(url)
    try:
        response = urlopen(request).read()
        if response != 'ok':
            logger.error("error when updating from protected server")
    except URLError as e:
        logger.error("protected server not answering requests -- " + str(e))


# TODO: the following methods are not compatible with the protected_store setup

# TODO: this method is specific to AlertMe
#@access_required
#@require_GET
# def event_log_view(request):
#    user = djutils.get_requested_user(request)
#
#    alertme_user = AlertMeUser.objects.get(user=user)
#    response = alertme.get_event_log(alertme_user)
#
#    return HttpResponse( response )
#
# TODO: this method is specific to AlertMe
#@access_required
#@require_GET
# def smart_plug_state_view(request):
#    user = djutils.get_requested_user(request)
#
#    smartplug = SmartPlug.objects.get(user=user)
#    alertme_user = AlertMeUser.objects.get(user=user)
#    response = alertme.get_smart_plug_state(alertme_user, smartplug.mac)
#
#    return HttpResponse( response )
#
#@access_required
#@require_GET
# def toggle_smart_plug_view(request):
#    user = djutils.get_requested_user(request)
#
#    smartplug = SmartPlug.objects.get(user=user)
#    alertme_user = AlertMeUser.objects.get(user=user)
#    response = alertme.toggle_smartplug(alertme_user, smartplug.mac)
#
#    return HttpResponse( response )
#
#@access_required
#@require_GET
# def smartplug_on_view(request):
#    user = djutils.get_requested_user(request)
#
#    smartplug = SmartPlug.objects.get(user=user)
#    #alertme_user = AlertMeUser.objects.get(user=user)
#    response = alertme.smart_plug_switch(user, smartplug.mac, "on")
#
#    return HttpResponse( response )
#
#@access_required
#@require_GET
# def smartplug_off_view(request):
#    user = djutils.get_requested_user(request)
#
#    smartplug = SmartPlug.objects.get(user=user)
#    alertme_user = AlertMeUser.objects.get(user=user)
#    response = alertme.smart_plug_switch(alertme_user, smartplug.mac, "off")
#
#    return HttpResponse( response )
#
#@access_required
#@require_GET
# def button_flash_on_view(request):
#    user = djutils.get_requested_user(request)
#
#    button = Button.objects.get(user=user)
#    alertme_user = AlertMeUser.objects.get(user=user)
#    response = alertme.smart_plug_switch(alertme_user, button.mac, "placing")
#
#    return HttpResponse( response )
#
#@access_required
#@require_GET
# def button_flash_off_view(request):
#    user = djutils.get_requested_user(request)
#
#    button = Button.objects.get(user=user)
#    alertme_user = AlertMeUser.objects.get(user=user)
#    response = alertme.smart_plug_switch(alertme_user, button.mac, "normal")
#
#    return HttpResponse( response )
#
#@access_required
#@permission_required('fe.backend.all_access', '/')
#@require_GET
# def toggle_user_battery_view(request):
#    user = djutils.get_requested_user(request)
#
#    battery_state = request.GET.get('state')
#
#    smartplug_owner = user
#    if smartplug_owner == None:
#        raise User.DoesNotExist
#
#    smartplug = SmartPlug.objects.get(user=smartplug_owner)
#    print "SMART PLUG FOUND FOR USER ", smartplug_owner, smartplug
#    if smartplug == None:
#        raise SmartPlug.DoesNotExist
#
#    alertme_user = AlertMeUser.objects.get(user=user)
#    response = alertme.smart_plug_switch(alertme_user, smartplug.mac, battery_state)
#    return HttpResponse(response)
#
# TODO: Extend this to other devices like smartplugs. This all depends on the model we take to handle different device types.
#@access_required
#@require_GET
# def device_presence_view(request):
#    user = djutils.get_requested_user(request)
#
#    meter = sdutils.get_meter(user, None)
#    alertme_user = AlertMeUser.objects.get(user=user)
#    device = {}
#    device['type'] = meter.type
#    device['id'] = meter.mac
#    presence = alertme.get_device_presence(alertme_user, device)
#
#    response = {}
#    response['device'] = meter.name
#    response['presence'] = json.loads(presence)
#
#    return HttpResponse( json.dumps(response) )
