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
       * - `Actuator <https://docs.openstack.org/watcher/latest/strategies/actuation.html>`_
         - Experimental
         - Unit, Integration
         - No
       * - `Basic Offline Server Consolidation <https://docs.openstack.org/watcher/latest/strategies/basic-server-consolidation.html>`_
         - Experimental
         - Missing
         - Yes, with default values
       * - `Host Maintenance Strategy <https://docs.openstack.org/watcher/latest/strategies/host_maintenance.html>`_
         - Supported
         - Unit, Integration
         - No (requires parameters)
       * - `Node Resource Consolidation Strategy <https://docs.openstack.org/watcher/latest/strategies/node_resource_consolidation.html>`_
         - Supported
         - Unit, Integration
         - Yes, with default values
       * - `Noisy Neighbor <https://docs.openstack.org/watcher/latest/strategies/noisy_neighbor.html>`_
         - Deprecated
         - Unit
         - N/A
       * - `Outlet Temperature Based Strategy <https://docs.openstack.org/watcher/latest/strategies/outlet_temp_control.html>`_
         - Experimental
         - Unit
         - Yes, with default values
       * - `Saving Energy Strategy <https://docs.openstack.org/watcher/latest/strategies/saving_energy.html>`_
         - Experimental
         - Unit
         - Yes, with default values
       * - `Storage Capacity Balance <https://docs.openstack.org/watcher/latest/strategies/storage_capacity_balance.html>`_
         - Experimental
         - Unit
         - Yes, with default values
       * - `Uniform Airflow Migration Strategy <https://docs.openstack.org/watcher/latest/strategies/uniform_airflow.html>`_
         - Experimental
         - Unit
         - Yes, with default values
       * - `VM Workload Consolidation Strategy <https://docs.openstack.org/watcher/latest/strategies/vm_workload_consolidation.html>`_
         - Supported
         - Unit, Integration
         - Yes, with default values
       * - `Watcher Overload Standard Deviation Algorithm <https://docs.openstack.org/watcher/latest/strategies/workload-stabilization.html>`_
         - Experimental
         - Missing
         - Yes, with default values
       * - `Workload Balance Migration Strategy <https://docs.openstack.org/watcher/latest/strategies/workload_balance.html>`_
         - Supported
         - Unit, Integration
         - Yes, with default values
       * - `Zone Migration <https://docs.openstack.org/watcher/latest/strategies/zone_migration.html>`_
         - Supported (Instance migrations), Experimental (Volume migration)
         - Unit, Some Integration
         - No
