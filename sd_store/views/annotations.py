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

from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.views.decorators.http import require_GET
from django.views.decorators.csrf import csrf_exempt

from basicutils import djutils
from basicutils.decorators import access_required
from ..models import Annotation, SensorChannelPair
from basicutils.djutils import get_json_error, get_json_success
from ..forms import IntervalForm, AnnotationForm
import json
from basicutils.djutils import to_dict


@csrf_exempt
@access_required
def annotation_view(request, annotation_id=None):
    owner = djutils.get_requested_user(request)
    if request.method == "GET":

        if annotation_id != None:
            annotation = Annotation.objects.get(id=annotation_id)
            return HttpResponse(json.dumps(to_dict(annotation)))
        else:
            # annotation_id not specified
            # get all annotations within interval
            form = IntervalForm(request.GET)
            if not form.is_valid():
                return HttpResponseBadRequest(get_json_error(dict(form.errors)))

            start = form.cleaned_data['start']
            end = form.cleaned_data['end']

            if start >= end:
                return HttpResponseBadRequest(get_json_error('invalid interval requested'))

            # filter by user
            annotations = Annotation.objects.filter(user=owner)
            annotations = annotations.filter(end__gte=start)
            annotations = annotations.filter(start__lte=end)
            result = [to_dict(annotation) for annotation in annotations]
            return HttpResponse(json.dumps(result))

    elif request.method == "POST":
        # print "In here..."
        username = request.POST.get('username')

        annotation = None
        if annotation_id != None:
            annotation = Annotation.objects.get(id=annotation_id)

        in_pairs = json.loads(request.POST.get('pairs'))
        pairs = []
        for in_pair in in_pairs:
            # print in_pair
            try:
                pair = SensorChannelPair.objects.get(
                    sensor=in_pair['sensor']['id'], channel=in_pair['channel']['id'])
            except:
                return HttpResponseBadRequest(get_json_error("invalid pair"))
            pairs.append(pair)

        if len(pairs) == 0:
            return HttpResponseBadRequest(get_json_error("no pairs for annotation"))

        form = AnnotationForm(request.POST, instance=annotation)
        if not form.is_valid():
            return HttpResponseBadRequest(get_json_error(dict(form.errors)))
        # print "Now in here."
        annotation = form.save(commit=False)
        annotation.user = owner
        annotation.save()
        annotation.pairs = pairs
        annotation.save()

        return HttpResponse(get_json_success(annotation.id))
    elif request.method == "DELETE":
        annotation = Annotation.objects.get(id=annotation_id)
        if annotation.user == owner:
            annotation_id = annotation.id
            annotation.delete()
            return HttpResponse(get_json_success(annotation_id))
        return HttpResponseForbidden(get_json_error("ACCESS_DENIED"))
    else:
        return HttpResponseBadRequest(get_json_error("NOT_GET_POST_OR_DELETE_REQUEST"))
