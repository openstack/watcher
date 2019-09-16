====================================
Node Resource Consolidation Strategy
====================================

Synopsis
--------

**display name**: ``Node Resource Consolidation Strategy``

**goal**: ``Server Consolidation``

    .. watcher-term:: watcher.decision_engine.strategy.strategies.node_resource_consolidation.NodeResourceConsolidation

Requirements
------------

None.

Metrics
*******

None

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

Strategy parameters are:

==================== ====== =======================================
parameter            type   default Value description
==================== ====== =======================================
``host_choice``      String The way to select the server migration
                            destination node, The value auto means
                            that Nova schedular selects the
                            destination node, and specify means
                            the strategy specifies the destination.
==================== ====== =======================================

Efficacy Indicator
------------------

None

Algorithm
---------

For more information on the Node Resource Consolidation Strategy please refer
to: https://specs.openstack.org/openstack/watcher-specs/specs/train/approved/node-resource-consolidation.html

How to use it ?
---------------

.. code-block:: shell

    $ openstack optimize audittemplate create \
      at1 server_consolidation \
      --strategy node_resource_consolidation

    $ openstack optimize audit create \
      -a at1 -p host_choice=auto

External Links
--------------

None.
