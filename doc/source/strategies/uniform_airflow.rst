==================================
Uniform Airflow Migration Strategy
==================================

Synopsis
--------

**display name**: ``Uniform airflow migration strategy``

**goal**: ``airflow_optimization``

    .. watcher-term:: watcher.decision_engine.strategy.strategies.uniform_airflow.UniformAirflow

Requirements
------------

This strategy has a dependency on the server having Intel's Power
Node Manager 3.0 or later enabled.

Metrics
*******

The *uniform_airflow* strategy requires the following metrics:

================================== ============ ======= =======
metric                             service name plugins comment
================================== ============ ======= =======
``hardware.ipmi.node.airflow``     ceilometer_  IPMI
``hardware.ipmi.node.temperature`` ceilometer_  IPMI
``hardware.ipmi.node.power``       ceilometer_  IPMI
================================== ============ ======= =======

.. _ceilometer: http://docs.openstack.org/admin-guide/telemetry-measurements.html#ipmi-based-meters

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

Strategy parameters are:

====================== ====== ============= ===========================
parameter              type   default Value description
====================== ====== ============= ===========================
``threshold_airflow``  Number 400.0         Airflow threshold for
                                            migration Unit is 0.1CFM
``threshold_inlet_t``  Number 28.0          Inlet temperature threshold
                                            for migration decision
``threshold_power``    Number 350.0         System power threshold for
                                            migration decision
``period``             Number 300           Aggregate time period of
                                            ceilometer
====================== ====== ============= ===========================

Efficacy Indicator
------------------

None

Algorithm
---------

For more information on the Uniform Airflow Migration Strategy please refer to:
https://specs.openstack.org/openstack/watcher-specs/specs/newton/implemented/uniform-airflow-migration-strategy.html

How to use it ?
---------------

.. code-block:: shell

    $ openstack optimize audittemplate create \
      at1 airflow_optimization --strategy uniform_airflow

    $ openstack optimize audit create -a at1 -p threshold_airflow=410 \
           -p threshold_inlet_t=29.0 -p threshold_power=355.0 -p period=310

External Links
--------------

- `Intel Power Node Manager 3.0 <http://www.intel.com/content/www/us/en/power-management/intelligent-power-node-manager-3-0-specification.html>`_
