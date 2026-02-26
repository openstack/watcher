==========================
Change Nova Service State
==========================

Synopsis
--------

**action name**: ``change_nova_service_state``

Disables or enables the nova-compute service, deployed on a host

By using this action, you will be able to update the state of a
nova-compute service. A disabled nova-compute service can not be selected
by the nova scheduler for future deployment of server.

Configuration
-------------

Action parameters:

======================== ====== ======== ===================================
parameter                type   required description
======================== ====== ======== ===================================
``resource_id``          string yes      nova-compute service name
``state``                string yes      Service state: "enabled" or "disabled"
``resource_name``        string yes      nova-compute service name
``disabled_reason``      string no       Reason why Watcher disables this
                                         nova-compute service. Value should
                                         have ``watcher_`` prefix, such as
                                         ``watcher_disabled`` or
                                         ``watcher_maintaining``
======================== ====== ======== ===================================

Skipping conditions
--------------------

Change nova service state actions will be automatically skipped in the
pre_condition phase in the following cases:

- nova-compute service does not exist
- nova-compute service is already in the desired state (enabled or disabled)
