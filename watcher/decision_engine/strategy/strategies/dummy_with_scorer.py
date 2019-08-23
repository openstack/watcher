# -*- encoding: utf-8 -*-
# Copyright (c) 2016 Intel
#
# Authors: Tomasz Kaczynski <tomasz.kaczynski@intel.com>
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
#

import random

from oslo_log import log
from oslo_serialization import jsonutils
from oslo_utils import units

from watcher._i18n import _
from watcher.decision_engine.scoring import scoring_factory
from watcher.decision_engine.strategy.strategies import base

LOG = log.getLogger(__name__)


class DummyWithScorer(base.DummyBaseStrategy):
    """A dummy strategy using dummy scoring engines.

    This is a dummy strategy demonstrating how to work with scoring
    engines. One scoring engine is predicting the workload type of a machine
    based on the telemetry data, the other one is simply calculating the
    average value for given elements in a list. Results are then passed to the
    NOP action.

    The strategy is presenting the whole workflow:
    - Get a reference to a scoring engine
    - Prepare input data (features) for score calculation
    - Perform score calculation
    - Use scorer's metadata for results interpretation
    """

    DEFAULT_NAME = "dummy_with_scorer"
    DEFAULT_DESCRIPTION = "Dummy Strategy with Scorer"

    NOP = "nop"
    SLEEP = "sleep"

    def __init__(self, config, osc=None):
        """Constructor: the signature should be identical within the subclasses

        :param config: Configuration related to this plugin
        :type config: :py:class:`~.Struct`
        :param osc: An OpenStackClients instance
        :type osc: :py:class:`~.OpenStackClients` instance
        """

        super(DummyWithScorer, self).__init__(config, osc)

        # Setup Scoring Engines
        self._workload_scorer = (scoring_factory
                                 .get_scoring_engine('dummy_scorer'))
        self._avg_scorer = (scoring_factory
                            .get_scoring_engine('dummy_avg_scorer'))

        # Get metainfo from Workload Scorer for result interpretation
        metainfo = jsonutils.loads(self._workload_scorer.get_metainfo())
        self._workloads = {index: workload
                           for index, workload in enumerate(
                               metainfo['workloads'])}

    def pre_execute(self):
        self._pre_execute()

    def do_execute(self, audit=None):
        # Simple "hello world" from strategy
        param1 = self.input_parameters.param1
        param2 = self.input_parameters.param2
        LOG.debug('DummyWithScorer params: param1=%(p1)f, param2=%(p2)s',
                  {'p1': param1, 'p2': param2})
        parameters = {'message': 'Hello from Dummy Strategy with Scorer!'}
        self.solution.add_action(action_type=self.NOP,
                                 input_parameters=parameters)

        # Demonstrate workload scorer
        features = self._generate_random_telemetry()
        result_str = self._workload_scorer.calculate_score(features)
        LOG.debug('Workload Scorer result: %s', result_str)

        # Parse the result using workloads from scorer's metainfo
        result = self._workloads[jsonutils.loads(result_str)[0]]
        LOG.debug('Detected Workload: %s', result)
        parameters = {'message': 'Detected Workload: %s' % result}
        self.solution.add_action(action_type=self.NOP,
                                 input_parameters=parameters)

        # Demonstrate AVG scorer
        features = jsonutils.dumps(random.sample(range(1000), 20))
        result_str = self._avg_scorer.calculate_score(features)
        LOG.debug('AVG Scorer result: %s', result_str)
        result = jsonutils.loads(result_str)[0]
        LOG.debug('AVG Scorer result (parsed): %d', result)
        parameters = {'message': 'AVG Scorer result: %s' % result}
        self.solution.add_action(action_type=self.NOP,
                                 input_parameters=parameters)

        # Sleep action
        self.solution.add_action(action_type=self.SLEEP,
                                 input_parameters={'duration': 5.0})

    def post_execute(self):
        pass

    @classmethod
    def get_name(cls):
        return 'dummy_with_scorer'

    @classmethod
    def get_display_name(cls):
        return _('Dummy Strategy using sample Scoring Engines')

    @classmethod
    def get_translatable_display_name(cls):
        return 'Dummy Strategy using sample Scoring Engines'

    @classmethod
    def get_schema(cls):
        # Mandatory default setting for each element
        return {
            'properties': {
                'param1': {
                    'description': 'number parameter example',
                    'type': 'number',
                    'default': 3.2,
                    'minimum': 1.0,
                    'maximum': 10.2,
                },
                'param2': {
                    'description': 'string parameter example',
                    'type': "string",
                    'default': "hello"
                },
            },
        }

    def _generate_random_telemetry(self):
        processor_time = random.randint(0, 100)
        mem_total_bytes = 4*units.Gi
        mem_avail_bytes = random.randint(1*units.Gi, 4*units.Gi)
        mem_page_reads = random.randint(0, 2000)
        mem_page_writes = random.randint(0, 2000)
        disk_read_bytes = random.randint(0*units.Mi, 200*units.Mi)
        disk_write_bytes = random.randint(0*units.Mi, 200*units.Mi)
        net_bytes_received = random.randint(0*units.Mi, 20*units.Mi)
        net_bytes_sent = random.randint(0*units.Mi, 10*units.Mi)

        return jsonutils.dumps([
            processor_time, mem_total_bytes, mem_avail_bytes,
            mem_page_reads, mem_page_writes, disk_read_bytes,
            disk_write_bytes, net_bytes_received, net_bytes_sent])
