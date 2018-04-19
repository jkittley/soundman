# encoding:UTF-8

'''
Created on 22 Dec 2011

@author: enrico
'''
from logging import getLogger
logger = getLogger('custom')

from urllib import parse as urlparse

from django.conf import settings
from django.http import HttpResponseForbidden
from django.utils.decorators import available_attrs
from django.contrib.auth.decorators import REDIRECT_FIELD_NAME
from django.contrib.auth.models import User
from django.contrib.auth.views import redirect_to_login

try:
    from functools import wraps
except ImportError:
    from django.utils.functional import wraps  # Python 2.4 fallback.

from basicutils.djutils import get_json_error, can_access_user_data


def access_required(view_func):
    login_url = None
    redirect_field_name = REDIRECT_FIELD_NAME

    @wraps(view_func, assigned=available_attrs(view_func))
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated():
            # does the request contain a user?
            owner = request.user
            # can the user access the data?
            if can_access_user_data(owner, request.user):
                return view_func(request, *args, **kwargs)
            else:
                return HttpResponseForbidden(get_json_error('ACCESS_DENIED'))
        path = request.build_absolute_uri()
        # If the login url is the same scheme and net location then just
        # use the path as the "next" url.
        login_scheme, login_netloc = urlparse.urlparse(login_url or
                                                       settings.LOGIN_URL)[:2]
        current_scheme, current_netloc = urlparse.urlparse(path)[:2]
        if ((not login_scheme or login_scheme == current_scheme) and
                (not login_netloc or login_netloc == current_netloc)):
            path = request.get_full_path()
        return redirect_to_login(path, login_url, redirect_field_name)
    return _wrapped_view


def log_request(view_func):
    @wraps(view_func, assigned=available_attrs(view_func))
    def _wrapped_view(request, *args, **kwargs):
        userId = request.user.id
        try:
            user = User.objects.get(id=userId)
        except Exception as e:
            logger.debug('Exception: ' + str(e))
            user = str(userId)
        #user = 'undef'

        paramsDict = {}
        if request.method == "POST":
            paramsDict = request.POST
        elif request.method == "GET":
            paramsDict = request.GET
        else:
            pass

        params = ', '.join(['"%s": "%s"' % (k, v)
                            for k, v in paramsDict.items()])

        msg = '"user": "%s", "view": "%s", "%s": {%s}' % (
            user, view_func.__name__, request.method, params)
        logger.info(msg)

        return view_func(request, *args, **kwargs)

    return _wrapped_view
