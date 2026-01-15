=======================
Change Node Power State
=======================

Synopsis
--------

**action name**: ``change_node_power_state``

Compute node power on/off

By using this action, you will be able to turn on/off the power of a
node managed by the Ironic service.

Configuration
-------------

Action parameters:

======================== ====== ======== ===================================
parameter                type   required description
======================== ====== ======== ===================================
``resource_id``          string yes      Baremetal node id (list of available
                                         ironic nodes is returned by
                                         ``ironic node-list`` command)
``state``                string yes      Power state: "on" or "off"
``resource_name``        string no       Name of the resource
======================== ====== ======== ===================================
