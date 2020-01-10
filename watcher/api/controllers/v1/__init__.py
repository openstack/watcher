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


"""
Version 1 of the Watcher API

NOTE: IN PROGRESS AND NOT FULLY IMPLEMENTED.
"""

import datetime

import pecan
from pecan import rest
from webob import exc
import wsme
from wsme import types as wtypes
import wsmeext.pecan as wsme_pecan

from watcher.api.controllers import base
from watcher.api.controllers import link
from watcher.api.controllers.v1 import action
from watcher.api.controllers.v1 import action_plan
from watcher.api.controllers.v1 import audit
from watcher.api.controllers.v1 import audit_template
from watcher.api.controllers.v1 import data_model
from watcher.api.controllers.v1 import goal
from watcher.api.controllers.v1 import scoring_engine
from watcher.api.controllers.v1 import service
from watcher.api.controllers.v1 import strategy
from watcher.api.controllers.v1 import utils
from watcher.api.controllers.v1 import versions
from watcher.api.controllers.v1 import webhooks


def min_version():
    return base.Version(
        {base.Version.string: ' '.join([versions.service_type_string(),
                                        versions.min_version_string()])},
        versions.min_version_string(), versions.max_version_string())


def max_version():
    return base.Version(
        {base.Version.string: ' '.join([versions.service_type_string(),
                                        versions.max_version_string()])},
        versions.min_version_string(), versions.max_version_string())


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


class MediaType(APIBase):
    """A media type representation."""

    base = wtypes.text
    type = wtypes.text

    def __init__(self, base, type):
        self.base = base
        self.type = type


class V1(APIBase):
    """The representation of the version 1 of the API."""

    id = wtypes.text
    """The ID of the version, also acts as the release number"""

    media_types = [MediaType]
    """An array of supcontainersed media types for this version"""

    audit_templates = [link.Link]
    """Links to the audit templates resource"""

    audits = [link.Link]
    """Links to the audits resource"""

    data_model = [link.Link]
    """Links to the data model resource"""

    actions = [link.Link]
    """Links to the actions resource"""

    action_plans = [link.Link]
    """Links to the action plans resource"""

    scoring_engines = [link.Link]
    """Links to the Scoring Engines resource"""

    services = [link.Link]
    """Links to the services resource"""

    webhooks = [link.Link]
    """Links to the webhooks resource"""

    links = [link.Link]
    """Links that point to a specific URL for this version and documentation"""

    @staticmethod
    def convert():
        v1 = V1()
        v1.id = "v1"
        base_url = pecan.request.application_url
        v1.links = [link.Link.make_link('self', base_url,
                                        'v1', '', bookmark=True),
                    link.Link.make_link('describedby',
                                        'http://docs.openstack.org',
                                        'developer/watcher/dev',
                                        'api-spec-v1.html',
                                        bookmark=True, type='text/html')
                    ]
        v1.media_types = [MediaType('application/json',
                          'application/vnd.openstack.watcher.v1+json')]
        v1.audit_templates = [link.Link.make_link('self',
                                                  base_url,
                                                  'audit_templates', ''),
                              link.Link.make_link('bookmark',
                                                  base_url,
                                                  'audit_templates', '',
                                                  bookmark=True)
                              ]
        v1.audits = [link.Link.make_link('self', base_url,
                                         'audits', ''),
                     link.Link.make_link('bookmark',
                                         base_url,
                                         'audits', '',
                                         bookmark=True)
                     ]
        if utils.allow_list_datamodel():
            v1.data_model = [link.Link.make_link('self', base_url,
                                                 'data_model', ''),
                             link.Link.make_link('bookmark',
                                                 base_url,
                                                 'data_model', '',
                                                 bookmark=True)
                             ]
        v1.actions = [link.Link.make_link('self', base_url,
                                          'actions', ''),
                      link.Link.make_link('bookmark',
                                          base_url,
                                          'actions', '',
                                          bookmark=True)
                      ]
        v1.action_plans = [link.Link.make_link(
            'self', base_url, 'action_plans', ''),
            link.Link.make_link('bookmark',
                                base_url,
                                'action_plans', '',
                                bookmark=True)
            ]

        v1.scoring_engines = [link.Link.make_link(
            'self', base_url, 'scoring_engines', ''),
            link.Link.make_link('bookmark',
                                base_url,
                                'scoring_engines', '',
                                bookmark=True)
            ]

        v1.services = [link.Link.make_link(
            'self', base_url, 'services', ''),
            link.Link.make_link('bookmark',
                                base_url,
                                'services', '',
                                bookmark=True)
            ]
        if utils.allow_webhook_api():
            v1.webhooks = [link.Link.make_link(
                'self', base_url, 'webhooks', ''),
                link.Link.make_link('bookmark',
                                    base_url,
                                    'webhooks', '',
                                    bookmark=True)
                ]
        return v1


class Controller(rest.RestController):
    """Version 1 API controller root."""

    audits = audit.AuditsController()
    audit_templates = audit_template.AuditTemplatesController()
    actions = action.ActionsController()
    action_plans = action_plan.ActionPlansController()
    goals = goal.GoalsController()
    scoring_engines = scoring_engine.ScoringEngineController()
    services = service.ServicesController()
    strategies = strategy.StrategiesController()
    data_model = data_model.DataModelController()
    webhooks = webhooks.WebhookController()

    @wsme_pecan.wsexpose(V1)
    def get(self):
        # NOTE: The reason why convert() it's being called for every
        #       request is because we need to get the host url from
        #       the request object to make the links.
        return V1.convert()

    def _check_version(self, version, headers=None):
        if headers is None:
            headers = {}
        # ensure that major version in the URL matches the header
        if version.major != versions.BASE_VERSION:
            raise exc.HTTPNotAcceptable(
                "Mutually exclusive versions requested. Version %(ver)s "
                "requested but not supported by this service. The supported "
                "version range is: [%(min)s, %(max)s]." %
                {'ver': version, 'min': versions.min_version_string(),
                 'max': versions.max_version_string()},
                headers=headers)
        # ensure the minor version is within the supported range
        if version < min_version() or version > max_version():
            raise exc.HTTPNotAcceptable(
                "Version %(ver)s was requested but the minor version is not "
                "supported by this service. The supported version range is: "
                "[%(min)s, %(max)s]." %
                {'ver': version, 'min': versions.min_version_string(),
                 'max': versions.max_version_string()},
                headers=headers)

    @pecan.expose()
    def _route(self, args, request=None):
        v = base.Version(pecan.request.headers, versions.min_version_string(),
                         versions.max_version_string())

        # The Vary header is used as a hint to caching proxies and user agents
        # that the response is also dependent on the OpenStack-API-Version and
        # not just the body and query parameters. See RFC 7231 for details.
        pecan.response.headers['Vary'] = base.Version.string

        # Always set the min and max headers
        pecan.response.headers[base.Version.min_string] = (
            versions.min_version_string())
        pecan.response.headers[base.Version.max_string] = (
            versions.max_version_string())

        # assert that requested version is supported
        self._check_version(v, pecan.response.headers)
        pecan.response.headers[base.Version.string] = (
            ' '.join([versions.service_type_string(), str(v)]))
        pecan.request.version = v

        return super(Controller, self)._route(args, request)


__all__ = ("Controller", )
