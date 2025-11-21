=======
Migrate
=======

Synopsis
--------

**action name**: ``migrate``

Migrates a server to a destination nova compute host

This action will allow you to migrate a server to another compute
destination host.
Migration type 'live' can only be used for migrating active VMs.
Migration type 'cold' can be used for migrating non-active VMs
as well active VMs, which will be shut down while migrating.

.. note::

    Nova API version must be 2.56 or above if ``destination_node`` parameter
    is given.

Configuration
-------------

Action parameters:

======================== ====== ======== ===================================
parameter                type   required description
======================== ====== ======== ===================================
``resource_id``          string yes      UUID of the server to migrate
``migration_type``       string yes      Type of migration: "live" or "cold"
``source_node``          string yes      Source compute hostname
``destination_node``     string no       Destination compute hostname.
                                         If not specified, nova-scheduler
                                         will determine the destination
======================== ====== ======== ===================================
