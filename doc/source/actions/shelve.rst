======
Shelve
======

Synopsis
--------

**action name**: ``shelve``

Shelves a server instance

This action will allow you to shelve a server instance on a compute host.
The instance keeps all data and associated resources but does not retain
in-memory information. Compute resources (vCPU, RAM) are freed on the host,
while the root disk is preserved (uploaded to Glance or kept in shared
storage).

Configuration
-------------

Action parameters:

.. list-table::
   :widths: 25 10 10 55
   :header-rows: 1

   * - parameter
     - type
     - required
     - description
   * - ``resource_id``
     - string
     - yes
     - UUID of the server instance to shelve

Skipping conditions
--------------------

Shelve actions will be automatically skipped in the pre_condition phase in
the following cases:

- The server does not exist
- The server is already in ``SHELVED`` or ``SHELVED_OFFLOADED`` state

.. note::
   Nova may automatically offload a shelved instance (transitioning from
   ``SHELVED`` to ``SHELVED_OFFLOADED``), especially when using shared
   storage (e.g. Ceph) or boot-from-volume instances. Both states are
   accepted as valid postconditions.
