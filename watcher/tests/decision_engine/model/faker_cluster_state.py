# -*- encoding: utf-8 -*-
# Copyright (c) 2015 b<>com
#
# Authors: Jean-Emile DARTOIS <jean-emile.dartois@b-com.com>
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

import os

import mock

from watcher.common import utils
from watcher.decision_engine.model.collector import base
from watcher.decision_engine.model import element
from watcher.decision_engine.model import model_root as modelroot


class FakerModelCollector(base.BaseClusterDataModelCollector):

    def __init__(self, config=None, osc=None, audit_scope=None):
        if config is None:
            config = mock.Mock(period=777)
        super(FakerModelCollector, self).__init__(config)

    @property
    def notification_endpoints(self):
        return []

    def load_data(self, filename):
        cwd = os.path.abspath(os.path.dirname(__file__))
        data_folder = os.path.join(cwd, "data")

        with open(os.path.join(data_folder, filename), 'rb') as xml_file:
            xml_data = xml_file.read()

        return xml_data

    def load_model(self, filename):
        return modelroot.ModelRoot.from_xml(self.load_data(filename))

    def get_audit_scope_handler(self, audit_scope):
        return None

    def execute(self):
        return self._cluster_data_model or self.build_scenario_1()

    def build_scenario_1(self):
        instances = []

        model = modelroot.ModelRoot()
        # number of nodes
        node_count = 5
        # number max of instance per node
        node_instance_count = 7
        # total number of virtual machine
        instance_count = (node_count * node_instance_count)

        for id_ in range(0, node_count):
            node_uuid = "Node_{0}".format(id_)
            hostname = "hostname_{0}".format(id_)
            node_attributes = {
                "id": id_,
                "uuid": node_uuid,
                "hostname": hostname,
                "memory": 132,
                "disk": 250,
                "disk_capacity": 250,
                "vcpus": 40,
            }
            node = element.ComputeNode(**node_attributes)
            model.add_node(node)

        for i in range(0, instance_count):
            instance_uuid = "INSTANCE_{0}".format(i)
            project_id = "project_{0}".format(i)
            instance_attributes = {
                "uuid": instance_uuid,
                "memory": 2,
                "disk": 20,
                "disk_capacity": 20,
                "vcpus": 10,
                "metadata":
                    '{"optimize": true,"top": "floor","nested": {"x": "y"}}',
                "project_id": project_id
            }

            instance = element.Instance(**instance_attributes)
            instances.append(instance)
            model.add_instance(instance)

        mappings = [
            ("INSTANCE_0", "Node_0"),
            ("INSTANCE_1", "Node_0"),
            ("INSTANCE_2", "Node_1"),
            ("INSTANCE_3", "Node_2"),
            ("INSTANCE_4", "Node_2"),
            ("INSTANCE_5", "Node_2"),
            ("INSTANCE_6", "Node_3"),
            ("INSTANCE_7", "Node_4"),
        ]
        for instance_uuid, node_uuid in mappings:
            model.map_instance(
                model.get_instance_by_uuid(instance_uuid),
                model.get_node_by_uuid(node_uuid),
            )

        return model

    def generate_scenario_1(self):
        return self.load_model('scenario_1.xml')

    def generate_scenario_1_with_1_node_unavailable(self):
        return self.load_model('scenario_1_with_1_node_unavailable.xml')

    def generate_scenario_1_with_all_instances_exclude(self):
        return self.load_model('scenario_1_with_all_instances_exclude.xml')

    def generate_scenario_3_with_2_nodes(self):
        return self.load_model('scenario_3_with_2_nodes.xml')

    def generate_scenario_4_with_1_node_no_instance(self):
        return self.load_model('scenario_4_with_1_node_no_instance.xml')

    def generate_scenario_5_with_instance_disk_0(self):
        return self.load_model('scenario_5_with_instance_disk_0.xml')

    def generate_scenario_6_with_2_nodes(self):
        return self.load_model('scenario_6_with_2_nodes.xml')

    def generate_scenario_7_with_2_nodes(self):
        return self.load_model('scenario_7_with_2_nodes.xml')

    def generate_scenario_8_with_4_nodes(self):
        return self.load_model('scenario_8_with_4_nodes.xml')

    def generate_scenario_9_with_3_active_plus_1_disabled_nodes(self):
        return self.load_model(
            'scenario_9_with_3_active_plus_1_disabled_nodes.xml')


