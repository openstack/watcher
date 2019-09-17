# -*- encoding: utf-8 -*-
# Copyright (c) 2015 b<>com
#
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

"""
A :ref:`Strategy <strategy_definition>` is an algorithm implementation which is
able to find a :ref:`Solution <solution_definition>` for a given
:ref:`Goal <goal_definition>`.

There may be several potential strategies which are able to achieve the same
:ref:`Goal <goal_definition>`. This is why it is possible to configure which
specific :ref:`Strategy <strategy_definition>` should be used for each
:ref:`Goal <goal_definition>`.

Some strategies may provide better optimization results but may take more time
to find an optimal :ref:`Solution <solution_definition>`.

When a new :ref:`Goal <goal_definition>` is added to the Watcher configuration,
at least one default associated :ref:`Strategy <strategy_definition>` should be
provided as well.

:ref:`Some default implementations are provided <watcher_strategies>`, but it
is possible to :ref:`develop new implementations <implement_strategy_plugin>`
which are dynamically loaded by Watcher at launch time.
"""

import abc
import six

from oslo_config import cfg
from oslo_log import log
from oslo_utils import strutils

from watcher.common import clients
from watcher.common import context
from watcher.common import exception
from watcher.common.loader import loadable
from watcher.common import utils
from watcher.decision_engine.datasources import manager as ds_manager
from watcher.decision_engine.loading import default as loading
from watcher.decision_engine.model.collector import manager
from watcher.decision_engine.solution import default
from watcher.decision_engine.strategy.common import level

LOG = log.getLogger(__name__)
CONF = cfg.CONF


class StrategyEndpoint(object):
    def __init__(self, messaging):
        self._messaging = messaging

    def _collect_metrics(self, strategy, datasource):
        metrics = []
        if not datasource:
            return {'type': 'Metrics', 'state': metrics,
                    'mandatory': False, 'comment': ''}
        else:
            ds_metrics = datasource.list_metrics()
            if ds_metrics is None:
                raise exception.DataSourceNotAvailable(
                    datasource=datasource.NAME)
            else:
                for metric in strategy.DATASOURCE_METRICS:
                    original_metric_name = datasource.METRIC_MAP.get(metric)
                    if original_metric_name in ds_metrics:
                        metrics.append({original_metric_name: 'available'})
                    else:
                        metrics.append({original_metric_name: 'not available'})
        return {'type': 'Metrics', 'state': metrics,
                'mandatory': False, 'comment': ''}

    def _get_datasource_status(self, strategy, datasource):
        if not datasource:
            state = "Datasource is not presented for this strategy"
        else:
            state = "%s: %s" % (datasource.NAME,
                                datasource.check_availability())
        return {'type': 'Datasource',
                'state': state,
                'mandatory': True, 'comment': ''}

    def _get_cdm(self, strategy):
        models = []
        for model in ['compute_model', 'storage_model', 'baremetal_model']:
            try:
                getattr(strategy, model)
            except Exception:
                models.append({model: 'not available'})
            else:
                models.append({model: 'available'})
        return {'type': 'CDM', 'state': models,
                'mandatory': True, 'comment': ''}

    def get_strategy_info(self, context, strategy_name):
        strategy = loading.DefaultStrategyLoader().load(strategy_name)
        try:
            is_datasources = getattr(strategy.config, 'datasources', None)
            if is_datasources:
                datasource = getattr(strategy, 'datasource_backend')
            else:
                datasource = getattr(strategy, strategy.config.datasource)
        except (AttributeError, IndexError):
            datasource = []
        available_datasource = self._get_datasource_status(strategy,
                                                           datasource)
        available_metrics = self._collect_metrics(strategy, datasource)
        available_cdm = self._get_cdm(strategy)
        return [available_datasource, available_metrics, available_cdm]


