==============
Zone migration
==============

Synopsis
--------

**display name**: ``Zone migration``

**goal**: ``hardware_maintenance``

    .. watcher-term:: watcher.decision_engine.strategy.strategies.zone_migration.ZoneMigration

.. note::
   The term ``Zone`` in the strategy name is not a reference to
   `Openstack availability zones <https://docs.openstack.org/nova/latest/admin/availability-zones.html>`_
   but rather a user-defined set of Compute nodes and storage pools.
   Currently, migrations across actual availability zones is not fully tested
   and might not work in all cluster configurations.

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

======================== ======== ======== ========= ==========================
parameter                type     default  required  description
======================== ======== ======== ========= ==========================
``compute_nodes``        array    None     Optional  Compute nodes to migrate.
``storage_pools``        array    None     Optional  Storage pools to migrate.
``parallel_total``       integer  6        Optional  The number of actions to
                                                     be run in parallel in
                                                     total.
``parallel_per_node``    integer  2        Optional  The number of actions to
                                                     be run in parallel per
                                                     compute node in one
                                                     action plan.
``parallel_per_pool``    integer  2        Optional  The number of actions to
                                                     be run in parallel per
                                                     storage pool.
``priority``             object   None     Optional  List prioritizes instances
                                                     and volumes.
``with_attached_volume`` boolean  False    Optional  False: Instances will
                                                     migrate after all volumes
                                                     migrate.
                                                     True: An instance will
                                                     migrate after the
                                                     attached volumes migrate.
======================== ======== ======== ========= ==========================

.. note::
   * All parameters in the table above have defaults and therefore the
     user can create an audit without specifying a value. However,
     if **only** defaults parameters are used, there will be nothing
     actionable for the audit.
   * ``parallel_*`` parameters are not in reference to concurrency,
     but rather on limiting the amount of actions to be added to the action
     plan
   * ``compute_nodes``, ``storage_pools``, and ``priority`` are optional
     parameters, however, if they are passed they **require** the parameters
     in the tables below:

The elements of compute_nodes array are:

============= ======= ======== ========= ========================
parameter     type    default  required  description
============= ======= ======== ========= ========================
``src_node``  string  None     Required  Compute node from which
                                         instances migrate.
``dst_node``  string  None     Optional  Compute node to which
                                         instances migrate.
                                         If omitted, nova will
                                         choose the destination
                                         node automatically.
============= ======= ======== ========= ========================

The elements of storage_pools array are:

============= ======= ======== ========= ========================
parameter     type    default  required  description
============= ======= ======== ========= ========================
``src_pool``  string  None     Required  Storage pool from which
                                         volumes migrate.
``dst_pool``  string  None     Optional  Storage pool to which
                                         volumes migrate.
``src_type``  string  None     Optional  Source volume type.
``dst_type``  string  None     Required  Destination volume type
============= ======= ======== ========= ========================

The elements of priority object are:

================ ======= ======== ========= =====================
parameter        type    default  Required  description
================ ======= ======== ========= =====================
``project``      array   None     Optional  Project names.
``compute_node`` array   None     Optional  Compute node names.
``storage_pool`` array   None     Optional  Storage pool names.
``compute``      enum    None     Optional  Instance attributes.
                                            |compute|
``storage``      enum    None     Optional  Volume attributes.
                                            |storage|
================ ======= ======== ========= =====================

.. |compute| replace:: ["vcpu_num", "mem_size", "disk_size", "created_at"]
.. |storage| replace:: ["size", "created_at"]

Efficacy Indicator
------------------

The efficacy indicators for action plans built from the command line
are:

.. watcher-func::
  :format: literal_block

  watcher.decision_engine.goal.efficacy.specs.HardwareMaintenance.get_global_efficacy_indicator

In **Horizon**, these indictors are shown with alternative text.

* ``live_migrate_instance_count`` is shown as
  ``The number of instances actually live migrated`` in Horizon
* ``planned_live_migrate_instance_count`` is  shown as
  ``The number of instances planned to live migrate`` in Horizon
* ``planned_live_migration_instance_count`` refers to the instances planned
  to live migrate in the action plan.
* ``live_migrate_instance_count`` tracks all the instances that could be
  migrated according to the audit input.


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

.. note::
   * Currently, the strategy will not generate both volume migration and
     instance migrations in the same audit. If both are requested,
     only volume migrations will be included in the action plan.
   * The Cinder model collector is not enabled by default.
     If the Cinder model collector is not enabled while deploying Watcher,
     the model will become outdated and cause errors eventually.
     See the `Configuration option to enable the storage collector <https://docs.openstack.org/watcher/latest/configuration/watcher.html#collector.collector_plugins>`_ documentation.

Support caveats
---------------

This strategy offers the option to perform both Instance migrations and
Volume migrations. Currently, Instance migrations are ready for production
use while Volume migrations remain experimental.

External Links
--------------

None
