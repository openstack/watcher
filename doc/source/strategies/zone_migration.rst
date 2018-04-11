==============
Zone migration
==============

Synopsis
--------

**display name**: ``Zone migration``

**goal**: ``hardware_maintenance``

    .. watcher-term:: watcher.decision_engine.strategy.strategies.zone_migration.ZoneMigration

Requirements
------------

Metrics
*******

None

Cluster data model
******************

Default Watcher's Compute cluster data model:

    .. watcher-term:: watcher.decision_engine.model.collector.nova.NovaClusterDataModelCollector

Storage cluster data model is also required:

    .. watcher-term:: watcher.decision_engine.model.collector.cinder.CinderClusterDataModelCollector

Actions
*******


Default Watcher's actions:

    .. list-table::
       :widths: 30 30
       :header-rows: 1

       * - action
         - description
       * - ``migrate``
         - .. watcher-term:: watcher.applier.actions.migration.Migrate
       * - ``volume_migrate``
         - .. watcher-term:: watcher.applier.actions.volume_migration.VolumeMigrate

Planner
*******

Default Watcher's planner:

    .. watcher-term:: watcher.decision_engine.planner.weight.WeightPlanner

Configuration
-------------

Strategy parameters are:

======================== ======== ============= ==============================
parameter                type     default Value description
======================== ======== ============= ==============================
``compute_nodes``        array    None          Compute nodes to migrate.
``storage_pools``        array    None          Storage pools to migrate.
``parallel_total``       integer  6             The number of actions to be
                                                run in parallel in total.
``parallel_per_node``    integer  2             The number of actions to be
                                                run in parallel per compute
                                                node.
``parallel_per_pool``    integer  2             The number of actions to be
                                                run in parallel per storage
                                                pool.
``priority``             object   None          List prioritizes instances
                                                and volumes.
``with_attached_volume`` boolean  False         False: Instances will migrate
                                                after all volumes migrate.
                                                True: An instance will migrate
                                                after the attached volumes
                                                migrate.
======================== ======== ============= ==============================

The elements of compute_nodes array are:

============= ======= =============== =============================
parameter     type    default Value   description
============= ======= =============== =============================
``src_node``  string    None          Compute node from which
                                      instances migrate(mandatory).
``dst_node``  string    None          Compute node to which
                                      instances migrate.
============= ======= =============== =============================

The elements of storage_pools array are:

============= ======= =============== ==============================
parameter     type    default Value   description
============= ======= =============== ==============================
``src_pool``  string    None          Storage pool from which
                                      volumes migrate(mandatory).
``dst_pool``  string    None          Storage pool to which
                                      volumes migrate.
``src_type``  string    None          Source volume type(mandatory).
``dst_type``  string    None          Destination volume type
                                      (mandatory).
============= ======= =============== ==============================

The elements of priority object are:

================ ======= =============== ======================
parameter        type    default Value   description
================ ======= =============== ======================
``project``      array   None            Project names.
``compute_node`` array   None            Compute node names.
``storage_pool`` array   None            Storage pool names.
``compute``      enum    None            Instance attributes.
                                         |compute|
``storage``      enum    None            Volume attributes.
                                         |storage|
================ ======= =============== ======================

.. |compute| replace:: ["vcpu_num", "mem_size", "disk_size", "created_at"]
.. |storage| replace:: ["size", "created_at"]

Efficacy Indicator
------------------

.. watcher-func::
  :format: literal_block

  watcher.decision_engine.goal.efficacy.specs.HardwareMaintenance.get_global_efficacy_indicator

Algorithm
---------

For more information on the zone migration strategy please refer
to: http://specs.openstack.org/openstack/watcher-specs/specs/queens/implemented/zone-migration-strategy.html

How to use it ?
---------------

.. code-block:: shell

    $ openstack optimize audittemplate create \
      at1 hardware_maintenance --strategy zone_migration

    $ openstack optimize audit create -a at1 \
      -p compute_nodes='[{"src_node": "s01", "dst_node": "d01"}]'

External Links
--------------

None
