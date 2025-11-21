================
Volume Migration
================

Synopsis
--------

**action name**: ``volume_migrate``

Migrates a volume to destination node or type

By using this action, you will be able to migrate cinder volume.
Migration type 'migrate' can be used for migrating a volume to
another pool with the same volume type.
Migration type 'retype' can be used for changing the volume type of
a volume.

Configuration
-------------

Action parameters:

======================== ====== ======== ===================================
parameter                type   required description
======================== ====== ======== ===================================
``resource_id``          string yes      UUID of cinder volume to migrate
``migration_type``       string yes      Type of migration: "migrate" or
                                         "retype"
``destination_node``     string no       Destination block storage pool name
                                         (list of available pools returned by
                                         ``openstack volume backend pool list``
                                         command).
                                         Mandatory for migrating a volume
                                         to a different backend with the same
                                         volume type
``destination_type``     string no       Destination block storage type name
                                         (list of available types returned by
                                         ``openstack volume type list``
                                         command).
                                         Mandatory for changing a volume
                                         to a different volume type
======================== ====== ======== ===================================
