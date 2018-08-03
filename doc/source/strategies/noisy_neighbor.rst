==============
Noisy neighbor
==============

Synopsis
--------

**display name**: ``Noisy Neighbor``

**goal**: ``noisy_neighbor``

    .. watcher-term:: watcher.decision_engine.strategy.strategies.noisy_neighbor.NoisyNeighbor

Requirements
------------

Metrics
*******

The *noisy_neighbor* strategy requires the following metrics:

============================ ============ ======= =======================
metric                       service name plugins comment
============================ ============ ======= =======================
``cpu_l3_cache``             ceilometer_  none     Intel CMT_ is required
============================ ============ ======= =======================

.. _CMT: http://www.intel.com/content/www/us/en/architecture-and-technology/resource-director-technology.html
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

Planner
*******

Default Watcher's planner:

    .. watcher-term:: watcher.decision_engine.planner.weight.WeightPlanner

Configuration
-------------

Strategy parameter is:

==================== ====== ============= ============================
parameter            type   default       Value description
==================== ====== ============= ============================
``cache_threshold``  Number 35.0          Performance drop in L3_cache
                                          threshold for migration
==================== ====== ============= ============================


Efficacy Indicator
------------------

None

Algorithm
---------

For more information on the noisy neighbor strategy please refer to:
http://specs.openstack.org/openstack/watcher-specs/specs/pike/implemented/noisy_neighbor_strategy.html

How to use it ?
---------------

.. code-block:: shell

    $ openstack optimize audittemplate create \
      at1 noisy_neighbor --strategy noisy_neighbor

    $ openstack optimize audit create -a at1 \
      -p cache_threshold=45.0

External Links
--------------

None