@six.add_metaclass(abc.ABCMeta)
class BaseStrategy(loadable.Loadable):
    """A base class for all the strategies

    A Strategy is an algorithm implementation which is able to find a
    Solution for a given Goal.
    """

    DATASOURCE_METRICS = []
    """Contains all metrics the strategy requires from a datasource to properly
    execute"""

    MIGRATION = "migrate"

    def __init__(self, config, osc=None):
        """Constructor: the signature should be identical within the subclasses

        :param config: Configuration related to this plugin
        :type config: :py:class:`~.Struct`
        :param osc: An OpenStackClients instance
        :type osc: :py:class:`~.OpenStackClients` instance
        """
        super(BaseStrategy, self).__init__(config)
        self.ctx = context.make_context()
        self._name = self.get_name()
        self._display_name = self.get_display_name()
        self._goal = self.get_goal()
        # default strategy level
        self._strategy_level = level.StrategyLevel.conservative
        self._cluster_state_collector = None
        # the solution given by the strategy
        self._solution = default.DefaultSolution(goal=self.goal, strategy=self)
        self._osc = osc
        self._collector_manager = None
        self._compute_model = None
        self._storage_model = None
        self._baremetal_model = None
        self._input_parameters = utils.Struct()
        self._audit_scope = None
        self._datasource_backend = None
        self._planner = 'weight'

    @classmethod
    @abc.abstractmethod
    def get_name(cls):
        """The name of the strategy"""
        raise NotImplementedError()

    @classmethod
    @abc.abstractmethod
    def get_display_name(cls):
        """The goal display name for the strategy"""
        raise NotImplementedError()

    @classmethod
    @abc.abstractmethod
    def get_translatable_display_name(cls):
        """The translatable msgid of the strategy"""
        # Note(v-francoise): Defined here to be used as the translation key for
        # other services
        raise NotImplementedError()

    @classmethod
    @abc.abstractmethod
    def get_goal_name(cls):
        """The goal name the strategy achieves"""
        raise NotImplementedError()

    @classmethod
    def get_goal(cls):
        """The goal the strategy achieves"""
        goal_loader = loading.DefaultGoalLoader()
        return goal_loader.load(cls.get_goal_name())

    @classmethod
    def get_config_opts(cls):
        """Defines the configuration options to be associated to this loadable

        :return: A list of configuration options relative to this Loadable
        :rtype: list of :class:`oslo_config.cfg.Opt` instances
        """

        datasources_ops = list(ds_manager.DataSourceManager.metric_map.keys())

        return [
            cfg.ListOpt(
                "datasources",
                help="Datasources to use in order to query the needed metrics."
                     " This option overrides the global preference."
                     " options: {0}".format(datasources_ops),
                item_type=cfg.types.String(choices=datasources_ops),
                default=None)
        ]

    @abc.abstractmethod
    def pre_execute(self):
        """Pre-execution phase

        This can be used to fetch some pre-requisites or data.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def do_execute(self, audit=None):
        """Strategy execution phase

        :param audit: An Audit instance
        :type audit: :py:class:`~.Audit` instance

        This phase is where you should put the main logic of your strategy.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def post_execute(self):
        """Post-execution phase

        This can be used to compute the global efficacy
        """
        raise NotImplementedError()

    def _pre_execute(self):
        """Base Pre-execution phase

         This will perform basic pre execution operations most strategies
         should perform.
        """

        LOG.info("Initializing " + self.get_display_name())

        if not self.compute_model:
            raise exception.ClusterStateNotDefined()

        if self.compute_model.stale:
            raise exception.ClusterStateStale()

        LOG.debug(self.compute_model.to_string())

    def execute(self, audit=None):
        """Execute a strategy

        :param audit: An Audit instance
        :type audit: :py:class:`~.Audit` instance
        :return: A computed solution (via a placement algorithm)
        :rtype: :py:class:`~.BaseSolution` instance
        """
        self.pre_execute()
        self.do_execute(audit=audit)
        self.post_execute()

        self.solution.compute_global_efficacy()

        return self.solution

    @property
    def collector_manager(self):
        if self._collector_manager is None:
            self._collector_manager = manager.CollectorManager()
        return self._collector_manager

    @property
    def compute_model(self):
        """Cluster data model

        :returns: Cluster data model the strategy is executed on
        :rtype model: :py:class:`~.ModelRoot` instance
        """
        if self._compute_model is None:
            collector = self.collector_manager.get_cluster_model_collector(
                'compute', osc=self.osc)
            audit_scope_handler = collector.get_audit_scope_handler(
                audit_scope=self.audit_scope)
            self._compute_model = audit_scope_handler.get_scoped_model(
                collector.get_latest_cluster_data_model())

        if not self._compute_model:
            raise exception.ClusterStateNotDefined()

        if self._compute_model.stale:
            raise exception.ClusterStateStale()

        return self._compute_model

    @property
    def storage_model(self):
        """Cluster data model

        :returns: Cluster data model the strategy is executed on
        :rtype model: :py:class:`~.ModelRoot` instance
        """
        if self._storage_model is None:
            collector = self.collector_manager.get_cluster_model_collector(
                'storage', osc=self.osc)
            audit_scope_handler = collector.get_audit_scope_handler(
                audit_scope=self.audit_scope)
            self._storage_model = audit_scope_handler.get_scoped_model(
                collector.get_latest_cluster_data_model())

        if not self._storage_model:
            raise exception.ClusterStateNotDefined()

        if self._storage_model.stale:
            raise exception.ClusterStateStale()

        return self._storage_model

    @property
    def baremetal_model(self):
        """Cluster data model

        :returns: Cluster data model the strategy is executed on
        :rtype model: :py:class:`~.ModelRoot` instance
        """
        if self._baremetal_model is None:
            collector = self.collector_manager.get_cluster_model_collector(
                'baremetal', osc=self.osc)
            audit_scope_handler = collector.get_audit_scope_handler(
                audit_scope=self.audit_scope)
            self._baremetal_model = audit_scope_handler.get_scoped_model(
                collector.get_latest_cluster_data_model())

        if not self._baremetal_model:
            raise exception.ClusterStateNotDefined()

        if self._baremetal_model.stale:
            raise exception.ClusterStateStale()

        return self._baremetal_model

    @classmethod
    def get_schema(cls):
        """Defines a Schema that the input parameters shall comply to

        :return: A jsonschema format (mandatory default setting)
        :rtype: dict
        """
        return {}

    @property
    def datasource_backend(self):
        if not self._datasource_backend:

            # Load the global preferred datasources order but override it
            # if the strategy has a specific datasources config
            datasources = CONF.watcher_datasources
            if self.config.datasources:
                datasources = self.config

            self._datasource_backend = ds_manager.DataSourceManager(
                config=datasources,
                osc=self.osc
            ).get_backend(self.DATASOURCE_METRICS)
        return self._datasource_backend

    @property
    def input_parameters(self):
        return self._input_parameters

    @input_parameters.setter
    def input_parameters(self, p):
        self._input_parameters = p

    @property
    def osc(self):
        if not self._osc:
            self._osc = clients.OpenStackClients()
        return self._osc

    @property
    def solution(self):
        return self._solution

    @solution.setter
    def solution(self, s):
        self._solution = s

    @property
    def audit_scope(self):
        return self._audit_scope

    @audit_scope.setter
    def audit_scope(self, s):
        self._audit_scope = s

    @property
    def name(self):
        return self._name

    @property
    def display_name(self):
        return self._display_name

    @property
    def goal(self):
        return self._goal

    @property
    def strategy_level(self):
        return self._strategy_level

    @strategy_level.setter
    def strategy_level(self, s):
        self._strategy_level = s

    @property
    def state_collector(self):
        return self._cluster_state_collector

    @state_collector.setter
    def state_collector(self, s):
        self._cluster_state_collector = s

    @property
    def planner(self):
        return self._planner

    @planner.setter
    def planner(self, s):
        self._planner = s

    def filter_instances_by_audit_tag(self, instances):
        if not self.config.check_optimize_metadata:
            return instances
        instances_to_migrate = []
        for instance in instances:
            optimize = True
            if instance.metadata:
                try:
                    optimize = strutils.bool_from_string(
                        instance.metadata.get('optimize'))
                except ValueError:
                    optimize = False
            if optimize:
                instances_to_migrate.append(instance)
        return instances_to_migrate

    def add_action_migrate(self,
                           instance,
                           migration_type,
                           source_node,
                           destination_node):
        parameters = {'migration_type': migration_type,
                      'source_node': source_node.hostname,
                      'destination_node': destination_node.hostname,
                      'resource_name': instance.name}
        self.solution.add_action(action_type=self.MIGRATION,
                                 resource_id=instance.uuid,
                                 input_parameters=parameters)


