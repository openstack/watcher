========================
Storage capacity balance
========================

Synopsis
--------

**display name**: ``Storage Capacity Balance Strategy``

**goal**: ``workload_balancing``

    .. watcher-term:: watcher.decision_engine.strategy.strategies.storage_capacity_balance.StorageCapacityBalance

Requirements
------------

Metrics
*******

None

Cluster data model
******************

Storage cluster data model is required:

    .. watcher-term:: watcher.decision_engine.model.collector.cinder.CinderClusterDataModelCollector

Actions
*******

Default Watcher's actions:

    .. list-table::
       :widths: 25 35
       :header-rows: 1

       * - action
         - description
       * - ``volume_migrate``
         - .. watcher-term:: watcher.applier.actions.volume_migration.VolumeMigrate

Planner
*******

Default Watcher's planner:

    .. watcher-term:: watcher.decision_engine.planner.weight.WeightPlanner

Configuration
-------------

Strategy parameter is:

==================== ====== ============= =====================================
parameter            type   default       Value description
==================== ====== ============= =====================================
``volume_threshold`` Number 80.0          Volume threshold for capacity balance
==================== ====== ============= =====================================


Efficacy Indicator
------------------

None

Algorithm
---------

For more information on the storage capacity balance strategy please refer to:
http://specs.openstack.org/openstack/watcher-specs/specs/queens/implemented/storage-capacity-balance.html

How to use it ?
---------------

.. code-block:: shell

    $ openstack optimize audittemplate create \
      at1 workload_balancing --strategy storage_capacity_balance

    $ openstack optimize audit create -a at1 \
      -p volume_threshold=85.0

External Links
--------------

None
