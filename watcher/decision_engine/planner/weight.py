# -*- encoding: utf-8 -*-
#
# Authors: Vincent Francoise <Vincent.FRANCOISE@b-com.com>
#          Alexander Chadin <a.chadin@servionica.ru>
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import collections

import networkx as nx
from oslo_config import cfg
from oslo_log import log

from watcher.common import utils
from watcher.decision_engine.planner import base
from watcher import objects

LOG = log.getLogger(__name__)


class WeightPlanner(base.BasePlanner):
    """Weight planner implementation

    This implementation builds actions with parents in accordance with weights.
    Set of actions having a higher weight will be scheduled before
    the other ones. There are two config options to configure:
    action_weights and parallelization.

    *Limitations*

    - This planner requires to have action_weights and parallelization configs
      tuned well.
    """

    def __init__(self, config):
        super(WeightPlanner, self).__init__(config)

    action_weights = {
        'nop': 70,
        'volume_migrate': 60,
        'change_nova_service_state': 50,
        'sleep': 40,
        'migrate': 30,
        'resize': 20,
        'turn_host_to_acpi_s3_state': 10,
        'change_node_power_state': 9,
    }

    parallelization = {
        'turn_host_to_acpi_s3_state': 2,
        'resize': 2,
        'migrate': 2,
        'sleep': 1,
        'change_nova_service_state': 1,
        'nop': 1,
        'change_node_power_state': 2,
        'volume_migrate': 2
    }

    @classmethod
    def get_config_opts(cls):
        return [
            cfg.DictOpt(
                'weights',
                help="These weights are used to schedule the actions. "
                     "Action Plan will be build in accordance with sets of "
                     "actions ordered by descending weights."
                     "Two action types cannot have the same weight. ",
                default=cls.action_weights),
            cfg.DictOpt(
                'parallelization',
                help="Number of actions to be run in parallel on a per "
                     "action type basis.",
                default=cls.parallelization),
        ]

    @staticmethod
    def chunkify(lst, n):
        """Yield successive n-sized chunks from lst."""
        n = int(n)
        if n < 1:
            # Just to make sure the number is valid
            n = 1

        # Split a flat list in a list of chunks of size n.
        # e.g. chunkify([0, 1, 2, 3, 4], 2) -> [[0, 1], [2, 3], [4]]
        for i in range(0, len(lst), n):
            yield lst[i:i + n]

    def compute_action_graph(self, sorted_weighted_actions):
        reverse_weights = {v: k for k, v in self.config.weights.items()}
        # leaf_groups contains a list of list of nodes called groups
        # each group is a set of nodes from which a future node will
        # branch off (parent nodes).

        # START --> migrate-1 --> migrate-3
        #     \                            \--> resize-1 --> FINISH
        #      \--> migrate-2 -------------/
        # In the above case migrate-1 will be the only member of the leaf
        # group that migrate-3 will use as parent group, whereas
        # resize-1 will have both migrate-2 and migrate-3 in its
        # parent/leaf group
        leaf_groups = []
        action_graph = nx.DiGraph()
        # We iterate through each action type category (sorted by weight) to
        # insert them in a Directed Acyclic Graph
        for idx, (weight, actions) in enumerate(sorted_weighted_actions):
            action_chunks = self.chunkify(
                actions, self.config.parallelization[reverse_weights[weight]])

            # We split the actions into chunks/layers that will have to be
            # spread across all the available branches of the graph
            for chunk_idx, actions_chunk in enumerate(action_chunks):
                for action in actions_chunk:
                    action_graph.add_node(action)

                    # all other actions
                    parent_nodes = []
                    if not idx and not chunk_idx:
                        parent_nodes = []
                    elif leaf_groups:
                        parent_nodes = leaf_groups

                    for parent_node in parent_nodes:
                        action_graph.add_edge(parent_node, action)
                        action.parents.append(parent_node.uuid)

                if leaf_groups:
                    leaf_groups = []
                leaf_groups.extend([a for a in actions_chunk])

        return action_graph

    def schedule(self, context, audit_id, solution):
        LOG.debug('Creating an action plan for the audit uuid: %s', audit_id)
        action_plan = self.create_action_plan(context, audit_id, solution)

        sorted_weighted_actions = self.get_sorted_actions_by_weight(
            context, action_plan, solution)
        action_graph = self.compute_action_graph(sorted_weighted_actions)

        self._create_efficacy_indicators(
            context, action_plan.id, solution.efficacy_indicators)

        if len(action_graph.nodes()) == 0:
            LOG.warning("The action plan is empty")
            action_plan.state = objects.action_plan.State.SUCCEEDED
            action_plan.save()

        self.create_scheduled_actions(action_graph)
        return action_plan

    def get_sorted_actions_by_weight(self, context, action_plan, solution):
        # We need to make them immutable to add them to the graph
        action_objects = list([
            objects.Action(
                context, uuid=utils.generate_uuid(), parents=[],
                action_plan_id=action_plan.id, **a)
            for a in solution.actions])
        # This is a dict of list with each being a weight and the list being
        # all the actions associated to this weight
        weighted_actions = collections.defaultdict(list)
        for action in action_objects:
            action_weight = self.config.weights[action.action_type]
            weighted_actions[action_weight].append(action)

        return reversed(sorted(weighted_actions.items(), key=lambda x: x[0]))

    def create_scheduled_actions(self, graph):
        for action in graph.nodes():
            LOG.debug("Creating the %s in the Watcher database",
                      action.action_type)
            try:
                action.create()
            except Exception as exc:
                LOG.exception(exc)
                raise

    def create_action_plan(self, context, audit_id, solution):
        strategy = objects.Strategy.get_by_name(
            context, solution.strategy.name)

        action_plan_dict = {
            'uuid': utils.generate_uuid(),
            'audit_id': audit_id,
            'strategy_id': strategy.id,
            'state': objects.action_plan.State.RECOMMENDED,
            'global_efficacy': solution.global_efficacy,
        }

        new_action_plan = objects.ActionPlan(context, **action_plan_dict)
        new_action_plan.create()

        return new_action_plan

    def _create_efficacy_indicators(self, context, action_plan_id, indicators):
        efficacy_indicators = []
        for indicator in indicators:
            efficacy_indicator_dict = {
                'uuid': utils.generate_uuid(),
                'name': indicator.name,
                'description': indicator.description,
                'unit': indicator.unit,
                'value': indicator.value,
                'action_plan_id': action_plan_id,
            }
            new_efficacy_indicator = objects.EfficacyIndicator(
                context, **efficacy_indicator_dict)
            new_efficacy_indicator.create()

            efficacy_indicators.append(new_efficacy_indicator)
        return efficacy_indicators