class FakerStorageModelCollector(base.BaseClusterDataModelCollector):

    def __init__(self, config=None, osc=None, audit_scope=None):
        if config is None:
            config = mock.Mock(period=777)
        super(FakerStorageModelCollector, self).__init__(config)

    @property
    def notification_endpoints(self):
        return []

    def load_data(self, filename):
        cwd = os.path.abspath(os.path.dirname(__file__))
        data_folder = os.path.join(cwd, "data")

        with open(os.path.join(data_folder, filename), 'rb') as xml_file:
            xml_data = xml_file.read()

        return xml_data

    def load_model(self, filename):
        return modelroot.StorageModelRoot.from_xml(self.load_data(filename))

    def get_audit_scope_handler(self, audit_scope):
        return None

    def execute(self):
        return self._cluster_data_model or self.build_scenario_1()

    def build_scenario_1(self):

        model = modelroot.StorageModelRoot()
        # number of nodes
        node_count = 2
        # number of pools per node
        pool_count = 2
        # number of volumes
        volume_count = 9

        for i in range(0, node_count):
            host = "host_{0}@backend_{0}".format(i)
            zone = "zone_{0}".format(i)
            volume_type = ["type_{0}".format(i)]
            node_attributes = {
                "host": host,
                "zone": zone,
                "status": 'enabled',
                "state": 'up',
                "volume_type": volume_type,
            }
            node = element.StorageNode(**node_attributes)
            model.add_node(node)

            for j in range(0, pool_count):
                name = "host_{0}@backend_{0}#pool_{1}".format(i, j)
                pool_attributes = {
                    "name": name,
                    "total_volumes": 2,
                    "total_capacity_gb": 500,
                    "free_capacity_gb": 420,
                    "provisioned_capacity_gb": 80,
                    "allocated_capacity_gb": 80,
                    "virtual_free": 420,
                }
                pool = element.Pool(**pool_attributes)
                model.add_pool(pool)

        mappings = [
            ("host_0@backend_0#pool_0", "host_0@backend_0"),
            ("host_0@backend_0#pool_1", "host_0@backend_0"),
            ("host_1@backend_1#pool_0", "host_1@backend_1"),
            ("host_1@backend_1#pool_1", "host_1@backend_1"),
        ]

        for pool_name, node_name in mappings:
            model.map_pool(
                model.get_pool_by_pool_name(pool_name),
                model.get_node_by_name(node_name),
            )

        for k in range(volume_count):
            uuid = "VOLUME_{0}".format(k)
            name = "name_{0}".format(k)
            project_id = "project_{0}".format(k)
            volume_attributes = {
                "size": 40,
                "status": "in-use",
                "uuid": uuid,
                "attachments":
                    '[{"server_id": "server","attachment_id": "attachment"}]',
                "name": name,
                "multiattach": 'True',
                "snapshot_id": uuid,
                "project_id": project_id,
                "metadata": '{"readonly": false,"attached_mode": "rw"}',
                "bootable": 'False'
            }
            volume = element.Volume(**volume_attributes)
            model.add_volume(volume)

        mappings = [
            ("VOLUME_0", "host_0@backend_0#pool_0"),
            ("VOLUME_1", "host_0@backend_0#pool_0"),
            ("VOLUME_2", "host_0@backend_0#pool_1"),
            ("VOLUME_3", "host_0@backend_0#pool_1"),
            ("VOLUME_4", "host_1@backend_1#pool_0"),
            ("VOLUME_5", "host_1@backend_1#pool_0"),
            ("VOLUME_6", "host_1@backend_1#pool_1"),
            ("VOLUME_7", "host_1@backend_1#pool_1"),
        ]

        for volume_uuid, pool_name in mappings:
            model.map_volume(
                model.get_volume_by_uuid(volume_uuid),
                model.get_pool_by_pool_name(pool_name),
            )

        return model

    def generate_scenario_1(self):
        return self.load_model('storage_scenario_1.xml')


class FakerBaremetalModelCollector(base.BaseClusterDataModelCollector):

    def __init__(self, config=None, osc=None):
        if config is None:
            config = mock.Mock(period=777)
        super(FakerBaremetalModelCollector, self).__init__(config)

    @property
    def notification_endpoints(self):
        return []

    def get_audit_scope_handler(self, audit_scope):
        return None

    def load_data(self, filename):
        cwd = os.path.abspath(os.path.dirname(__file__))
        data_folder = os.path.join(cwd, "data")

        with open(os.path.join(data_folder, filename), 'rb') as xml_file:
            xml_data = xml_file.read()

        return xml_data

    def load_model(self, filename):
        return modelroot.BaremetalModelRoot.from_xml(self.load_data(filename))

    def execute(self):
        return self._cluster_data_model or self.build_scenario_1()

    def build_scenario_1(self):
        model = modelroot.BaremetalModelRoot()
        # number of nodes
        node_count = 2

        for i in range(0, node_count):
            uuid = utils.generate_uuid()
            node_attributes = {
                "uuid": uuid,
                "power_state": "power on",
                "maintenance": "false",
                "maintenance_reason": "null",
                "extra": {"compute_node_id": i}
            }
            node = element.IronicNode(**node_attributes)
            model.add_node(node)

        return model

    def generate_scenario_1(self):
        return self.load_model('ironic_scenario_1.xml')
