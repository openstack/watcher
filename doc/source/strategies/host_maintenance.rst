===========================
Host Maintenance Strategy
===========================

Synopsis
--------

**display name**: ``Host Maintenance Strategy``

**goal**: ``cluster_maintaining``

    .. watcher-term:: watcher.decision_engine.strategy.strategies.host_maintenance.HostMaintenance

Requirements
------------

None.

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

==================== ====== ====================================
parameter            type   default Value description
==================== ====== ====================================
``maintenance_node`` String The name of the compute node which
                            need maintenance. Required.
``backup_node``      String The name of the compute node which
                            will backup the maintenance node.
                            Optional.
==================== ====== ====================================

Efficacy Indicator
------------------

None

Algorithm
---------

For more information on the Host Maintenance Strategy please refer
to: https://specs.openstack.org/openstack/watcher-specs/specs/queens/approved/cluster-maintenance-strategy.html

How to use it ?
---------------

.. code-block:: shell

    $ openstack optimize audit create \
      -g cluster_maintaining -s host_maintenance \
      -p maintenance_node=compute01 \
      -p backup_node=compute02 \
      --auto-trigger

External Links
--------------

None.
