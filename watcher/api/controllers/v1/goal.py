# -*- encoding: utf-8 -*-
# Copyright 2013 Red Hat, Inc.
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
A :ref:`Goal <goal_definition>` is a human readable, observable and measurable
end result having one objective to be achieved.

Here are some examples of :ref:`Goals <goal_definition>`:

-  minimize the energy consumption
-  minimize the number of compute nodes (consolidation)
-  balance the workload among compute nodes
-  minimize the license cost (some softwares have a licensing model which is
   based on the number of sockets or cores where the software is deployed)
-  find the most appropriate moment for a planned maintenance on a
   given group of host (which may be an entire availability zone):
   power supply replacement, cooling system replacement, hardware
   modification, ...
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


class Goal(base.APIBase):
    """API representation of a goal.

    This class enforces type checking and value constraints, and converts
    between the internal object model and the API representation of a goal.
    """

    uuid = types.uuid
    """Unique UUID for this goal"""

    name = wtypes.text
    """Name of the goal"""

    display_name = wtypes.text
    """Localized name of the goal"""

    efficacy_specification = wtypes.wsattr(types.jsontype, readonly=True)
    """Efficacy specification for this goal"""

    links = wtypes.wsattr([link.Link], readonly=True)
    """A list containing a self link and associated audit template links"""

    def __init__(self, **kwargs):
        self.fields = []
        fields = list(objects.Goal.fields)

        for k in fields:
            # Skip fields we do not expose.
            if not hasattr(self, k):
                continue
            self.fields.append(k)
            setattr(self, k, kwargs.get(k, wtypes.Unset))

    @staticmethod
    def _convert_with_links(goal, url, expand=True):
        if not expand:
            goal.unset_fields_except(['uuid', 'name', 'display_name',
                                      'efficacy_specification'])

        goal.links = [link.Link.make_link('self', url,
                                          'goals', goal.uuid),
                      link.Link.make_link('bookmark', url,
                                          'goals', goal.uuid,
                                          bookmark=True)]
        return goal

    @classmethod
    def convert_with_links(cls, goal, expand=True):
        goal = Goal(**goal.as_dict())
        hide_fields_in_newer_versions(goal)
        return cls._convert_with_links(goal, pecan.request.host_url, expand)

    @classmethod
    def sample(cls, expand=True):
        sample = cls(
            uuid='27e3153e-d5bf-4b7e-b517-fb518e17f34c',
            name='DUMMY',
            display_name='Dummy strategy',
            efficacy_specification=[
                {'description': 'Dummy indicator', 'name': 'dummy',
                 'schema': 'Range(min=0, max=100, min_included=True, '
                           'max_included=True, msg=None)',
                 'unit': '%'}
            ])
        return cls._convert_with_links(sample, 'http://localhost:9322', expand)


class GoalCollection(collection.Collection):
    """API representation of a collection of goals."""

    goals = [Goal]
    """A list containing goals objects"""

    def __init__(self, **kwargs):
        super(GoalCollection, self).__init__()
        self._type = 'goals'

    @staticmethod
    def convert_with_links(goals, limit, url=None, expand=False,
                           **kwargs):
        goal_collection = GoalCollection()
        goal_collection.goals = [
            Goal.convert_with_links(g, expand) for g in goals]
        goal_collection.next = goal_collection.get_next(
            limit, url=url, **kwargs)
        return goal_collection

    @classmethod
    def sample(cls):
        sample = cls()
        sample.goals = [Goal.sample(expand=False)]
        return sample


class GoalsController(rest.RestController):
    """REST controller for Goals."""
    def __init__(self):
        super(GoalsController, self).__init__()

    from_goals = False
    """A flag to indicate if the requests to this controller are coming
    from the top-level resource Goals."""

    _custom_actions = {
        'detail': ['GET'],
    }

    def _get_goals_collection(self, marker, limit, sort_key, sort_dir,
                              expand=False, resource_url=None):
        api_utils.validate_sort_key(
            sort_key, list(objects.Goal.fields))
        limit = api_utils.validate_limit(limit)
        api_utils.validate_sort_dir(sort_dir)

        marker_obj = None
        if marker:
            marker_obj = objects.Goal.get_by_uuid(
                pecan.request.context, marker)

        sort_db_key = (sort_key if sort_key in objects.Goal.fields
                       else None)

        goals = objects.Goal.list(pecan.request.context, limit, marker_obj,
                                  sort_key=sort_db_key, sort_dir=sort_dir)

        return GoalCollection.convert_with_links(goals, limit,
                                                 url=resource_url,
                                                 expand=expand,
                                                 sort_key=sort_key,
                                                 sort_dir=sort_dir)

    @wsme_pecan.wsexpose(GoalCollection, wtypes.text,
                         int, wtypes.text, wtypes.text)
    def get_all(self, marker=None, limit=None, sort_key='id', sort_dir='asc'):
        """Retrieve a list of goals.

        :param marker: pagination marker for large data sets.
        :param limit: maximum number of resources to return in a single result.
        :param sort_key: column to sort results by. Default: id.
        :param sort_dir: direction to sort. "asc" or "desc". Default: asc.
        """
        context = pecan.request.context
        policy.enforce(context, 'goal:get_all',
                       action='goal:get_all')
        return self._get_goals_collection(marker, limit, sort_key, sort_dir)

    @wsme_pecan.wsexpose(GoalCollection, wtypes.text, int,
                         wtypes.text, wtypes.text)
    def detail(self, marker=None, limit=None, sort_key='id', sort_dir='asc'):
        """Retrieve a list of goals with detail.

        :param marker: pagination marker for large data sets.
        :param limit: maximum number of resources to return in a single result.
        :param sort_key: column to sort results by. Default: id.
        :param sort_dir: direction to sort. "asc" or "desc". Default: asc.
        """
        context = pecan.request.context
        policy.enforce(context, 'goal:detail',
                       action='goal:detail')
        # NOTE(lucasagomes): /detail should only work agaist collections
        parent = pecan.request.path.split('/')[:-1][-1]
        if parent != "goals":
            raise exception.HTTPNotFound
        expand = True
        resource_url = '/'.join(['goals', 'detail'])
        return self._get_goals_collection(marker, limit, sort_key, sort_dir,
                                          expand, resource_url)

    @wsme_pecan.wsexpose(Goal, wtypes.text)
    def get_one(self, goal):
        """Retrieve information about the given goal.

        :param goal: UUID or name of the goal.
        """
        if self.from_goals:
            raise exception.OperationNotPermitted

        context = pecan.request.context
        rpc_goal = api_utils.get_resource('Goal', goal)
        policy.enforce(context, 'goal:get', rpc_goal, action='goal:get')

        return Goal.convert_with_links(rpc_goal)
