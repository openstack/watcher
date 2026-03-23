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

from openstack import exceptions as sdk_exc
from oslo_log import log as logging

from watcher.common.base_helper import BaseConnectionMixin


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
    def from_openstacksdk(cls, inventory):
        """Create an Inventory from an OpenStackSDK inventory.

        :param inventory: openstack.placement.Inventory
        :returns: Inventory dataclass instance
        """
        return cls(
            total=inventory.total,
            reserved=inventory.reserved,
            min_unit=inventory.min_unit,
            max_unit=inventory.max_unit,
            step_size=inventory.step_size,
            allocation_ratio=inventory.allocation_ratio,
        )


class PlacementHelper(BaseConnectionMixin):
    def __init__(self, session=None, context=None):
        """Create and return a helper to call the placement service

        :param session: Optional keystone session to create the openstack
        connection.
        :param context: Optional context object, use to get user's token to
        create openstack connection.
        """
        self._create_sdk_connection(
            'placement', context=context, session=session
        )

    def get_inventories(self, rp_uuid: str) -> dict[str, Inventory] | None:
        """Calls the placement API to get resource inventory information.

        :param rp_uuid: UUID of the resource provider to get.
        :return: A dictionary of Inventory objects keyed by resource
                 classes or None if the provider could not be fetched.
        """
        try:
            invs = self.connection.placement.resource_provider_inventories(
                rp_uuid
            )
            return {
                inv.resource_class: Inventory.from_openstacksdk(inv)
                for inv in invs
            }
        except sdk_exc.SDKException as exc:
            LOG.exception(exc)
            return None
