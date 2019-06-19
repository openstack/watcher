==================================
Basic Offline Server Consolidation
==================================

Synopsis
--------

**display name**: ``Basic offline consolidation``

**goal**: ``server_consolidation``

    .. watcher-term:: watcher.decision_engine.strategy.strategies.basic_consolidation.BasicConsolidation

Requirements
------------

Metrics
*******

The *basic* strategy requires the following metrics:

============================ ============ ======= ===========================
metric                       service name plugins comment
============================ ============ ======= ===========================
``compute.node.cpu.percent`` ceilometer_  none    need to set the
                                                  ``compute_monitors`` option
                                                  to ``cpu.virt_driver`` in
                                                  the nova.conf.
``cpu_util``                 ceilometer_  none    cpu_util has been removed
                                                  since Stein.
============================ ============ ======= ===========================

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
``migration_attempts`` Number 0             Maximum number of combinations to
                                            be tried by the strategy while
                                            searching for potential candidates.
                                            To remove the limit, set it to 0
``period``             Number 7200          The time interval in seconds
                                            for getting statistic aggregation
                                            from metric data source
====================== ====== ============= ===================================

Efficacy Indicator
------------------

.. watcher-func::
  :format: literal_block

  watcher.decision_engine.goal.efficacy.specs.ServerConsolidation.get_global_efficacy_indicator

How to use it ?
---------------

.. code-block:: shell

    $ openstack optimize audittemplate create \
      at1 server_consolidation --strategy basic

    $ openstack optimize audit create -a at1 -p migration_attempts=4

External Links
--------------
None.
