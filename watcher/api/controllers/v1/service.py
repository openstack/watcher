# -*- encoding: utf-8 -*-
# Copyright (c) 2016 Servionica
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

"""
Service mechanism provides ability to monitor Watcher services state.
"""

import datetime
from oslo_config import cfg
from oslo_log import log
from oslo_utils import timeutils
import pecan
from pecan import rest
from wsme import types as wtypes
import wsmeext.pecan as wsme_pecan

from watcher.api.controllers import base
from watcher.api.controllers import link
from watcher.api.controllers.v1 import collection
from watcher.api.controllers.v1 import utils as api_utils
from watcher.common import context
from watcher.common import exception
from watcher.common import policy
from watcher import objects


CONF = cfg.CONF
LOG = log.getLogger(__name__)


def hide_fields_in_newer_versions(obj):
    """This method hides fields that were added in newer API versions.

    Certain node fields were introduced at certain API versions.
    These fields are only made available when the request's API version
    matches or exceeds the versions when these fields were introduced.
    """
    pass


class Service(base.APIBase):
    """API representation of a service.

    This class enforces type checking and value constraints, and converts
    between the internal object model and the API representation of a service.
    """

    _status = None
    _context = context.RequestContext(is_admin=True)

    def _get_status(self):
        return self._status

    def _set_status(self, id):
        service = objects.Service.get(pecan.request.context, id)
        last_heartbeat = (service.last_seen_up or service.updated_at or
                          service.created_at)
        if isinstance(last_heartbeat, str):
            # NOTE(russellb) If this service came in over rpc via
            # conductor, then the timestamp will be a string and needs to be
            # converted back to a datetime.
            last_heartbeat = timeutils.parse_strtime(last_heartbeat)
        else:
            # Objects have proper UTC timezones, but the timeutils comparison
            # below does not (and will fail)
            last_heartbeat = last_heartbeat.replace(tzinfo=None)
        elapsed = timeutils.delta_seconds(last_heartbeat, timeutils.utcnow())
        is_up = abs(elapsed) <= CONF.service_down_time
        if not is_up:
            LOG.warning('Seems service %(name)s on host %(host)s is down. '
                        'Last heartbeat was %(lhb)s.'
                        'Elapsed time is %(el)s',
                        {'name': service.name,
                         'host': service.host,
                         'lhb': str(last_heartbeat), 'el': str(elapsed)})
            self._status = objects.service.ServiceStatus.FAILED
        else:
            self._status = objects.service.ServiceStatus.ACTIVE

    id = wtypes.wsattr(int, readonly=True)
    """ID for this service."""

    name = wtypes.text
    """Name of the service."""

    host = wtypes.text
    """Host where service is placed on."""

    last_seen_up = wtypes.wsattr(datetime.datetime, readonly=True)
    """Time when Watcher service sent latest heartbeat."""

    status = wtypes.wsproperty(wtypes.text, _get_status, _set_status,
                               mandatory=True)

    links = wtypes.wsattr([link.Link], readonly=True)
    """A list containing a self link."""

    def __init__(self, **kwargs):
        super(Service, self).__init__()

        fields = list(objects.Service.fields) + ['status']
        self.fields = []
        for field in fields:
            self.fields.append(field)
            setattr(self, field, kwargs.get(
                field if field != 'status' else 'id', wtypes.Unset))

    @staticmethod
    def _convert_with_links(service, url, expand=True):
        if not expand:
            service.unset_fields_except(
                ['id', 'name', 'host', 'status'])

        service.links = [
            link.Link.make_link('self', url, 'services', str(service.id)),
            link.Link.make_link('bookmark', url, 'services', str(service.id),
                                bookmark=True)]
        return service

    @classmethod
    def convert_with_links(cls, service, expand=True):
        service = Service(**service.as_dict())
        hide_fields_in_newer_versions(service)
        return cls._convert_with_links(
            service, pecan.request.host_url, expand)

    @classmethod
    def sample(cls, expand=True):
        sample = cls(id=1,
                     name='watcher-applier',
                     host='Controller',
                     last_seen_up=datetime.datetime(2016, 1, 1))
        return cls._convert_with_links(sample, 'http://localhost:9322', expand)


