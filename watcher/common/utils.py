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

from jsonschema import validators
from oslo_config import cfg
from oslo_log import log as logging

import re
import six
import uuid


from watcher._i18n import _LW

UTILS_OPTS = [
    cfg.StrOpt('rootwrap_config',
               default="/etc/watcher/rootwrap.conf",
               help='Path to the rootwrap configuration file to use for '
                    'running commands as root.'),
    cfg.StrOpt('tempdir',
               help='Explicitly specify the temporary working directory.'),
]

CONF = cfg.CONF
CONF.register_opts(UTILS_OPTS)

LOG = logging.getLogger(__name__)


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


def safe_rstrip(value, chars=None):
    """Removes trailing characters from a string if that does not make it empty

    :param value: A string value that will be stripped.
    :param chars: Characters to remove.
    :return: Stripped value.

    """
    if not isinstance(value, six.string_types):
        LOG.warning(_LW(
            "Failed to remove trailing character. Returning original object."
            "Supplied object is not a string: %s,"), value)
        return value

    return value.rstrip(chars) or value


def generate_uuid():
    return str(uuid.uuid4())


def is_int_like(val):
    """Check if a value looks like an int."""
    try:
        return str(int(val)) == str(val)
    except Exception:
        return False


def is_uuid_like(val):
    """Returns validation of a value as a UUID.

    For our purposes, a UUID is a canonical form string:
    aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa

    """
    try:
        return str(uuid.UUID(val)) == val
    except (TypeError, ValueError, AttributeError):
        return False


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
    return (isinstance(hostname, six.string_types) and
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
            if "default" in subschema:
                instance.setdefault(prop, subschema["default"])

            for error in validate_properties(
                validator, properties, instance, schema,
            ):
                yield error

    return validators.extend(
        validator_class, {"properties": set_defaults},
    )

DefaultValidatingDraft4Validator = extend_with_default(
    validators.Draft4Validator)
