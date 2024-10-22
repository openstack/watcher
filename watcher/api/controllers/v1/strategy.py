# -*- encoding: utf-8 -*-
# Copyright (c) 2016 b<>com
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
A :ref:`Strategy <strategy_definition>` is an algorithm implementation which is
able to find a :ref:`Solution <solution_definition>` for a given
:ref:`Goal <goal_definition>`.

There may be several potential strategies which are able to achieve the same
:ref:`Goal <goal_definition>`. This is why it is possible to configure which
specific :ref:`Strategy <strategy_definition>` should be used for each goal.

Some strategies may provide better optimization results but may take more time
to find an optimal :ref:`Solution <solution_definition>`.
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
from watcher.common import utils as common_utils
from watcher.decision_engine import rpcapi
from watcher import objects


def hide_fields_in_newer_versions(obj):
    """This method hides fields that were added in newer API versions.

    Certain node fields were introduced at certain API versions.
    These fields are only made available when the request's API version
    matches or exceeds the versions when these fields were introduced.
    """
    pass


class Strategy(base.APIBase):
    """API representation of a strategy.

    This class enforces type checking and value constraints, and converts
    between the internal object model and the API representation of a strategy.
    """
    _goal_uuid = None
    _goal_name = None

    def _get_goal(self, value):
        if value == wtypes.Unset:
            return None
        goal = None
        try:
            if (common_utils.is_uuid_like(value) or
                    common_utils.is_int_like(value)):
                goal = objects.Goal.get(pecan.request.context, value)
            else:
                goal = objects.Goal.get_by_name(pecan.request.context, value)
        except exception.GoalNotFound:
            pass
        if goal:
            self.goal_id = goal.id
        return goal

    def _get_goal_uuid(self):
        return self._goal_uuid

    def _set_goal_uuid(self, value):
        if value and self._goal_uuid != value:
            self._goal_uuid = None
            goal = self._get_goal(value)
            if goal:
                self._goal_uuid = goal.uuid

    def _get_goal_name(self):
        return self._goal_name

    def _set_goal_name(self, value):
        if value and self._goal_name != value:
            self._goal_name = None
            goal = self._get_goal(value)
            if goal:
                self._goal_name = goal.name

    uuid = types.uuid
    """Unique UUID for this strategy"""

    name = wtypes.text
    """Name of the strategy"""

    display_name = wtypes.text
    """Localized name of the strategy"""

    links = wtypes.wsattr([link.Link], readonly=True)
    """A list containing a self link and associated goal links"""

    goal_uuid = wtypes.wsproperty(wtypes.text, _get_goal_uuid, _set_goal_uuid,
                                  mandatory=True)
    """The UUID of the goal this audit refers to"""

    goal_name = wtypes.wsproperty(wtypes.text, _get_goal_name, _set_goal_name,
                                  mandatory=False)
    """The name of the goal this audit refers to"""

    parameters_spec = {wtypes.text: types.jsontype}
    """Parameters spec dict"""

    def __init__(self, **kwargs):
        super(Strategy, self).__init__()

        self.fields = []
        self.fields.append('uuid')
        self.fields.append('name')
        self.fields.append('display_name')
        self.fields.append('goal_uuid')
        self.fields.append('goal_name')
        self.fields.append('parameters_spec')
        setattr(self, 'uuid', kwargs.get('uuid', wtypes.Unset))
        setattr(self, 'name', kwargs.get('name', wtypes.Unset))
        setattr(self, 'display_name', kwargs.get('display_name', wtypes.Unset))
        setattr(self, 'goal_uuid', kwargs.get('goal_id', wtypes.Unset))
        setattr(self, 'goal_name', kwargs.get('goal_id', wtypes.Unset))
        setattr(self, 'parameters_spec', kwargs.get('parameters_spec',
                wtypes.Unset))

    @staticmethod
    def _convert_with_links(strategy, url, expand=True):
        if not expand:
            strategy.unset_fields_except(
                ['uuid', 'name', 'display_name', 'goal_uuid', 'goal_name'])

        strategy.links = [
            link.Link.make_link('self', url, 'strategies', strategy.uuid),
            link.Link.make_link('bookmark', url, 'strategies', strategy.uuid,
                                bookmark=True)]
        return strategy

    @classmethod
    def convert_with_links(cls, strategy, expand=True):
        strategy = Strategy(**strategy.as_dict())
        hide_fields_in_newer_versions(strategy)
        return cls._convert_with_links(
            strategy, pecan.request.host_url, expand)

    @classmethod
    def sample(cls, expand=True):
        sample = cls(uuid='27e3153e-d5bf-4b7e-b517-fb518e17f34c',
                     name='DUMMY',
                     display_name='Dummy strategy')
        return cls._convert_with_links(sample, 'http://localhost:9322', expand)


class StrategyCollection(collection.Collection):
    """API representation of a collection of strategies."""

    strategies = [Strategy]
    """A list containing strategies objects"""

    def __init__(self, **kwargs):
        super(StrategyCollection, self).__init__()
        self._type = 'strategies'

    @staticmethod
    def convert_with_links(strategies, limit, url=None, expand=False,
                           **kwargs):
        strategy_collection = StrategyCollection()
        strategy_collection.strategies = [
            Strategy.convert_with_links(g, expand) for g in strategies]
        strategy_collection.next = strategy_collection.get_next(
            limit, url=url, **kwargs)
        return strategy_collection

    @classmethod
    def sample(cls):
        sample = cls()
        sample.strategies = [Strategy.sample(expand=False)]
        return sample


