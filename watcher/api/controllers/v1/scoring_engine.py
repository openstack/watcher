# -*- encoding: utf-8 -*-
# Copyright 2016 Intel
# All Rights Reserved.
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
A :ref:`Scoring Engine <scoring_engine_definition>` is an executable that has
a well-defined input, a well-defined output, and performs a purely mathematical
task. That is, the calculation does not depend on the environment in which it
is running - it would produce the same result anywhere.

Because there might be multiple algorithms used to build a particular data
model (and therefore a scoring engine), the usage of scoring engine might
vary. A metainfo field is supposed to contain any information which might
be needed by the user of a given scoring engine.
"""

import pecan
from pecan import rest
from wsme import types as wtypes
import wsmeext.pecan as wsme_pecan

from watcher.api.controllers import base
from watcher.api.controllers import link
from watcher.api.controllers.v1 import collection
from watcher.api.controllers.v1 import types
from watcher.api.controllers.v1 import utils as api_utils
from watcher.common import exception
from watcher.common import policy
from watcher import objects


def hide_fields_in_newer_versions(obj):
    """This method hides fields that were added in newer API versions.

    Certain node fields were introduced at certain API versions.
    These fields are only made available when the request's API version
    matches or exceeds the versions when these fields were introduced.
    """
    pass


class ScoringEngine(base.APIBase):
    """API representation of a scoring engine.

    This class enforces type checking and value constraints, and converts
    between the internal object model and the API representation of a scoring
    engine.
    """

    uuid = types.uuid
    """Unique UUID of the scoring engine"""

    name = wtypes.text
    """The name of the scoring engine"""

    description = wtypes.text
    """A human readable description of the Scoring Engine"""

    metainfo = wtypes.text
    """A metadata associated with the scoring engine"""

    links = wtypes.wsattr([link.Link], readonly=True)
    """A list containing a self link and associated action links"""

    def __init__(self, **kwargs):
        super(ScoringEngine, self).__init__()

        self.fields = []
        self.fields.append('uuid')
        self.fields.append('name')
        self.fields.append('description')
        self.fields.append('metainfo')
        setattr(self, 'uuid', kwargs.get('uuid', wtypes.Unset))
        setattr(self, 'name', kwargs.get('name', wtypes.Unset))
        setattr(self, 'description', kwargs.get('description', wtypes.Unset))
        setattr(self, 'metainfo', kwargs.get('metainfo', wtypes.Unset))

    @staticmethod
    def _convert_with_links(se, url, expand=True):
        if not expand:
            se.unset_fields_except(
                ['uuid', 'name', 'description'])

        se.links = [link.Link.make_link('self', url,
                                        'scoring_engines', se.uuid),
                    link.Link.make_link('bookmark', url,
                                        'scoring_engines', se.uuid,
                                        bookmark=True)]
        return se

    @classmethod
    def convert_with_links(cls, scoring_engine, expand=True):
        scoring_engine = ScoringEngine(**scoring_engine.as_dict())
        hide_fields_in_newer_versions(scoring_engine)
        return cls._convert_with_links(
            scoring_engine, pecan.request.host_url, expand)

    @classmethod
    def sample(cls, expand=True):
        sample = cls(uuid='81bbd3c7-3b08-4d12-a268-99354dbf7b71',
                     name='sample-se-123',
                     description='Sample Scoring Engine 123 just for testing')
        return cls._convert_with_links(sample, 'http://localhost:9322', expand)


class ScoringEngineCollection(collection.Collection):
    """API representation of a collection of scoring engines."""

    scoring_engines = [ScoringEngine]
    """A list containing scoring engine objects"""

    def __init__(self, **kwargs):
        super(ScoringEngineCollection, self).__init__()
        self._type = 'scoring_engines'

    @staticmethod
    def convert_with_links(scoring_engines, limit, url=None, expand=False,
                           **kwargs):

        collection = ScoringEngineCollection()
        collection.scoring_engines = [ScoringEngine.convert_with_links(
            se, expand) for se in scoring_engines]
        collection.next = collection.get_next(limit, url=url, **kwargs)
        return collection

    @classmethod
    def sample(cls):
        sample = cls()
        sample.scoring_engines = [ScoringEngine.sample(expand=False)]
        return sample


class ScoringEngineController(rest.RestController):
    """REST controller for Scoring Engines."""

    def __init__(self):
        super(ScoringEngineController, self).__init__()

    from_scoring_engines = False
    """A flag to indicate if the requests to this controller are coming
    from the top-level resource Scoring Engines."""

    _custom_actions = {
        'detail': ['GET'],
    }

    def _get_scoring_engines_collection(self, marker, limit,
                                        sort_key, sort_dir, expand=False,
                                        resource_url=None):
        api_utils.validate_sort_key(
            sort_key, list(objects.ScoringEngine.fields))
        limit = api_utils.validate_limit(limit)
        api_utils.validate_sort_dir(sort_dir)

        marker_obj = None
        if marker:
            marker_obj = objects.ScoringEngine.get_by_uuid(
                pecan.request.context, marker)

        filters = {}

        sort_db_key = (sort_key if sort_key in objects.ScoringEngine.fields
                       else None)

        scoring_engines = objects.ScoringEngine.list(
            context=pecan.request.context,
            limit=limit,
            marker=marker_obj,
            sort_key=sort_db_key,
            sort_dir=sort_dir,
            filters=filters)

        return ScoringEngineCollection.convert_with_links(
            scoring_engines,
            limit,
            url=resource_url,
            expand=expand,
            sort_key=sort_key,
            sort_dir=sort_dir)

    @wsme_pecan.wsexpose(ScoringEngineCollection, wtypes.text,
                         int, wtypes.text, wtypes.text)
    def get_all(self, marker=None, limit=None, sort_key='id',
                sort_dir='asc'):
        """Retrieve a list of Scoring Engines.

        :param marker: pagination marker for large data sets.
        :param limit: maximum number of resources to return in a single result.
        :param sort_key: column to sort results by. Default: name.
        :param sort_dir: direction to sort. "asc" or "desc". Default: asc.
        """
        context = pecan.request.context
        policy.enforce(context, 'scoring_engine:get_all',
                       action='scoring_engine:get_all')

        return self._get_scoring_engines_collection(
            marker, limit, sort_key, sort_dir)

    @wsme_pecan.wsexpose(ScoringEngineCollection, wtypes.text,
                         int, wtypes.text, wtypes.text)
    def detail(self, marker=None, limit=None, sort_key='id', sort_dir='asc'):
        """Retrieve a list of Scoring Engines with detail.

        :param marker: pagination marker for large data sets.
        :param limit: maximum number of resources to return in a single result.
        :param sort_key: column to sort results by. Default: name.
        :param sort_dir: direction to sort. "asc" or "desc". Default: asc.
        """
        context = pecan.request.context
        policy.enforce(context, 'scoring_engine:detail',
                       action='scoring_engine:detail')

        parent = pecan.request.path.split('/')[:-1][-1]
        if parent != "scoring_engines":
            raise exception.HTTPNotFound
        expand = True
        resource_url = '/'.join(['scoring_engines', 'detail'])
        return self._get_scoring_engines_collection(
            marker, limit, sort_key, sort_dir, expand, resource_url)

    @wsme_pecan.wsexpose(ScoringEngine, wtypes.text)
    def get_one(self, scoring_engine):
        """Retrieve information about the given Scoring Engine.

        :param scoring_engine_name: The name of the Scoring Engine.
        """
        context = pecan.request.context
        policy.enforce(context, 'scoring_engine:get',
                       action='scoring_engine:get')

        if self.from_scoring_engines:
            raise exception.OperationNotPermitted

        rpc_scoring_engine = api_utils.get_resource(
            'ScoringEngine', scoring_engine)

        return ScoringEngine.convert_with_links(rpc_scoring_engine)
