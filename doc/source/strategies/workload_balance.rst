===================================
Workload Balance Migration Strategy
===================================

Synopsis
--------

**display name**: ``Workload Balance Migration Strategy``

**goal**: ``workload_balancing``

    .. watcher-term:: watcher.decision_engine.strategy.strategies.workload_balance.WorkloadBalance

Metrics
*******

The ``workload_balance`` strategy requires the following metrics:

======================= ============ ======= =========== ======================
metric                  service name plugins unit        comment
======================= ============ ======= =========== ======================
``cpu``                 ceilometer_  none    percentage  CPU of the instance.
                                                         Used to calculate the
                                                         threshold
``memory.resident``     ceilometer_  none    MB          RAM of the instance.
                                                         Used to calculate the
                                                         threshold
======================= ============ ======= =========== ======================

.. _ceilometer: https://docs.openstack.org/ceilometer/latest/admin/telemetry-measurements.html#openstack-compute

.. note::
   * The parameters above reference the instance CPU or RAM usage, but
     the threshold calculation is based of the CPU/RAM usage on the
     hypervisor.
   * The RAM usage can be calculated based on the RAM consumed by the instance,
     and the available RAM on the hypervisor.
   * The CPU percentage calculation relies on the CPU load, but also on the
     number of CPUs on the hypervisor.
   * The host memory metric is calculated by summing the RAM usage of each
     instance on the host. This measure is close to the real usage, but is
     not the exact usage on the host.

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

================ ====== ==================== ==================================
parameter        type   default value        description
================ ====== ==================== ==================================
``metrics``      String instance_cpu_usage   Workload balance base on cpu or
                                             ram utilization. Choices:
                                             ['instance_cpu_usage',
                                             'instance_ram_usage']
``threshold``    Number 25.0                 Workload threshold for migration.
                                             Used for both the source and the
                                             destination calculations.
                                             Threshold is always a percentage.
``period``       Number 300                  Aggregate time period of
                                             ceilometer
``granularity``  Number 300                  The time between two measures in
                                             an aggregated timeseries of a
                                             metric.
                                             This parameter is only used
                                             with the Gnocchi data source,
                                             and it must match to any of the
                                             valid archive policies for the
                                             metric.
================ ====== ==================== ==================================

Efficacy Indicator
------------------

None

Algorithm
---------

For more information on the Workload Balance Migration Strategy please refer
to: https://specs.openstack.org/openstack/watcher-specs/specs/mitaka/implemented/workload-balance-migration-strategy.html

How to use it ?
---------------

Create an audit template using the Workload Balancing strategy.

.. code-block:: shell

    $ openstack optimize audittemplate create \
      at1 workload_balancing --strategy workload_balance

Run an audit using the Workload Balance strategy. The result of
the audit should be an action plan to move VMs from any host
where the CPU usage is over the threshold of 26%, to a host
where the utilization of CPU is under the threshold.
The measurements of CPU utilization are taken from the configured
datasouce plugin with an aggregate period of 310.

.. code-block:: shell

    $ openstack optimize audit create -a at1 -p threshold=26.0 \
            -p period=310 -p metrics=instance_cpu_usage

Run an audit using the Workload Balance strategy to
obtain a plan to balance VMs over hosts with a threshold of 20%.
In this case, the stipulation of the CPU utilization metric
measurement is a combination of period and granularity.

.. code-block:: shell

    $ openstack optimize audit create -a at1 \
           -p granularity=30 -p threshold=20 -p period=300 \
           -p metrics=instance_cpu_usage --auto-trigger

External Links
--------------

None.
