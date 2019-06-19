==================================
VM Workload Consolidation Strategy
==================================

Synopsis
--------

**display name**: ``VM Workload Consolidation Strategy``

**goal**: ``vm_consolidation``

    .. watcher-term:: watcher.decision_engine.strategy.strategies.vm_workload_consolidation.VMWorkloadConsolidation

Requirements
------------

Metrics
*******

The *vm_workload_consolidation* strategy requires the following metrics:

============================ ============ ======= =========================
metric                       service name plugins comment
============================ ============ ======= =========================
``cpu_util``                 ceilometer_  none    cpu_util has been removed
                                                  since Stein.
``memory.resident``          ceilometer_  none
``memory``                   ceilometer_  none
``disk.root.size``           ceilometer_  none
============================ ============ ======= =========================

.. _ceilometer: https://docs.openstack.org/ceilometer/latest/admin/telemetry-measurements.html#openstack-compute

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

Strategy parameter is:

====================== ====== ============= ===================================
parameter              type   default Value description
====================== ====== ============= ===================================
``period``             Number 3600          The time interval in seconds
                                            for getting statistic aggregation
                                            from metric data source
====================== ====== ============= ===================================


Efficacy Indicator
------------------

.. watcher-func::
  :format: literal_block

  watcher.decision_engine.goal.efficacy.specs.ServerConsolidation.get_global_efficacy_indicator

Algorithm
---------

For more information on the VM Workload consolidation strategy please refer to: https://specs.openstack.org/openstack/watcher-specs/specs/mitaka/implemented/zhaw-load-consolidation.html

How to use it ?
---------------

.. code-block:: shell

    $ openstack optimize audittemplate create \
      at1 server_consolidation --strategy vm_workload_consolidation

    $ openstack optimize audit create -a at1

External Links
--------------

*Spec URL*
https://specs.openstack.org/openstack/watcher-specs/specs/mitaka/implemented/zhaw-load-consolidation.html