class StrategiesController(rest.RestController):
    """REST controller for Strategies."""

    def __init__(self):
        super(StrategiesController, self).__init__()

    from_strategies = False
    """A flag to indicate if the requests to this controller are coming
    from the top-level resource Strategies."""

    _custom_actions = {
        'detail': ['GET'],
        'state': ['GET'],
    }

    def _get_strategies_collection(self, filters, marker, limit, sort_key,
                                   sort_dir, expand=False, resource_url=None):
        additional_fields = ["goal_uuid", "goal_name"]

        api_utils.validate_sort_key(
            sort_key, list(objects.Strategy.fields) + additional_fields)
        api_utils.validate_search_filters(
            filters, list(objects.Strategy.fields) + additional_fields)
        limit = api_utils.validate_limit(limit)
        api_utils.validate_sort_dir(sort_dir)

        marker_obj = None
        if marker:
            marker_obj = objects.Strategy.get_by_uuid(
                pecan.request.context, marker)

        need_api_sort = api_utils.check_need_api_sort(sort_key,
                                                      additional_fields)
        sort_db_key = (sort_key if not need_api_sort
                       else None)

        strategies = objects.Strategy.list(
            pecan.request.context, limit, marker_obj, filters=filters,
            sort_key=sort_db_key, sort_dir=sort_dir)

        strategies_collection = StrategyCollection.convert_with_links(
            strategies, limit, url=resource_url, expand=expand,
            sort_key=sort_key, sort_dir=sort_dir)

        if need_api_sort:
            api_utils.make_api_sort(strategies_collection.strategies,
                                    sort_key, sort_dir)

        return strategies_collection

    @wsme_pecan.wsexpose(StrategyCollection, wtypes.text, wtypes.text,
                         int, wtypes.text, wtypes.text)
    def get_all(self, goal=None, marker=None, limit=None,
                sort_key='id', sort_dir='asc'):
        """Retrieve a list of strategies.

        :param goal: goal UUID or name to filter by.
        :param marker: pagination marker for large data sets.
        :param limit: maximum number of resources to return in a single result.
        :param sort_key: column to sort results by. Default: id.
        :param sort_dir: direction to sort. "asc" or "desc". Default: asc.
        """
        context = pecan.request.context
        policy.enforce(context, 'strategy:get_all',
                       action='strategy:get_all')
        filters = {}
        if goal:
            if common_utils.is_uuid_like(goal):
                filters['goal_uuid'] = goal
            else:
                filters['goal_name'] = goal

        return self._get_strategies_collection(
            filters, marker, limit, sort_key, sort_dir)

    @wsme_pecan.wsexpose(StrategyCollection, wtypes.text, wtypes.text, int,
                         wtypes.text, wtypes.text)
    def detail(self, goal=None, marker=None, limit=None,
               sort_key='id', sort_dir='asc'):
        """Retrieve a list of strategies with detail.

        :param goal: goal UUID or name to filter by.
        :param marker: pagination marker for large data sets.
        :param limit: maximum number of resources to return in a single result.
        :param sort_key: column to sort results by. Default: id.
        :param sort_dir: direction to sort. "asc" or "desc". Default: asc.
        """
        context = pecan.request.context
        policy.enforce(context, 'strategy:detail',
                       action='strategy:detail')
        # NOTE(lucasagomes): /detail should only work against collections
        parent = pecan.request.path.split('/')[:-1][-1]
        if parent != "strategies":
            raise exception.HTTPNotFound
        expand = True
        resource_url = '/'.join(['strategies', 'detail'])

        filters = {}
        if goal:
            if common_utils.is_uuid_like(goal):
                filters['goal_uuid'] = goal
            else:
                filters['goal_name'] = goal

        return self._get_strategies_collection(
            filters, marker, limit, sort_key, sort_dir, expand, resource_url)

    @wsme_pecan.wsexpose(wtypes.text, wtypes.text)
    def state(self, strategy):
        """Retrieve an information about strategy requirements.

        :param strategy: name of the strategy.
        """
        context = pecan.request.context
        policy.enforce(context, 'strategy:state', action='strategy:state')
        parents = pecan.request.path.split('/')[:-1]
        if parents[-2] != "strategies":
            raise exception.HTTPNotFound
        rpc_strategy = api_utils.get_resource('Strategy', strategy)
        de_client = rpcapi.DecisionEngineAPI()
        strategy_state = de_client.get_strategy_info(context,
                                                     rpc_strategy.name)
        strategy_state.extend([{
            'type': 'Name', 'state': rpc_strategy.name,
            'mandatory': '', 'comment': ''}])
        return strategy_state

    @wsme_pecan.wsexpose(Strategy, wtypes.text)
    def get_one(self, strategy):
        """Retrieve information about the given strategy.

        :param strategy: UUID or name of the strategy.
        """
        if self.from_strategies:
            raise exception.OperationNotPermitted

        context = pecan.request.context
        rpc_strategy = api_utils.get_resource('Strategy', strategy)
        policy.enforce(context, 'strategy:get', rpc_strategy,
                       action='strategy:get')

        return Strategy.convert_with_links(rpc_strategy)
