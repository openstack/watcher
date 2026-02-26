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

Skipping conditions
--------------------

Volume migration actions will be automatically skipped in the pre_condition
phase in the following cases:

- The volume does not exist
- The migration_type is 'retype' and the destination_type is the same as the
  current volume type
- The migration_type is 'migrate' and the destination_node is the same as the
  current volume host

On other conditions the action will be FAILED in the pre_condition check:

- The destination_type does not exist (if specified)
- The destination_node (pool) does not exist (if specified)
