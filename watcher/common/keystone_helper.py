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

from oslo_log import log

from watcher.common import clients


LOG = log.getLogger(__name__)


class KeystoneHelper:
    def __init__(self, osc=None):
        """:param osc: an OpenStackClients instance"""
        self.osc = osc if osc else clients.OpenStackClients()
        self.keystone = self.osc.keystone()

    def is_service_enabled_by_type(self, svc_type):
        services = self.keystone.services.list(type=svc_type)
        svcs_enabled = [svc for svc in services if svc.enabled]
        if len(svcs_enabled) == 0:
            LOG.warning("Service enabled not found for type: %s", svc_type)
            return False
        elif len(svcs_enabled) > 1:
            LOG.warning("Multiple services found for type: %s", svc_type)
            return False
        # if there is only one enabled service, consider it a valid
        # case
        return True
