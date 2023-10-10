=============================================
Watcher Overload standard deviation algorithm
=============================================

Synopsis
--------

**display name**: ``Workload stabilization``

**goal**: ``workload_balancing``

    .. watcher-term:: watcher.decision_engine.strategy.strategies.workload_stabilization.WorkloadStabilization

Requirements
------------

Metrics
*******

The *workload_stabilization* strategy requires the following metrics:

============================ ============ ======= =============================
metric                       service name plugins comment
============================ ============ ======= =============================
``compute.node.cpu.percent`` ceilometer_  none    need to set the
                                                  ``compute_monitors`` option
                                                  to ``cpu.virt_driver`` in the
                                                  nova.conf.
``hardware.memory.used``     ceilometer_  SNMP_
``cpu``                      ceilometer_  none
``instance_ram_usage``       ceilometer_  none
============================ ============ ======= =============================

.. _ceilometer: https://docs.openstack.org/ceilometer/latest/admin/telemetry-measurements.html#openstack-compute
.. _SNMP: https://docs.openstack.org/ceilometer/latest/admin/telemetry-measurements.html#snmp-based-meters

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

==================== ====== ===================== =============================
parameter            type   default Value         description
==================== ====== ===================== =============================
``metrics``          array  |metrics|             Metrics used as rates of
                                                  cluster loads.
``thresholds``       object |thresholds|          Dict where key is a metric
                                                  and value is a trigger value.

``weights``          object |weights|             These weights used to
                                                  calculate common standard
                                                  deviation. Name of weight
                                                  contains meter name and
                                                  _weight suffix.
``instance_metrics`` object |instance_metrics|    Mapping to get hardware
                                                  statistics using instance
                                                  metrics.
``host_choice``      string retry                 Method of host's choice.
                                                  There are cycle, retry and
                                                  fullsearch methods. Cycle
                                                  will iterate hosts in cycle.
                                                  Retry will get some hosts
                                                  random (count defined in
                                                  retry_count option).
                                                  Fullsearch will return each
                                                  host from list.
``retry_count``      number 1                     Count of random returned
                                                  hosts.
``periods``          object |periods|             These periods are used to get
                                                  statistic aggregation for
                                                  instance and host metrics.
                                                  The period is simply a
                                                  repeating interval of time
                                                  into which the samples are
                                                  grouped for aggregation.
                                                  Watcher uses only the last
                                                  period of all received ones.
==================== ====== ===================== =============================

.. |metrics| replace:: ["instance_cpu_usage", "instance_ram_usage"]
.. |thresholds| replace:: {"instance_cpu_usage": 0.2, "instance_ram_usage": 0.2}
.. |weights| replace:: {"instance_cpu_usage_weight": 1.0, "instance_ram_usage_weight": 1.0}
.. |instance_metrics| replace:: {"instance_cpu_usage": "compute.node.cpu.percent", "instance_ram_usage": "hardware.memory.used"}
.. |periods| replace:: {"instance": 720, "node": 600}

Efficacy Indicator
------------------

.. watcher-func::
  :format: literal_block

  watcher.decision_engine.goal.efficacy.specs.ServerConsolidation.get_global_efficacy_indicator

Algorithm
---------

You can find description of overload algorithm and role of standard deviation
here: https://specs.openstack.org/openstack/watcher-specs/specs/newton/implemented/sd-strategy.html

How to use it ?
---------------

.. code-block:: shell

    $ openstack optimize audittemplate create \
      at1 workload_balancing --strategy workload_stabilization

    $ openstack optimize audit create -a at1 \
      -p thresholds='{"instance_ram_usage": 0.05}' \
      -p metrics='["instance_ram_usage"]'

External Links
--------------

- `Watcher Overload standard deviation algorithm spec <https://specs.openstack.org/openstack/watcher-specs/specs/newton/implemented/sd-strategy.html>`_
