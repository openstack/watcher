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
#

import random
import time

from oslo_log import log

import cinderclient.exceptions as ciexceptions
import novaclient.exceptions as nvexceptions

from watcher.common import clients

LOG = log.getLogger(__name__)


class NovaHelper(object):

    def __init__(self, osc=None):
        """:param osc: an OpenStackClients instance"""
        self.osc = osc if osc else clients.OpenStackClients()
        self.neutron = self.osc.neutron()
        self.cinder = self.osc.cinder()
        self.nova = self.osc.nova()
        self.glance = self.osc.glance()

    def get_hypervisors_list(self):
        return self.nova.hypervisors.list()

    def find_instance(self, instance_id):
        search_opts = {'all_tenants': True}
        instances = self.nova.servers.list(detailed=True,
                                           search_opts=search_opts)
        instance = None
        for _instance in instances:
            if _instance.id == instance_id:
                instance = _instance
                break
        return instance

    def watcher_non_live_migrate_instance(self, instance_id, hypervisor_id,
                                          keep_original_image_name=True):
        """This method migrates a given instance

        using an image of this instance and creating a new instance
        from this image. It saves some configuration information
        about the original instance : security group, list of networks,
        list of attached volumes, floating IP, ...
        in order to apply the same settings to the new instance.
        At the end of the process the original instance is deleted.
        It returns True if the migration was successful,
        False otherwise.

        :param instance_id: the unique id of the instance to migrate.
        :param keep_original_image_name: flag indicating whether the
            image name from which the original instance was built must be
            used as the name of the intermediate image used for migration.
            If this flag is False, a temporary image name is built
        """

        new_image_name = ""

        LOG.debug(
            "Trying a non-live migrate of instance '%s' "
            "using a temporary image ..." % instance_id)

        # Looking for the instance to migrate
        instance = self.find_instance(instance_id)
        if not instance:
            LOG.debug("Instance %s not found !" % instance_id)
            return False
        else:
            host_name = getattr(instance, "OS-EXT-SRV-ATTR:host")
            LOG.debug(
                "Instance %s found on host '%s'." % (instance_id, host_name))

            if not keep_original_image_name:
                # randrange gives you an integral value
                irand = random.randint(0, 1000)

                # Building the temporary image name
                # which will be used for the migration
                new_image_name = "tmp-migrate-%s-%s" % (instance_id, irand)
            else:
                # Get the image name of the current instance.
                # We'll use the same name for the new instance.
                imagedict = getattr(instance, "image")
                image_id = imagedict["id"]
                image = self.nova.images.get(image_id)
                new_image_name = getattr(image, "name")

            instance_name = getattr(instance, "name")
            flavordict = getattr(instance, "flavor")
            # a_dict = dict([flavorstr.strip('{}').split(":"),])
            flavor_id = flavordict["id"]
            flavor = self.nova.flavors.get(flavor_id)
            flavor_name = getattr(flavor, "name")
            keypair_name = getattr(instance, "key_name")

            addresses = getattr(instance, "addresses")

            floating_ip = ""
            network_names_list = []

            for network_name, network_conf_obj in addresses.items():
                LOG.debug(
                    "Extracting network configuration for network '%s'" %
                    network_name)

                network_names_list.append(network_name)

                for net_conf_item in network_conf_obj:
                    if net_conf_item['OS-EXT-IPS:type'] == "floating":
                        floating_ip = net_conf_item['addr']
                        break

            sec_groups_list = getattr(instance, "security_groups")
            sec_groups = []

            for sec_group_dict in sec_groups_list:
                sec_groups.append(sec_group_dict['name'])

            # Stopping the old instance properly so
            # that no new data is sent to it and to its attached volumes
            stopped_ok = self.stop_instance(instance_id)

            if not stopped_ok:
                LOG.debug("Could not stop instance: %s" % instance_id)
                return False

            # Building the temporary image which will be used
            # to re-build the same instance on another target host
            image_uuid = self.create_image_from_instance(instance_id,
                                                         new_image_name)

            if not image_uuid:
                LOG.debug(
                    "Could not build temporary image of instance: %s" %
                    instance_id)
                return False

            #
            # We need to get the list of attached volumes and detach
            # them from the instance in order to attache them later
            # to the new instance
            #
            blocks = []

            # Looks like this :
            # os-extended-volumes:volumes_attached |
            # [{u'id': u'c5c3245f-dd59-4d4f-8d3a-89d80135859a'}]
            attached_volumes = getattr(instance,
                                       "os-extended-volumes:volumes_attached")

            for attached_volume in attached_volumes:
                volume_id = attached_volume['id']

                try:
                    volume = self.cinder.volumes.get(volume_id)

                    attachments_list = getattr(volume, "attachments")

                    device_name = attachments_list[0]['device']
                    # When a volume is attached to an instance
                    # it contains the following property :
                    # attachments = [{u'device': u'/dev/vdb',
                    # u'server_id': u'742cc508-a2f2-4769-a794-bcdad777e814',
                    # u'id': u'f6d62785-04b8-400d-9626-88640610f65e',
                    # u'host_name': None, u'volume_id':
                    # u'f6d62785-04b8-400d-9626-88640610f65e'}]

                    # boot_index indicates a number
                    # designating the boot order of the device.
                    # Use -1 for the boot volume,
                    # choose 0 for an attached volume.
                    block_device_mapping_v2_item = {"device_name": device_name,
                                                    "source_type": "volume",
                                                    "destination_type":
                                                        "volume",
                                                    "uuid": volume_id,
                                                    "boot_index": "0"}

                    blocks.append(
                        block_device_mapping_v2_item)

                    LOG.debug("Detaching volume %s from instance: %s" % (
                        volume_id, instance_id))
                    # volume.detach()
                    self.nova.volumes.delete_server_volume(instance_id,
                                                           volume_id)

                    if not self.wait_for_volume_status(volume, "available", 5,
                                                       10):
                        LOG.debug(
                            "Could not detach volume %s from instance: %s" % (
                                volume_id, instance_id))
                        return False
                except ciexceptions.NotFound:
                    LOG.debug("Volume '%s' not found " % image_id)
                    return False

            # We create the new instance from
            # the intermediate image of the original instance
            new_instance = self. \
                create_instance(hypervisor_id,
                                instance_name,
                                image_uuid,
                                flavor_name,
                                sec_groups,
                                network_names_list=network_names_list,
                                keypair_name=keypair_name,
                                create_new_floating_ip=False,
                                block_device_mapping_v2=blocks)

            if not new_instance:
                LOG.debug(
                    "Could not create new instance "
                    "for non-live migration of instance %s" % instance_id)
                return False

            try:
                LOG.debug("Detaching floating ip '%s' from instance %s" % (
                    floating_ip, instance_id))
                # We detach the floating ip from the current instance
                instance.remove_floating_ip(floating_ip)

                LOG.debug(
                    "Attaching floating ip '%s' to the new instance %s" % (
                        floating_ip, new_instance.id))

                # We attach the same floating ip to the new instance
                new_instance.add_floating_ip(floating_ip)
            except Exception as e:
                LOG.debug(e)

            new_host_name = getattr(new_instance, "OS-EXT-SRV-ATTR:host")

            # Deleting the old instance (because no more useful)
            delete_ok = self.delete_instance(instance_id)
            if not delete_ok:
                LOG.debug("Could not delete instance: %s" % instance_id)
                return False

            LOG.debug(
                "Instance %s has been successfully migrated "
                "to new host '%s' and its new id is %s." % (
                    instance_id, new_host_name, new_instance.id))

            return True

    def live_migrate_instance(self, instance_id, dest_hostname,
                              block_migration=False, retry=120):
        """This method does a live migration of a given instance

        This method uses the Nova built-in live_migrate()
        action to do a live migration of a given instance.

        It returns True if the migration was successful,
        False otherwise.

        :param instance_id: the unique id of the instance to migrate.
        :param dest_hostname: the name of the destination compute node.
        :param block_migration:  No shared storage is required.
        """

        LOG.debug("Trying a live migrate of instance %s to host '%s'" % (
            instance_id, dest_hostname))

        # Looking for the instance to migrate
        instance = self.find_instance(instance_id)

        if not instance:
            LOG.debug("Instance not found: %s" % instance_id)
            return False
        else:
            host_name = getattr(instance, 'OS-EXT-SRV-ATTR:host')
            LOG.debug(
                "Instance %s found on host '%s'." % (instance_id, host_name))

            instance.live_migrate(host=dest_hostname,
                                  block_migration=block_migration,
                                  disk_over_commit=True)
            while getattr(instance,
                          'OS-EXT-SRV-ATTR:host') != dest_hostname \
                    and retry:
                instance = self.nova.servers.get(instance.id)
                LOG.debug(
                    'Waiting the migration of {0}  to {1}'.format(
                        instance,
                        getattr(instance,
                                'OS-EXT-SRV-ATTR:host')))
                time.sleep(1)
                retry -= 1

            host_name = getattr(instance, 'OS-EXT-SRV-ATTR:host')
            if host_name != dest_hostname:
                return False

            LOG.debug(
                "Live migration succeeded : "
                "instance %s is now on host '%s'." % (
                    instance_id, host_name))

            return True

        return False

    def enable_service_nova_compute(self, hostname):
        if self.nova.services.enable(host=hostname,
                                     binary='nova-compute'). \
                status == 'enabled':
            return True
        else:
            return False

    def disable_service_nova_compute(self, hostname):
        if self.nova.services.disable(host=hostname,
                                      binary='nova-compute'). \
                status == 'disabled':
            return True
        else:
            return False

    def set_host_offline(self, hostname):
        # See API on http://developer.openstack.org/api-ref-compute-v2.1.html
        # especially the PUT request
        # regarding this resource : /v2.1/os-hosts/​{host_name}​
        #
        # The following body should be sent :
        # {
        # "host": {
        # "host": "65c5d5b7e3bd44308e67fc50f362aee6",
        # "maintenance_mode": "off_maintenance",
        # "status": "enabled"
        # }
        # }

        # Voir ici
        # https://github.com/openstack/nova/
        # blob/master/nova/virt/xenapi/host.py
        # set_host_enabled(self, enabled):
        # Sets the compute host's ability to accept new instances.
        # host_maintenance_mode(self, host, mode):
        # Start/Stop host maintenance window.
        # On start, it triggers guest VMs evacuation.
        host = self.nova.hosts.get(hostname)

        if not host:
            LOG.debug("host not found: %s" % hostname)
            return False
        else:
            host[0].update(
                {"maintenance_mode": "disable", "status": "disable"})
            return True

    def create_image_from_instance(self, instance_id, image_name,
                                   metadata={"reason": "instance_migrate"}):
        """This method creates a new image from a given instance.

        It waits for this image to be in 'active' state before returning.
        It returns the unique UUID of the created image if successful,
        None otherwise.

        :param instance_id: the uniqueid of
            the instance to backup as an image.
        :param image_name: the name of the image to create.
        :param metadata: a dictionary containing the list of
            key-value pairs to associate to the image as metadata.
        """
        LOG.debug(
            "Trying to create an image from instance %s ..." % instance_id)

        # Looking for the instance
        instance = self.find_instance(instance_id)

        if not instance:
            LOG.debug("Instance not found: %s" % instance_id)
            return None
        else:
            host_name = getattr(instance, 'OS-EXT-SRV-ATTR:host')
            LOG.debug(
                "Instance %s found on host '%s'." % (instance_id, host_name))

            # We need to wait for an appropriate status
            # of the instance before we can build an image from it
            if self.wait_for_instance_status(instance, ('ACTIVE', 'SHUTOFF'),
                                             5,
                                             10):
                image_uuid = self.nova.servers.create_image(instance_id,
                                                            image_name,
                                                            metadata)

                image = self.glance.images.get(image_uuid)

                # Waiting for the new image to be officially in ACTIVE state
                # in order to make sure it can be used
                status = image.status
                retry = 10
                while status != 'active' and status != 'error' and retry:
                    time.sleep(5)
                    retry -= 1
                    # Retrieve the instance again so the status field updates
                    image = self.glance.images.get(image_uuid)
                    status = image.status
                    LOG.debug("Current image status: %s" % status)

                if not image:
                    LOG.debug("Image not found: %s" % image_uuid)
                else:
                    LOG.debug(
                        "Image %s successfully created for instance %s" % (
                            image_uuid, instance_id))
                    return image_uuid
        return None

    def delete_instance(self, instance_id):
        """This method deletes a given instance.

        :param instance_id: the unique id of the instance to delete.
        """

        LOG.debug("Trying to remove instance %s ..." % instance_id)

        instance = self.find_instance(instance_id)

        if not instance:
            LOG.debug("Instance not found: %s" % instance_id)
            return False
        else:
            self.nova.servers.delete(instance_id)
            LOG.debug("Instance %s removed." % instance_id)
            return True

    def stop_instance(self, instance_id):
        """This method stops a given instance.

        :param instance_id: the unique id of the instance to stop.
        """

        LOG.debug("Trying to stop instance %s ..." % instance_id)

        instance = self.find_instance(instance_id)

        if not instance:
            LOG.debug("Instance not found: %s" % instance_id)
            return False
        else:
            self.nova.servers.stop(instance_id)

            if self.wait_for_vm_state(instance, "stopped", 8, 10):
                LOG.debug("Instance %s stopped." % instance_id)
                return True
            else:
                return False

    def wait_for_vm_state(self, server, vm_state, retry, sleep):
        """Waits for server to be in a specific vm_state

        The vm_state can be one of the following :
        active, stopped

        :param server: server object.
        :param vm_state: for which state we are waiting for
        :param retry: how many times to retry
        :param sleep: seconds to sleep between the retries
        """

        if not server:
            return False

        while getattr(server, 'OS-EXT-STS:vm_state') != vm_state and retry:
            time.sleep(sleep)
            server = self.nova.servers.get(server)
            retry -= 1
        return getattr(server, 'OS-EXT-STS:vm_state') == vm_state

    def wait_for_instance_status(self, instance, status_list, retry, sleep):
        """Waits for instance to be in a specific status

        The status can be one of the following
        : BUILD, ACTIVE, ERROR, VERIFY_RESIZE, SHUTOFF

        :param instance: instance object.
        :param status_list: tuple containing the list of
            status we are waiting for
        :param retry: how many times to retry
        :param sleep: seconds to sleep between the retries
        """

        if not instance:
            return False

        while instance.status not in status_list and retry:
            LOG.debug("Current instance status: %s" % instance.status)
            time.sleep(sleep)
            instance = self.nova.servers.get(instance.id)
            retry -= 1
        LOG.debug("Current instance status: %s" % instance.status)
        return instance.status in status_list

    def create_instance(self, hypervisor_id, inst_name="test", image_id=None,
                        flavor_name="m1.tiny",
                        sec_group_list=["default"],
                        network_names_list=["demo-net"], keypair_name="mykeys",
                        create_new_floating_ip=True,
                        block_device_mapping_v2=None):
        """This method creates a new instance

        It also creates, if requested, a new floating IP and associates
        it with the new instance
        It returns the unique id of the created instance.
        """

        LOG.debug(
            "Trying to create new instance '%s' "
            "from image '%s' with flavor '%s' ..." % (
                inst_name, image_id, flavor_name))

        try:
            self.nova.keypairs.findall(name=keypair_name)
        except nvexceptions.NotFound:
            LOG.debug("Key pair '%s' not found " % keypair_name)
            return

        try:
            image = self.nova.images.get(image_id)
        except nvexceptions.NotFound:
            LOG.debug("Image '%s' not found " % image_id)
            return

        try:
            flavor = self.nova.flavors.find(name=flavor_name)
        except nvexceptions.NotFound:
            LOG.debug("Flavor '%s' not found " % flavor_name)
            return

        # Make sure all security groups exist
        for sec_group_name in sec_group_list:
            try:
                self.nova.security_groups.find(name=sec_group_name)

            except nvexceptions.NotFound:
                LOG.debug("Security group '%s' not found " % sec_group_name)
                return

        net_list = list()

        for network_name in network_names_list:
            nic_id = self.get_network_id_from_name(network_name)

            if not nic_id:
                LOG.debug("Network '%s' not found " % network_name)
                return
            net_obj = {"net-id": nic_id}
            net_list.append(net_obj)

        instance = self.nova.servers. \
            create(inst_name,
                   image, flavor=flavor,
                   key_name=keypair_name,
                   security_groups=sec_group_list,
                   nics=net_list,
                   block_device_mapping_v2=block_device_mapping_v2,
                   availability_zone="nova:" +
                                     hypervisor_id)

        # Poll at 5 second intervals, until the status is no longer 'BUILD'
        if instance:
            if self.wait_for_instance_status(instance,
                                             ('ACTIVE', 'ERROR'), 5, 10):
                instance = self.nova.servers.get(instance.id)

                if create_new_floating_ip and instance.status == 'ACTIVE':
                    LOG.debug(
                        "Creating a new floating IP"
                        " for instance '%s'" % instance.id)
                    # Creating floating IP for the new instance
                    floating_ip = self.nova.floating_ips.create()

                    instance.add_floating_ip(floating_ip)

                    LOG.debug("Instance %s associated to Floating IP '%s'" % (
                        instance.id, floating_ip.ip))

        return instance

    def get_network_id_from_name(self, net_name="private"):
        """This method returns the unique id of the provided network name"""
        networks = self.neutron.list_networks(name=net_name)

        # LOG.debug(networks)
        network_id = networks['networks'][0]['id']

        return network_id

    def get_vms_by_hypervisor(self, host):
        return [vm for vm in
                self.nova.servers.list(search_opts={"all_tenants": True})
                if self.get_hostname(vm) == host]

    def get_hostname(self, vm):
        return str(getattr(vm, 'OS-EXT-SRV-ATTR:host'))

    def get_flavor_instance(self, instance, cache):
        fid = instance.flavor['id']
        if fid in cache:
            flavor = cache.get(fid)
        else:
            try:
                flavor = self.nova.flavors.get(fid)
            except ciexceptions.NotFound:
                flavor = None
            cache[fid] = flavor
        attr_defaults = [('name', 'unknown-id-%s' % fid),
                         ('vcpus', 0), ('ram', 0), ('disk', 0),
                         ('ephemeral', 0)]
        for attr, default in attr_defaults:
            if not flavor:
                instance.flavor[attr] = default
                continue
            instance.flavor[attr] = getattr(flavor, attr, default)
