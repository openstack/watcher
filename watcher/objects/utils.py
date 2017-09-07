#    Copyright 2013 IBM Corp.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""Utility methods for objects"""

import ast
import datetime

import iso8601
import netaddr
from oslo_utils import timeutils
import six

from watcher._i18n import _


def datetime_or_none(value, tzinfo_aware=False):
    """Validate a datetime or None value."""
    if value is None:
        return None
    if isinstance(value, six.string_types):
        # NOTE(danms): Being tolerant of isotime strings here will help us
        # during our objects transition
        value = timeutils.parse_isotime(value)
    elif not isinstance(value, datetime.datetime):
        raise ValueError(
            _("A datetime.datetime is required here. Got %s"), value)

    if value.utcoffset() is None and tzinfo_aware:
        # NOTE(danms): Legacy objects from sqlalchemy are stored in UTC,
        # but are returned without a timezone attached.
        # As a transitional aid, assume a tz-naive object is in UTC.
        value = value.replace(tzinfo=iso8601.UTC)
    elif not tzinfo_aware:
        value = value.replace(tzinfo=None)

    return value


def datetime_or_str_or_none(val, tzinfo_aware=False):
    if isinstance(val, six.string_types):
        return timeutils.parse_isotime(val)
    return datetime_or_none(val, tzinfo_aware=tzinfo_aware)


def numeric_or_none(val):
    """Attempt to parse an integer value, or None."""
    if val is None:
        return val
    else:
        f_val = float(val)
        return f_val if not f_val.is_integer() else val


def int_or_none(val):
    """Attempt to parse an integer value, or None."""
    if val is None:
        return val
    else:
        return int(val)


def str_or_none(val):
    """Attempt to stringify a value to unicode, or None."""
    if val is None:
        return val
    else:
        return six.text_type(val)


def dict_or_none(val):
    """Attempt to dictify a value, or None."""
    if val is None:
        return {}
    elif isinstance(val, six.string_types):
        return dict(ast.literal_eval(val))
    else:
        try:
            return dict(val)
        except ValueError:
            return {}


def list_or_none(val):
    """Attempt to listify a value, or None."""
    if val is None:
        return []
    elif isinstance(val, six.string_types):
        return list(ast.literal_eval(val))
    else:
        try:
            return list(val)
        except ValueError:
            return []


def ip_or_none(version):
    """Return a version-specific IP address validator."""
    def validator(val, version=version):
        if val is None:
            return val
        else:
            return netaddr.IPAddress(val, version=version)
    return validator


def nested_object_or_none(objclass):
    def validator(val, objclass=objclass):
        if val is None or isinstance(val, objclass):
            return val
        raise ValueError(_("An object of class %s is required here")
                         % objclass)
    return validator


def dt_serializer(name):
    """Return a datetime serializer for a named attribute."""
    def serializer(self, name=name):
        if getattr(self, name) is not None:
            return datetime.datetime.isoformat(getattr(self, name))
        else:
            return None
    return serializer


def dt_deserializer(val):
    """A deserializer method for datetime attributes."""
    if val is None:
        return None
    else:
        return timeutils.parse_isotime(val)


def obj_serializer(name):
    def serializer(self, name=name):
        if getattr(self, name) is not None:
            return getattr(self, name).obj_to_primitive()
        else:
            return None
    return serializer
