=================================
Outlet Temperature Based Strategy
=================================

Synopsis
--------

**display name**: ``Outlet temperature based strategy``

**goal**: ``thermal_optimization``

    .. watcher-term:: watcher.decision_engine.strategy.strategies.outlet_temp_control

Requirements
------------

This strategy has a dependency on the host having Intel's Power
Node Manager 3.0 or later enabled.


Metrics
*******

The *outlet_temperature* strategy requires the following metrics:

========================================= ============ ======= =======
metric                                    service name plugins comment
========================================= ============ ======= =======
``hardware.ipmi.node.outlet_temperature`` ceilometer_  IPMI
========================================= ============ ======= =======

.. _ceilometer: https://docs.openstack.org/ceilometer/latest/admin/telemetry-measurements.html#ipmi-based-meters

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

    .. watcher-term:: watcher.decision_engine.planner.weight.WeightPlanner

Configuration
-------------

Strategy parameter is:

============== ====== ============= ====================================
parameter      type   default Value description
============== ====== ============= ====================================
``threshold``  Number 35.0          Temperature threshold for migration
``period``     Number 30            The time interval in seconds for
                                    getting statistic aggregation from
                                    metric data source
============== ====== ============= ====================================

Efficacy Indicator
------------------

None

Algorithm
---------

For more information on the Outlet Temperature Based Strategy please refer to:
https://specs.openstack.org/openstack/watcher-specs/specs/mitaka/implemented/outlet-temperature-based-strategy.html

How to use it ?
---------------

.. code-block:: shell

    $ openstack optimize audittemplate create \
      at1 thermal_optimization --strategy outlet_temperature

    $ openstack optimize audit create -a at1 -p threshold=31.0

External Links
--------------

- `Intel Power Node Manager 3.0 <http://www.intel.com/content/www/us/en/power-management/intelligent-power-node-manager-3-0-specification.html>`_
