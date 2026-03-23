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

import dataclasses as dc

from http import HTTPStatus

from oslo_config import cfg
from oslo_log import log as logging

from watcher.common import clients


CONF = cfg.CONF
LOG = logging.getLogger(__name__)


@dc.dataclass(frozen=True)
class Inventory:
    """Pure dataclass for placement inventory data.

    Extracted from the Placement API inventory response with all
    attributes resolved at construction time.
    """

    total: int
    reserved: int
    min_unit: int
    max_unit: int
    step_size: int
    allocation_ratio: float

    @classmethod
    def from_placement_api(cls, inventory_dict):
        """Create an Inventory from a Placement API inventory dict.

        :param inventory_dict: dict from Placement API response
        :returns: Inventory dataclass instance
        """
        return cls(
            total=inventory_dict['total'],
            reserved=inventory_dict['reserved'],
            min_unit=inventory_dict['min_unit'],
            max_unit=inventory_dict['max_unit'],
            step_size=inventory_dict['step_size'],
            allocation_ratio=inventory_dict['allocation_ratio'],
        )


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

    def get_inventories(self, rp_uuid: str) -> dict[str, Inventory]:
        """Calls the placement API to get resource inventory information.

        :param rp_uuid: UUID of the resource provider to get.
        :return: A dictionary of Inventory objects keyed by resource
                 classes.
        """
        url = f'/resource_providers/{rp_uuid}/inventories'
        resp = self.get(url)
        if resp.status_code == HTTPStatus.OK:
            json = resp.json()
            return {
                rc: Inventory.from_placement_api(inv)
                for rc, inv in json['inventories'].items()
            }
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
