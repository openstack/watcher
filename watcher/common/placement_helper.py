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

from oslo_config import cfg
from oslo_log import log as logging

from watcher.common import clients

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class PlacementHelper(object):

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

    def get_resource_providers(self, rp_name=None):
        """Calls the placement API for a resource provider record.

        :param rp_name: Name of the resource provider, if None,
                 list all resource providers.
        :return: A list of resource providers information
                 or None if the resource provider doesn't exist.
        """
        url = '/resource_providers'
        if rp_name:
            url += '?name=%s' % rp_name
        resp = self.get(url)
        if resp.status_code == 200:
            json_resp = resp.json()
            return json_resp['resource_providers']

        if rp_name:
            msg = "Failed to get resource provider %(name)s. "
        else:
            msg = "Failed to get all resource providers. "
        msg += "Got %(status_code)d: %(err_text)s."
        args = {
            'name': rp_name,
            'status_code': resp.status_code,
            'err_text': self.get_error_msg(resp),
        }
        LOG.error(msg, args)

    def get_inventories(self, rp_uuid):
        """Calls the placement API to get resource inventory information.

        :param rp_uuid: UUID of the resource provider to get.
        :return: A dictionary of inventories keyed by resource classes.
        """
        url = '/resource_providers/%s/inventories' % rp_uuid
        resp = self.get(url)
        if resp.status_code == 200:
            json = resp.json()
            return json['inventories']
        msg = ("Failed to get resource provider %(rp_uuid)s inventories. "
               "Got %(status_code)d: %(err_text)s.")
        args = {
            'rp_uuid': rp_uuid,
            'status_code': resp.status_code,
            'err_text': self.get_error_msg(resp),
        }
        LOG.error(msg, args)

    def get_provider_traits(self, rp_uuid):
        """Queries the placement API for a resource provider's traits.

        :param rp_uuid: UUID of the resource provider to grab traits for.
        :return: A list of traits.
        """
        resp = self.get("/resource_providers/%s/traits" % rp_uuid)

        if resp.status_code == 200:
            json = resp.json()
            return json['traits']
        msg = ("Failed to get resource provider %(rp_uuid)s traits. "
               "Got %(status_code)d: %(err_text)s.")
        args = {
            'rp_uuid': rp_uuid,
            'status_code': resp.status_code,
            'err_text': self.get_error_msg(resp),
        }
        LOG.error(msg, args)

    def get_allocations_for_consumer(self, consumer_uuid):
        """Retrieves the allocations for a specific consumer.

        :param consumer_uuid: the UUID of the consumer resource.
        :return: A dictionary of allocation records keyed by resource
                 provider uuid.
        """
        url = '/allocations/%s' % consumer_uuid
        resp = self.get(url)
        if resp.status_code == 200:
            json = resp.json()
            return json['allocations']
        msg = ("Failed to get allocations for consumer %(c_uuid). "
               "Got %(status_code)d: %(err_text)s.")
        args = {
            'c_uuid': consumer_uuid,
            'status_code': resp.status_code,
            'err_text': self.get_error_msg(resp),
        }
        LOG.error(msg, args)

    def get_usages_for_resource_provider(self, rp_uuid):
        """Retrieves the usages for a specific provider.

        :param rp_uuid: The UUID of the provider.
        :return: A dictionary that describes how much each class of
                 resource is being consumed on this resource provider.
        """
        url = '/resource_providers/%s/usages' % rp_uuid
        resp = self.get(url)
        if resp.status_code == 200:
            json = resp.json()
            return json['usages']
        msg = ("Failed to get resource provider %(rp_uuid)s usages. "
               "Got %(status_code)d: %(err_text)s.")
        args = {
            'rp_uuid': rp_uuid,
            'status_code': resp.status_code,
            'err_text': self.get_error_msg(resp),
        }
        LOG.error(msg, args)

    def get_candidate_providers(self, resources):
        """Returns a dictionary of resource provider summaries.

        :param resources: A comma-separated list of strings indicating
                  an amount of resource of a specified class that
                  providers in each allocation request must collectively
                  have the capacity and availability to serve:
                  resources=VCPU:4,DISK_GB:64,MEMORY_MB:2048
        :returns: A dict, keyed by resource provider UUID, which can
                  provide the required resources.
        """
        url = "/allocation_candidates?%s" % resources
        resp = self.get(url)
        if resp.status_code == 200:
            data = resp.json()
            return data['provider_summaries']

        args = {
            'resource_request': resources,
            'status_code': resp.status_code,
            'err_text': self.get_error_msg(resp),
        }
        msg = ("Failed to get allocation candidates from placement "
               "API for resources: %(resource_request)s\n"
               "Got %(status_code)d: %(err_text)s.")
        LOG.error(msg, args)
