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
Created on 12 Jan 2012

@author: enrico
'''
from datetime import datetime
from django import forms
from django.utils.translation import ugettext_lazy as _

from sd_store.models import Event, Annotation, SensorChannelPair  # Booking,

from basicutils.djutils import DATE_FMTS


class JSTimestampField(forms.fields.IntegerField):
    default_error_messages = {
        'invalid': _(u'Enter a valid timestamp.'),
    }

    def to_python(self, value):
        """
        Validates that float() can be called on the input. Returns the result
        of float(). Returns None for empty values.
        """
        value = super(forms.fields.IntegerField, self).to_python(value)
        if value in forms.fields.validators.EMPTY_VALUES:
            return None
        if self.localize:
            value = forms.fields.formats.sanitize_separators(value)
        try:
            value = float(value)
            value = datetime.fromtimestamp(value / 1000)
        except (ValueError, TypeError):
            raise forms.fields.ValidationError(self.error_messages['invalid'])
        return value


class RawDataForm(forms.Form):
    value = forms.FloatField()
    key = forms.CharField(max_length=32)
    dt = forms.DateTimeField(input_formats=DATE_FMTS, required=False)


class ThresholdDeltaForm(forms.Form):
    threshold = forms.FloatField()
    delta = forms.FloatField()


class IntervalForm(forms.Form):
    # start and end are passed as timestamps
    start = forms.DateTimeField(input_formats=DATE_FMTS)
    end = forms.DateTimeField(input_formats=DATE_FMTS)


class SampledIntervalForm(IntervalForm):
    sampling_interval = forms.IntegerField(min_value=0)


class AnnotationForm(forms.ModelForm):
    start = forms.DateTimeField(input_formats=DATE_FMTS)
    end = forms.DateTimeField(input_formats=DATE_FMTS)

    class Meta:
        model = Annotation
        exclude = ('user', 'pairs')

    def clean(self):
        cleaned_data = self.cleaned_data
        start = cleaned_data.get("start")
        end = cleaned_data.get("end")
        if start and end:
            if start >= end:
                raise forms.ValidationError(
                    "Annotation start must be before event end.")
        return cleaned_data


class EventForm(forms.ModelForm):
    start = forms.DateTimeField(input_formats=DATE_FMTS)
    #start = JSTimestampField()
    end = forms.DateTimeField(input_formats=DATE_FMTS)
    #end = JSTimestampField()
    event_type_id = forms.IntegerField()

    class Meta:
        model = Event
        exclude = ('user', 'event_type')
    #

    def clean(self):
        cleaned_data = self.cleaned_data
        start = cleaned_data.get("start")
        end = cleaned_data.get("end")
        if start and end:
            if start >= end:
                raise forms.ValidationError(
                    "Event start must be before event end.")
        return cleaned_data

    #

#
