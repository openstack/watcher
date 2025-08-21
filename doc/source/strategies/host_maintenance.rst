===========================
Host Maintenance Strategy
===========================

Synopsis
--------

**display name**: ``Host Maintenance Strategy``

**goal**: ``cluster_maintaining``

    .. watcher-term:: watcher.decision_engine.strategy.strategies.host_maintenance.HostMaintenance


Metrics
*******

None

Cluster data model
******************

Default Watcher's Compute cluster data model:

    .. watcher-term:: watcher.decision_engine.model.collector.nova.NovaClusterDataModelCollector

Actions
*******

Default Watcher's actions:

    .. list-table::
       :widths: 30 30
       :header-rows: 1

       * - action
         - description
       * - ``migration``
         - .. watcher-term:: watcher.applier.actions.migration.Migrate
       * - ``change_nova_service_state``
         - .. watcher-term:: watcher.applier.actions.change_nova_service_state.ChangeNovaServiceState

Planner
*******

Default Watcher's planner:

    .. watcher-term:: watcher.decision_engine.planner.weight.WeightPlanner

Configuration
-------------

Strategy parameters are:

========================== ======== ========================== ==========
parameter                  type     description                required
========================== ======== ========================== ==========
``maintenance_node``       String   The name of the            Required
                                    compute node
                                    which needs maintenance.
``backup_node``            String   The name of the compute    Optional
                                    node which will backup
                                    the maintenance node.
``disable_live_migration`` Boolean  False: Active instances    Optional
                                    will be live migrated.
                                    True: Active instances
                                    will be cold migrated
                                    if cold migration is
                                    not disabled. Otherwise,
                                    they will be stopped.
                                    False by default.
``disable_cold_migration`` Boolean  False: Inactive instances  Optional
                                    will be cold migrated.
                                    True: Inactive instances
                                    will not be cold migrated.
                                    False by default.
========================== ======== ========================== ==========

Efficacy Indicator
------------------

None

Algorithm
---------

For more information on the Host Maintenance Strategy please refer
to: https://specs.openstack.org/openstack/watcher-specs/specs/queens/approved/cluster-maintenance-strategy.html

How to use it ?
---------------

Run an audit using Host Maintenance strategy.
Executing the actions will move the servers from compute01 host
to a host determined by the Nova scheduler service.

.. code-block:: shell

    $ openstack optimize audit create \
      -g cluster_maintaining -s host_maintenance \
      -p maintenance_node=compute01

Run an audit using Host Maintenance strategy with a backup node specified.
Executing the actions will move the servers from compute01 host
to compute02 host.

.. code-block:: shell

    $ openstack optimize audit create \
      -g cluster_maintaining -s host_maintenance \
      -p maintenance_node=compute01 \
      -p backup_node=compute02

Run an audit using Host Maintenance strategy with migration disabled.
This will only stop active instances on compute01, useful for maintenance
scenarios where operators do not want to migrate workloads to other hosts.

.. code-block:: shell

    $ openstack optimize audit create \
      -g cluster_maintaining -s host_maintenance \
      -p maintenance_node=compute01 \
      -p disable_live_migration=True \
      -p disable_cold_migration=True

Note that after executing this strategy, the *maintenance_node* will be
marked as disabled, with the reason set to ``watcher_maintaining``.
To enable the node again:

.. code-block:: shell

   $ openstack compute service set --enable compute01

External Links
--------------

None.
