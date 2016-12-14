===================================
Workload Balance Migration Strategy
===================================

Synopsis
--------

**display name**: ``workload_balance``

**goal**: ``workload_balancing``

.. watcher-term:: watcher.decision_engine.strategy.strategies.workload_balance

Requirements
------------

None.

Metrics
*******

The *workload_balance* strategy requires the following metrics:

======================= ============ ======= =======
metric                  service name plugins comment
======================= ============ ======= =======
``cpu_util``            ceilometer_  none
======================= ============ ======= =======

.. _ceilometer: http://docs.openstack.org/admin-guide/telemetry-measurements.html#openstack-compute


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

Planner
*******

Default Watcher's planner:

    .. watcher-term:: watcher.decision_engine.planner.default.DefaultPlanner

Configuration
-------------

Strategy parameters are:

============== ====== ============= ====================================
parameter      type   default Value description
============== ====== ============= ====================================
``threshold``  Number 25.0          Workload threshold for migration
``period``     Number 300           Aggregate time period of ceilometer
============== ====== ============= ====================================

Efficacy Indicator
------------------

None

Algorithm
---------

For more information on the Workload Balance Migration Strategy please refer
to: https://specs.openstack.org/openstack/watcher-specs/specs/mitaka/implemented/workload-balance-migration-strategy.html

How to use it ?
---------------

.. code-block:: shell

    $ openstack optimize audittemplate create \
      at1 workload_balancing --strategy workload_balance

    $ openstack optimize audit create -a at1 -p threshold=26.0 \
            -p period=310

External Links
--------------

None.
