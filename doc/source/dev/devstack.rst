..
      Except where otherwise noted, this document is licensed under Creative
      Commons Attribution 3.0 License.  You can view the license at:

          https://creativecommons.org/licenses/by/3.0/

=============================================
Set up a development environment via DevStack
=============================================

Watcher is currently able to optimize compute resources - specifically Nova
compute hosts - via operations such as live migrations.  In order for you to
fully be able to exercise what Watcher can do, it is necessary to have a
multinode environment to use.  If you have no experience with DevStack, you
should check out the `DevStack documentation`_ and be comfortable with the
basics of DevStack before attempting to get a multinode DevStack setup with
the Watcher plugin.

You can set up the Watcher services quickly and easily using a Watcher
DevStack plugin.  See `PluginModelDocs`_ for information on DevStack's plugin
model.

.. _DevStack documentation: http://docs.openstack.org/developer/devstack/
.. _PluginModelDocs: http://docs.openstack.org/developer/devstack/plugins.html

It is recommended that you build off of the provided example local.conf files
(`local.conf.controller`_, `local.conf.compute`_).  You'll likely want to
configure something to obtain metrics, such as Ceilometer.  Ceilometer is used
in the example local.conf files.

To configure the Watcher services with DevStack, add the following to the
`[[local|localrc]]` section of your controller's `local.conf` to enable the
Watcher plugin::

    enable_plugin watcher git://git.openstack.org/openstack/watcher

Then run devstack normally::

    cd /opt/stack/devstack
    ./stack.sh

.. _local.conf.controller: https://github.com/openstack/watcher/tree/master/devstack/local.conf.controller
.. _local.conf.compute: https://github.com/openstack/watcher/tree/master/devstack/local.conf.compute

Multi-Node DevStack Environment
===============================

Since deploying Watcher with only a single compute node is not very useful, a
few tips are given here for enabling a multi-node environment with live
migration.

Configuring NFS Server
----------------------

If you would like to use live migration for shared storage, then the controller
can serve as the NFS server if needed::

    sudo apt-get install nfs-kernel-server
    sudo mkdir -p /nfs/instances
    sudo chown stack:stack /nfs/instances

Add an entry to `/etc/exports` with the appropriate gateway and netmask
information::

    /nfs/instances <gateway>/<netmask>(rw,fsid=0,insecure,no_subtree_check,async,no_root_squash)

Export the NFS directories::

    sudo exportfs -ra

Make sure the NFS server is running::

    sudo service nfs-kernel-server status

If the server is not running, then start it::

    sudo service nfs-kernel-server start

Configuring NFS on Compute Node
-------------------------------

Each compute node needs to use the NFS server to hold the instance data::

    sudo apt-get install rpcbind nfs-common
    mkdir -p /opt/stack/data/instances
    sudo mount <nfs-server-ip>:/nfs/instances /opt/stack/data/instances

If you would like to have the NFS directory automatically mounted on reboot,
then add the following to `/etc/fstab`::

    <nfs-server-ip>:/nfs/instances /opt/stack/data/instances nfs auto 0 0

Edit `/etc/libvirt/libvirtd.conf` to make sure the following values are set::

    listen_tls = 0
    listen_tcp = 1
    auth_tcp = "none"

Edit `/etc/default/libvirt-bin`::

    libvirt_opts="-d -l"

Restart the libvirt service::

    sudo service libvirt-bin restart


Setting up SSH keys between compute nodes to enable live migration
------------------------------------------------------------------

In order for live migration to work, SSH keys need to be exchanged between
each compute node:

1. The SOURCE root user's public RSA key (likely in /root/.ssh/id_rsa.pub)
   needs to be in the DESTINATION stack user's authorized_keys file
   (~stack/.ssh/authorized_keys).  This can be accomplished by manually
   copying the contents from the file on the SOURCE to the DESTINATION.  If
   you have a password configured for the stack user, then you can use the
   following command to accomplish the same thing::

        ssh-copy-id -i /root/.ssh/id_rsa.pub stack@DESTINATION

2. The DESTINATION host's public ECDSA key (/etc/ssh/ssh_host_ecdsa_key.pub)
   needs to be in the SOURCE root user's known_hosts file
   (/root/.ssh/known_hosts).  This can be accomplished by running the
   following on the SOURCE machine (hostname must be used)::

        ssh-keyscan -H DEST_HOSTNAME | sudo tee -a /root/.ssh/known_hosts

In essence, this means that every compute node's root user's public RSA key
must exist in every other compute node's stack user's authorized_keys file and
every compute node's public ECDSA key needs to be in every other compute
node's root user's known_hosts file.
