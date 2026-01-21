============
Integrations
============

The following table provides an Integration status with different services
which Watcher interact with. Some integrations are marked as Supported,
while others as Experimental due to the lack of testing and a proper
documentations.

Integration Status Matrix
-------------------------

    .. list-table::
       :widths: 20 20 20 20
       :header-rows: 1

       * - Service Name
         - Integration Status
         - Documentation
         - Testing
       * - :ref:`Cinder <cinder_integration>`
         - Supported
         - Minimal
         - Unit
       * - :ref:`Glance <glance_integration>`
         - Experimental
         - Missing
         - None
       * - :ref:`Ironic <ironic_integration>`
         - Experimental
         - Minimal
         - Unit
       * - :ref:`Keystone <keystone_integration>`
         - Supported
         - Minimal
         - Integration
       * - :ref:`MAAS <maas_integration>`
         - Deprecated
         - Missing
         - Unit
       * - :ref:`Neutron <neutron_integration>`
         - Experimental
         - Missing
         - Unit
       * - :ref:`Nova <nova_integration>`
         - Supported
         - Minimal
         - Unit and Integration
       * - :ref:`Placement <placement_integration>`
         - Supported
         - Minimal
         - Unit and Integration

.. note::
   Minimal documentation covers only basic configuration and, if available,
   how to enable notifications.

.. _cinder_integration:

Cinder
^^^^^^
The OpenStack Block Storage service integration includes a cluster data
model collector that creates a in-memory representation of the storage
resources, strategies that propose solutions based on storage capacity
and Actions that perform volume migration.

.. _glance_integration:

Glance
^^^^^^
The Image service integration is consumed by Nova Helper to create instances
from images, which was used older releases of Watcher to cold migrate
instances. This procedure is not used by Watcher anymore and this integration
is classified as Experimental and may be removed in future releases.

.. _ironic_integration:

Ironic
^^^^^^
The Bare Metal service integration includes a data model collector that
creates an in-memory representation of Ironic resources and Actions that
allows the management of the power state of nodes. This integration is
classified as Experimental and may be removed in future releases.

.. _keystone_integration:

Keystone
^^^^^^^^
The Identity service integration includes authentication with other services
and retrieving information about domains, projects and users.

.. _maas_integration:

MAAS (Metal As A Service)
^^^^^^^^^^^^^^^^^^^^^^^^^
This integration allows managing bare metal servers of a MAAS service,
which includes Actions that manage the power state of nodes. This
integration is deprecated and will be removed in a future release.

.. _neutron_integration:

Neutron
^^^^^^^
Neutron integration is currently consumed by Nova Helper to create instance,
which was used by older releases of Watcher to cold migrate instances. This
procedure is not used by Watcher anymore and this integration is classified
as Experimental and may be removed in future releases.

.. _nova_integration:

Nova
^^^^
Nova service integration includes a cluster data model collector that creates
an in-memory representation of the compute resources available in the cloud,
strategies that propose solutions based on available resources and Actions
that perform instance migrations.

.. _placement_integration:

Placement
^^^^^^^^^
Placement integration allows Watcher to track resource provider inventories
and usages information, building a in-memory representation of those resources
that can be used by strategies when calculating new solutions.

