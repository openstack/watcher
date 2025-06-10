# -*- encoding: utf-8 -*-
# Copyright (c) 2015 b<>com
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Utilities and helper functions."""

import asyncio
import datetime
import inspect
import re

from croniter import croniter
import eventlet
from eventlet import tpool

from jsonschema import validators
from oslo_config import cfg
from oslo_log import log
from oslo_utils import strutils
from oslo_utils import uuidutils

from watcher.common import exception

CONF = cfg.CONF

LOG = log.getLogger(__name__)


class Struct(dict):
    """Specialized dict where you access an item like an attribute

    >>> struct = Struct()
    >>> struct['a'] = 1
    >>> struct.b = 2
    >>> assert struct.a == 1
    >>> assert struct['b'] == 2
    """

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name, value):
        try:
            self[name] = value
        except KeyError:
            raise AttributeError(name)


generate_uuid = uuidutils.generate_uuid
is_uuid_like = uuidutils.is_uuid_like
is_int_like = strutils.is_int_like


def is_cron_like(value):
    """Return True is submitted value is like cron syntax"""
    try:
        croniter(value, datetime.datetime.now())
    except Exception as e:
        raise exception.CronFormatIsInvalid(message=str(e))
    return True


def safe_rstrip(value, chars=None):
    """Removes trailing characters from a string if that does not make it empty

    :param value: A string value that will be stripped.
    :param chars: Characters to remove.
    :return: Stripped value.

    """
    if not isinstance(value, str):
        LOG.warning(
            "Failed to remove trailing character. Returning original object."
            "Supplied object is not a string: %s,", value)
        return value

    return value.rstrip(chars) or value


def is_hostname_safe(hostname):
    """Determine if the supplied hostname is RFC compliant.

    Check that the supplied hostname conforms to:
        * http://en.wikipedia.org/wiki/Hostname
        * http://tools.ietf.org/html/rfc952
        * http://tools.ietf.org/html/rfc1123

    :param hostname: The hostname to be validated.
    :returns: True if valid. False if not.

    """
    m = r'^[a-z0-9]([a-z0-9\-]{0,61}[a-z0-9])?$'
    return (isinstance(hostname, str) and
            (re.match(m, hostname) is not None))


def get_cls_import_path(cls):
    """Return the import path of a given class"""
    module = cls.__module__
    if module is None or module == str.__module__:
        return cls.__name__
    return module + '.' + cls.__name__


# Default value feedback extension as jsonschema doesn't support it
def extend_with_default(validator_class):
    validate_properties = validator_class.VALIDATORS["properties"]

    def set_defaults(validator, properties, instance, schema):
        for prop, subschema in properties.items():
            if "default" in subschema and instance is not None:
                instance.setdefault(prop, subschema["default"])

            for error in validate_properties(
                validator, properties, instance, schema
            ):
                yield error

    return validators.extend(validator_class,
                             {"properties": set_defaults})


# Parameter strict check extension as jsonschema doesn't support it
def extend_with_strict_schema(validator_class):
    validate_properties = validator_class.VALIDATORS["properties"]

    def strict_schema(validator, properties, instance, schema):
        if instance is None:
            return

        for para in instance.keys():
            if para not in properties.keys():
                raise exception.AuditParameterNotAllowed(parameter=para)

            for error in validate_properties(
                validator, properties, instance, schema
            ):
                yield error

    return validators.extend(validator_class, {"properties": strict_schema})


StrictDefaultValidatingDraft4Validator = extend_with_default(
    extend_with_strict_schema(validators.Draft4Validator))


Draft4Validator = validators.Draft4Validator


# Some clients (e.g. MAAS) use asyncio, which isn't compatible with Eventlet.
# As a workaround, we're delegating such calls to a native thread.
def async_compat_call(f, *args, **kwargs):
    timeout = kwargs.pop('timeout', None)

    async def async_wrapper():
        ret = f(*args, **kwargs)
        if inspect.isawaitable(ret):
            return await asyncio.wait_for(ret, timeout)
        return ret

    def tpool_wrapper():
        # This will run in a separate native thread. Ideally, there should be
        # a single thread permanently running an asyncio loop, but for
        # convenience we'll use eventlet.tpool, which leverages a thread pool.
        #
        # That being considered, we're setting up a temporary asyncio loop to
        # handle this call.
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(async_wrapper())
        finally:
            loop.close()

    # We'll use eventlet timeouts as an extra precaution and asyncio timeouts
    # to avoid lingering threads. For consistency, we'll convert eventlet
    # timeout exceptions to asyncio timeout errors.
    with eventlet.timeout.Timeout(
            seconds=timeout,
            exception=asyncio.TimeoutError("Timeout: %ss" % timeout)):
        return tpool.execute(tpool_wrapper)
