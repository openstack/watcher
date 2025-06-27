Strategies
==========

.. toctree::
   :glob:
   :maxdepth: 1

   ./*

Strategies status matrix
------------------------

    .. list-table::
       :widths: 20 20 20 20
       :header-rows: 1

       * - Strategy Name
         - Status
         - Testing
         - Can Be Triggered from Horizon (UI)
       * - :doc:`actuation`
         - Experimental
         - Unit, Integration
         - No
       * - :doc:`basic-server-consolidation`
         - Experimental
         - Missing
         - Yes, with default values
       * - :doc:`host_maintenance`
         - Supported
         - Unit, Integration
         - No (requires parameters)
       * - :doc:`node_resource_consolidation`
         - Supported
         - Unit, Integration
         - Yes, with default values
       * - :doc:`noisy_neighbor`
         - Deprecated
         - Unit
         - N/A
       * - :doc:`outlet_temp_control`
         - Experimental
         - Unit
         - Yes, with default values
       * - :doc:`saving_energy`
         - Experimental
         - Unit
         - Yes, with default values
       * - :doc:`storage_capacity_balance`
         - Experimental
         - Unit
         - Yes, with default values
       * - :doc:`uniform_airflow`
         - Experimental
         - Unit
         - Yes, with default values
       * - :doc:`vm_workload_consolidation`
         - Supported
         - Unit, Integration
         - Yes, with default values
       * - :doc:`workload-stabilization`
         - Experimental
         - Missing
         - Yes, with default values
       * - :doc:`workload_balance`
         - Supported
         - Unit, Integration
         - Yes, with default values
       * - :doc:`zone_migration`
         - Supported (Instance migrations), Experimental (Volume migration)
         - Unit, Some Integration
         - No
