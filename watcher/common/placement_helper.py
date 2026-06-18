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

from http import HTTPStatus

from oslo_config import cfg
from oslo_log import log as logging

from watcher.common import clients


CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class PlacementHelper:
    def __init__(self, osc=None):
        """:param osc: an OpenStackClients instance"""
        self.osc = osc if osc else clients.OpenStackClients()
        self._placement = self.osc.placement()

    def get(self, url):
        return self._placement.get(url, raise_exc=False)

    @staticmethod
    def get_error_msg(resp):
        json_resp = resp.json()
        # https://docs.openstack.org/api-ref/placement/#errors
        if 'errors' in json_resp:
            error_msg = json_resp['errors'][0].get('detail')
        else:
            error_msg = resp.text

        return error_msg

    def get_inventories(self, rp_uuid):
        """Calls the placement API to get resource inventory information.

        :param rp_uuid: UUID of the resource provider to get.
        :return: A dictionary of inventories keyed by resource classes.
        """
        url = f'/resource_providers/{rp_uuid}/inventories'
        resp = self.get(url)
        if resp.status_code == HTTPStatus.OK:
            json = resp.json()
            return json['inventories']
        msg = (
            "Failed to get resource provider %(rp_uuid)s inventories. "
            "Got %(status_code)d: %(err_text)s."
        )
        args = {
            'rp_uuid': rp_uuid,
            'status_code': resp.status_code,
            'err_text': self.get_error_msg(resp),
        }
        LOG.error(msg, args)