@six.add_metaclass(abc.ABCMeta)
class DummyBaseStrategy(BaseStrategy):

    @classmethod
    def get_goal_name(cls):
        return "dummy"

    @classmethod
    def get_config_opts(cls):
        """Override base class config options as do not use datasource """

        return []


@six.add_metaclass(abc.ABCMeta)
class UnclassifiedStrategy(BaseStrategy):
    """This base class is used to ease the development of new strategies

    The goal defined within this strategy can be used to simplify the
    documentation explaining how to implement a new strategy plugin by
    omitting the need for the strategy developer to define a goal straight
    away.
    """

    @classmethod
    def get_goal_name(cls):
        return "unclassified"


@six.add_metaclass(abc.ABCMeta)
class ServerConsolidationBaseStrategy(BaseStrategy):

    REASON_FOR_DISABLE = 'watcher_disabled'

    @classmethod
    def get_goal_name(cls):
        return "server_consolidation"


@six.add_metaclass(abc.ABCMeta)
class ThermalOptimizationBaseStrategy(BaseStrategy):

    @classmethod
    def get_goal_name(cls):
        return "thermal_optimization"


@six.add_metaclass(abc.ABCMeta)
class WorkloadStabilizationBaseStrategy(BaseStrategy):

    def __init__(self, *args, **kwargs):
        super(WorkloadStabilizationBaseStrategy, self
              ).__init__(*args, **kwargs)
        self._planner = 'workload_stabilization'

    @classmethod
    def get_goal_name(cls):
        return "workload_balancing"


@six.add_metaclass(abc.ABCMeta)
class NoisyNeighborBaseStrategy(BaseStrategy):

    @classmethod
    def get_goal_name(cls):
        return "noisy_neighbor"


@six.add_metaclass(abc.ABCMeta)
class SavingEnergyBaseStrategy(BaseStrategy):

    @classmethod
    def get_goal_name(cls):
        return "saving_energy"

    @classmethod
    def get_config_opts(cls):
        """Override base class config options as do not use datasource """

        return []


@six.add_metaclass(abc.ABCMeta)
class ZoneMigrationBaseStrategy(BaseStrategy):

    @classmethod
    def get_goal_name(cls):
        return "hardware_maintenance"

    @classmethod
    def get_config_opts(cls):
        """Override base class config options as do not use datasource """

        return []


@six.add_metaclass(abc.ABCMeta)
class HostMaintenanceBaseStrategy(BaseStrategy):

    REASON_FOR_MAINTAINING = 'watcher_maintaining'

    @classmethod
    def get_goal_name(cls):
        return "cluster_maintaining"

    @classmethod
    def get_config_opts(cls):
        """Override base class config options as do not use datasource """

        return []