class ServiceCollection(collection.Collection):
    """API representation of a collection of services."""

    services = [Service]
    """A list containing services objects"""

    def __init__(self, **kwargs):
        super(ServiceCollection, self).__init__()
        self._type = 'services'

    @staticmethod
    def convert_with_links(services, limit, url=None, expand=False,
                           **kwargs):
        service_collection = ServiceCollection()
        service_collection.services = [
            Service.convert_with_links(g, expand) for g in services]
        service_collection.next = service_collection.get_next(
            limit, url=url, marker_field='id', **kwargs)
        return service_collection

    @classmethod
    def sample(cls):
        sample = cls()
        sample.services = [Service.sample(expand=False)]
        return sample


class ServicesController(rest.RestController):
    """REST controller for Services."""
    def __init__(self):
        super(ServicesController, self).__init__()

    from_services = False
    """A flag to indicate if the requests to this controller are coming
    from the top-level resource Services."""

    _custom_actions = {
        'detail': ['GET'],
    }

    def _get_services_collection(self, marker, limit, sort_key, sort_dir,
                                 expand=False, resource_url=None):
        api_utils.validate_sort_key(
            sort_key, list(objects.Service.fields))
        limit = api_utils.validate_limit(limit)
        api_utils.validate_sort_dir(sort_dir)

        marker_obj = None
        if marker:
            marker_obj = objects.Service.get(
                pecan.request.context, marker)

        sort_db_key = (sort_key if sort_key in objects.Service.fields
                       else None)

        services = objects.Service.list(
            pecan.request.context, limit, marker_obj,
            sort_key=sort_db_key, sort_dir=sort_dir)

        return ServiceCollection.convert_with_links(
            services, limit, url=resource_url, expand=expand,
            sort_key=sort_key, sort_dir=sort_dir)

    @wsme_pecan.wsexpose(ServiceCollection, int, int, wtypes.text, wtypes.text)
    def get_all(self, marker=None, limit=None, sort_key='id', sort_dir='asc'):
        """Retrieve a list of services.

        :param marker: pagination marker for large data sets.
        :param limit: maximum number of resources to return in a single result.
        :param sort_key: column to sort results by. Default: id.
        :param sort_dir: direction to sort. "asc" or "desc". Default: asc.
        """
        context = pecan.request.context
        policy.enforce(context, 'service:get_all',
                       action='service:get_all')

        return self._get_services_collection(marker, limit, sort_key, sort_dir)

    @wsme_pecan.wsexpose(ServiceCollection, int, int, wtypes.text, wtypes.text)
    def detail(self, marker=None, limit=None, sort_key='id', sort_dir='asc'):
        """Retrieve a list of services with detail.

        :param marker: pagination marker for large data sets.
        :param limit: maximum number of resources to return in a single result.
        :param sort_key: column to sort results by. Default: id.
        :param sort_dir: direction to sort. "asc" or "desc". Default: asc.
        """
        context = pecan.request.context
        policy.enforce(context, 'service:detail',
                       action='service:detail')
        # NOTE(lucasagomes): /detail should only work agaist collections
        parent = pecan.request.path.split('/')[:-1][-1]
        if parent != "services":
            raise exception.HTTPNotFound
        expand = True
        resource_url = '/'.join(['services', 'detail'])

        return self._get_services_collection(
            marker, limit, sort_key, sort_dir, expand, resource_url)

    @wsme_pecan.wsexpose(Service, wtypes.text)
    def get_one(self, service):
        """Retrieve information about the given service.

        :param service: ID or name of the service.
        """
        if self.from_services:
            raise exception.OperationNotPermitted

        context = pecan.request.context
        rpc_service = api_utils.get_resource('Service', service)
        policy.enforce(context, 'service:get', rpc_service,
                       action='service:get')

        return Service.convert_with_links(rpc_service)
