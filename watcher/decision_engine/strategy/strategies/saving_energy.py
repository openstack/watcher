# -*- encoding: utf-8 -*-
# Copyright (c) 2017 ZTE Corporation
#
# Authors: licanwei <li.canwei2@zte.com.cn>
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

from watcher._i18n import _
from watcher.common import exception
from watcher.common.metal_helper import constants as metal_constants
from watcher.common.metal_helper import factory as metal_helper_factory
from watcher.decision_engine.strategy.strategies import base

LOG = log.getLogger(__name__)


class SavingEnergy(base.SavingEnergyBaseStrategy):
    """Saving Energy Strategy

    *Description*

    Saving Energy Strategy together with VM Workload Consolidation Strategy
    can perform the Dynamic Power Management (DPM) functionality, which tries
    to save power by dynamically consolidating workloads even further during
    periods of low resource utilization. Virtual machines are migrated onto
    fewer hosts and the unneeded  hosts are powered off.

    After consolidation, Saving Energy Strategy produces a solution of powering
    off/on according to the following detailed policy:

    In this policy, a preset number(min_free_hosts_num) is given by user, and
    this min_free_hosts_num describes minimum free compute nodes that users
    expect to have, where "free compute nodes" refers to those nodes unused
    but still powered on.

    If the actual number of unused nodes(in power-on state) is larger than
    the given number, randomly select the redundant nodes and power off them;
    If the actual number of unused nodes(in poweron state) is smaller than
    the given number and there are spare unused nodes(in poweroff state),
    randomly select some nodes(unused,poweroff) and power on them.

    *Requirements*

    In this policy, in order to calculate the min_free_hosts_num,
    users must provide two parameters:

    * One parameter("min_free_hosts_num") is a constant int number.
      This number should be int type and larger than zero.

    * The other parameter("free_used_percent") is a percentage number, which
      describes the quotient of min_free_hosts_num/nodes_with_VMs_num,
      where nodes_with_VMs_num is the number of nodes with VMs running on it.
      This parameter is used to calculate a dynamic min_free_hosts_num.
      The nodes with VMs refer to those nodes with VMs running on it.

    Then choose the larger one as the final min_free_hosts_num.

    *Limitations*

    * at least 2 physical compute hosts

    *Spec URL*

    http://specs.openstack.org/openstack/watcher-specs/specs/pike/implemented/energy-saving-strategy.html
    """

    def __init__(self, config, osc=None):

        super(SavingEnergy, self).__init__(config, osc)
        self._metal_helper = None
        self._nova_client = None

        self.with_vms_node_pool = []
        self.free_poweron_node_pool = []
        self.free_poweroff_node_pool = []
        self.free_used_percent = 0
        self.min_free_hosts_num = 1

    @property
    def metal_helper(self):
        if not self._metal_helper:
            self._metal_helper = metal_helper_factory.get_helper(self.osc)
        return self._metal_helper

    @property
    def nova_client(self):
        if not self._nova_client:
            self._nova_client = self.osc.nova()
        return self._nova_client

    @classmethod
    def get_name(cls):
        return "saving_energy"

    @classmethod
    def get_display_name(cls):
        return _("Saving Energy Strategy")

    @classmethod
    def get_translatable_display_name(cls):
        return "Saving Energy Strategy"

    @classmethod
    def get_schema(cls):
        """return a schema of two input parameters

        The standby nodes refer to those nodes unused
        but still poweredon to deal with boom of new instances.
        """
        return {
            "properties": {
                "free_used_percent": {
                    "description": ("a rational number, which describes the"
                                    " quotient of"
                                    " min_free_hosts_num/nodes_with_VMs_num"
                                    " where nodes_with_VMs_num is the number"
                                    " of nodes with VMs"),
                    "type": "number",
                    "default": 10.0
                },
                "min_free_hosts_num": {
                    "description": ("minimum number of hosts without VMs"
                                    " but still powered on"),
                    "type": "number",
                    "default": 1
                },
            },
        }

    def add_action_poweronoff_node(self, node, state):
        """Add an action for node disability into the solution.

        :param node: node
        :param state: node power state, power on or power off
        :return: None
        """
        params = {'state': state,
                  'resource_name': node.get_hypervisor_hostname()}
        self.solution.add_action(
            action_type='change_node_power_state',
            resource_id=node.get_id(),
            input_parameters=params)

    def get_hosts_pool(self):
        """Get three pools, with_vms_node_pool, free_poweron_node_pool,

        free_poweroff_node_pool.

        """

        node_list = self.metal_helper.list_compute_nodes()
        for node in node_list:
            hypervisor_node = node.get_hypervisor_node().to_dict()

            compute_service = hypervisor_node.get('service', None)
            host_name = compute_service.get('host')
            LOG.debug("Found hypervisor: %s", hypervisor_node)
            try:
                self.compute_model.get_node_by_name(host_name)
            except exception.ComputeNodeNotFound:
                LOG.info("The compute model does not contain the host: %s",
                         host_name)
                continue

            if (node.hv_up_when_powered_off and
                    hypervisor_node.get('state') != 'up'):
                # filter nodes that are not in 'up' state
                LOG.info("Ignoring node that isn't in 'up' state: %s",
                         host_name)
                continue
            else:
                if (hypervisor_node['running_vms'] == 0):
                    power_state = node.get_power_state()
                    if power_state == metal_constants.PowerState.ON:
                        self.free_poweron_node_pool.append(node)
                    elif power_state == metal_constants.PowerState.OFF:
                        self.free_poweroff_node_pool.append(node)
                    else:
                        LOG.info("Ignoring node %s, unknown state: %s",
                                 node, power_state)
                else:
                    self.with_vms_node_pool.append(node)

    def save_energy(self):

        need_poweron = int(max(
            (len(self.with_vms_node_pool) * self.free_used_percent / 100), (
                self.min_free_hosts_num)))
        len_poweron = len(self.free_poweron_node_pool)
        len_poweroff = len(self.free_poweroff_node_pool)
        LOG.debug("need_poweron: %s, len_poweron: %s, len_poweroff: %s",
                  need_poweron, len_poweron, len_poweroff)
        if len_poweron > need_poweron:
            for node in random.sample(self.free_poweron_node_pool,
                                      (len_poweron - need_poweron)):
                self.add_action_poweronoff_node(node,
                                                metal_constants.PowerState.OFF)
                LOG.info("power off %s", node.get_id())
        elif len_poweron < need_poweron:
            diff = need_poweron - len_poweron
            for node in random.sample(self.free_poweroff_node_pool,
                                      min(len_poweroff, diff)):
                self.add_action_poweronoff_node(node,
                                                metal_constants.PowerState.ON)
                LOG.info("power on %s", node.get_id())

    def pre_execute(self):
        self._pre_execute()
        self.free_used_percent = self.input_parameters.free_used_percent
        self.min_free_hosts_num = self.input_parameters.min_free_hosts_num

    def do_execute(self, audit=None):
        """Strategy execution phase

        This phase is where you should put the main logic of your strategy.
        """
        self.get_hosts_pool()
        self.save_energy()

    def post_execute(self):
        """Post-execution phase

        This can be used to compute the global efficacy
        """
        self.solution.model = self.compute_model

        LOG.debug(self.compute_model.to_string())
