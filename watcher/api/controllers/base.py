# -*- encoding: utf-8 -*-
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

import datetime
import functools

import microversion_parse
from webob import exc
import wsme
from wsme import types as wtypes


class APIBase(wtypes.Base):

    created_at = wsme.wsattr(datetime.datetime, readonly=True)
    """The time in UTC at which the object is created"""

    updated_at = wsme.wsattr(datetime.datetime, readonly=True)
    """The time in UTC at which the object is updated"""

    deleted_at = wsme.wsattr(datetime.datetime, readonly=True)
    """The time in UTC at which the object is deleted"""

    def as_dict(self):
        """Render this object as a dict of its fields."""
        return dict((k, getattr(self, k))
                    for k in self.fields
                    if hasattr(self, k) and
                    getattr(self, k) != wsme.Unset)

    def unset_fields_except(self, except_list=None):
        """Unset fields so they don't appear in the message body.

        :param except_list: A list of fields that won't be touched.

        """
        if except_list is None:
            except_list = []

        for k in self.as_dict():
            if k not in except_list:
                setattr(self, k, wsme.Unset)


@functools.total_ordering
class Version(object):
    """API Version object."""

    string = 'OpenStack-API-Version'
    """HTTP Header string carrying the requested version"""

    min_string = 'OpenStack-API-Minimum-Version'
    """HTTP response header"""

    max_string = 'OpenStack-API-Maximum-Version'
    """HTTP response header"""

    def __init__(self, headers, default_version, latest_version):
        """Create an API Version object from the supplied headers.

        :param headers: webob headers
        :param default_version: version to use if not specified in headers
        :param latest_version: version to use if latest is requested
        :raises: webob.HTTPNotAcceptable

        """
        (self.major, self.minor) = Version.parse_headers(
            headers, default_version, latest_version)

    def __repr__(self):
        return '%s.%s' % (self.major, self.minor)

    @staticmethod
    def parse_headers(headers, default_version, latest_version):
        """Determine the API version requested based on the headers supplied.

        :param headers: webob headers
        :param default_version: version to use if not specified in headers
        :param latest_version: version to use if latest is requested
        :returns: a tuple of (major, minor) version numbers
        :raises: webob.HTTPNotAcceptable

        """
        version_str = microversion_parse.get_version(
            headers,
            service_type='infra-optim')

        minimal_version = (1, 0)

        if version_str is None:
            # If requested header is wrong, Watcher answers with the minimal
            # supported version.
            return minimal_version

        if version_str.lower() == 'latest':
            parse_str = latest_version
        else:
            parse_str = version_str

        try:
            version = tuple(int(i) for i in parse_str.split('.'))
        except ValueError:
            version = minimal_version

        # NOTE (alexchadin): Old python-watcherclient sends requests with
        # value of version header is "1". It should be transformed to 1.0 as
        # it was supposed to be.
        if len(version) == 1 and version[0] == 1:
            version = minimal_version

        if len(version) != 2:
            raise exc.HTTPNotAcceptable(
                "Invalid value for %s header" % Version.string)
        return version

    def __gt__(self, other):
        return (self.major, self.minor) > (other.major, other.minor)

    def __eq__(self, other):
        return (self.major, self.minor) == (other.major, other.minor)

    def __ne__(self, other):
        return not self.__eq__(other)
