Actions
=======

.. toctree::
   :glob:
   :maxdepth: 1

   ./*

Actions Overview
----------------

This section provides detailed documentation for each action available in
Watcher. Actions are the building blocks of action plans that implement the
optimization strategies recommended by the decision engine.


Available Actions
-----------------

    .. list-table::
       :widths: 33 67
       :header-rows: 1

       * - Action Name
         - Description
       * - :doc:`change_node_power_state`
         - Compute node power on/off through Ironic
       * - :doc:`change_nova_service_state`
         - Disables or enables the nova-compute service on a host
       * - :doc:`migrate`
         - Migrates a server to a destination nova-compute host (live or cold)
       * - :doc:`resize`
         - Resizes a server with the specified flavor
       * - :doc:`stop`
         - Stops a server instance
       * - :doc:`volume_migration`
         - Migrates a volume to a destination node or type

Following Actions are intended to be used **only for testing purposes** and do
not produce any meaningful task.

    .. list-table::
       :widths: 33 67
       :header-rows: 1

       * - Action Name
         - Description
       * - :doc:`nop`
         - Logs a message (**testing only**)
       * - :doc:`sleep`
         - Waits for a given duration (**testing only**)
