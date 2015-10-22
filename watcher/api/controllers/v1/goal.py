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

from oslo_config import cfg

import pecan
from pecan import rest
import wsme
from wsme import types as wtypes
import wsmeext.pecan as wsme_pecan

from watcher.api.controllers import base
from watcher.api.controllers import link
from watcher.api.controllers.v1 import collection
from watcher.api.controllers.v1 import types
from watcher.api.controllers.v1 import utils as api_utils
from watcher.common import exception

CONF = cfg.CONF


class Goal(base.APIBase):
    """API representation of a action.

    This class enforces type checking and value constraints, and converts
    between the internal object model and the API representation of a action.
    """

    name = wtypes.text
    """Name of the goal"""

    strategy = wtypes.text
    """The strategy associated with the goal"""

    uuid = types.uuid
    """Unused field"""

    links = wsme.wsattr([link.Link], readonly=True)
    """A list containing a self link and associated action links"""

    def __init__(self, **kwargs):
        super(Goal, self).__init__()

        self.fields = []
        self.fields.append('name')
        self.fields.append('strategy')
        setattr(self, 'name', kwargs.get('name',
                wtypes.Unset))
        setattr(self, 'strategy', kwargs.get('strategy',
                wtypes.Unset))

    @staticmethod
    def _convert_with_links(goal, url, expand=True):
        if not expand:
            goal.unset_fields_except(['name', 'strategy'])

        goal.links = [link.Link.make_link('self', url,
                                          'goals', goal.name),
                      link.Link.make_link('bookmark', url,
                                          'goals', goal.name,
                                          bookmark=True)]
        return goal

    @classmethod
    def convert_with_links(cls, goal, expand=True):
        goal = Goal(**goal)
        return cls._convert_with_links(goal, pecan.request.host_url, expand)

    @classmethod
    def sample(cls, expand=True):
        sample = cls(name='27e3153e-d5bf-4b7e-b517-fb518e17f34c',
                     strategy='action description')
        return cls._convert_with_links(sample, 'http://localhost:9322', expand)


class GoalCollection(collection.Collection):
    """API representation of a collection of goals."""

    goals = [Goal]
    """A list containing goals objects"""

    def __init__(self, **kwargs):
        self._type = 'goals'

    @staticmethod
    def convert_with_links(goals, limit, url=None, expand=False,
                           **kwargs):

        collection = GoalCollection()
        collection.goals = [Goal.convert_with_links(g, expand) for g in goals]

        if 'sort_key' in kwargs:
            reverse = False
            if kwargs['sort_key'] == 'strategy':
                if 'sort_dir' in kwargs:
                    reverse = True if kwargs['sort_dir'] == 'desc' else False
                collection.goals = sorted(
                    collection.goals,
                    key=lambda goal: goal.name,
                    reverse=reverse)

        collection.next = collection.get_next(limit, url=url, **kwargs)
        return collection

    @classmethod
    def sample(cls):
        sample = cls()
        sample.actions = [Goal.sample(expand=False)]
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

    def _get_goals_collection(self, limit,
                              sort_key, sort_dir, expand=False,
                              resource_url=None, goal_name=None):

        limit = api_utils.validate_limit(limit)
        sort_dir = api_utils.validate_sort_dir(sort_dir)

        goals = []

        if not goal_name and goal_name in CONF.watcher_goals.goals.keys():
            goals.append({'name': goal_name, 'strategy': goals[goal_name]})
        else:
            for name, strategy in CONF.watcher_goals.goals.items():
                goals.append({'name': name, 'strategy': strategy})

        return GoalCollection.convert_with_links(goals[:limit], limit,
                                                 url=resource_url,
                                                 expand=expand,
                                                 sort_key=sort_key,
                                                 sort_dir=sort_dir)

    @wsme_pecan.wsexpose(GoalCollection, int, wtypes.text, wtypes.text)
    def get_all(self, limit=None,
                sort_key='name', sort_dir='asc'):
        """Retrieve a list of goals.

        :param limit: maximum number of resources to return in a single result.
        :param sort_key: column to sort results by. Default: id.
        :param sort_dir: direction to sort. "asc" or "desc". Default: asc.
           to get only actions for that goal.
        """
        return self._get_goals_collection(limit, sort_key, sort_dir)

    @wsme_pecan.wsexpose(GoalCollection, wtypes.text, int,
                         wtypes.text, wtypes.text)
    def detail(self, goal_name=None, limit=None,
               sort_key='name', sort_dir='asc'):
        """Retrieve a list of actions with detail.

        :param goal_name: name of a goal, to get only goals for that
                            action.
        :param limit: maximum number of resources to return in a single result.
        :param sort_key: column to sort results by. Default: id.
        :param sort_dir: direction to sort. "asc" or "desc". Default: asc.
           to get only goals for that goal.
        """
        # NOTE(lucasagomes): /detail should only work agaist collections
        parent = pecan.request.path.split('/')[:-1][-1]
        if parent != "goals":
            raise exception.HTTPNotFound
        expand = True
        resource_url = '/'.join(['goals', 'detail'])
        return self._get_goals_collection(limit, sort_key, sort_dir,
                                          expand, resource_url, goal_name)

    @wsme_pecan.wsexpose(Goal, wtypes.text)
    def get_one(self, goal_name):
        """Retrieve information about the given goal.

        :param goal_name: name of the goal.
        """
        if self.from_goals:
            raise exception.OperationNotPermitted

        goals = CONF.watcher_goals.goals
        goal = {}
        if goal_name in goals.keys():
            goal = {'name': goal_name, 'strategy': goals[goal_name]}

        return Goal.convert_with_links(goal)
