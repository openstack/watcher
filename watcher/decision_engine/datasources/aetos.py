# Copyright 2025 Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
from observabilityclient.utils import metric_utils as obs_client_utils
from oslo_config import cfg
from oslo_log import log

from watcher.common import clients
from watcher.decision_engine.datasources import prometheus_base

CONF = cfg.CONF
LOG = log.getLogger(__name__)


class AetosHelper(prometheus_base.PrometheusBase):
    """AetosHelper class for retrieving metrics from Aetos

    This class implements the PrometheusBase to allow Watcher to query
    Aetos as a data source for metrics.
    """

    NAME = 'aetos'

    def __init__(self, osc=None):
        """Initialize AetosHelper with optional OpenStackClients instance

        :param osc: OpenStackClients instance for Keystone authentication
        """
        self.osc = osc if osc else clients.OpenStackClients()
        super(AetosHelper, self).__init__()

    def _get_fqdn_label(self):
        """Get the FQDN label from aetos_client config"""
        return CONF.aetos_client.fqdn_label

    def _get_instance_uuid_label(self):
        """Get the instance UUID label from aetos_client config"""
        return CONF.aetos_client.instance_uuid_label

    def _setup_prometheus_client(self):
        """Initialize the prometheus client for Aetos with Keystone auth

        :return: PrometheusAPIClient instance configured for Aetos
        """
        # Get Keystone session from OpenStackClients
        session = self.osc.session

        opts = {'interface': CONF.aetos_client.interface,
                'region_name': CONF.aetos_client.region_name,
                'service_type': 'metric-storage'}

        the_client = obs_client_utils.get_prom_client_from_keystone(
            session, adapter_options=opts
        )

        return the_client
