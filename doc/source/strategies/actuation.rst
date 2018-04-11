=============
Actuator
=============

Synopsis
--------

**display name**: ``Actuator``

**goal**: ``unclassified``

    .. watcher-term:: watcher.decision_engine.strategy.strategies.actuation.Actuator

Requirements
------------

Metrics
*******

None

Cluster data model
******************

None

Actions
*******

Default Watcher's actions.

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
``actions``          array  None                  Actions to be executed.
==================== ====== ===================== =============================

The elements of actions array are:

==================== ====== ===================== =============================
parameter            type   default Value         description
==================== ====== ===================== =============================
``action_type``      string None                  Action name defined in
                                                  setup.cfg(mandatory)
``resource_id``      string None                  Resource_id of the action.
``input_parameters`` object None                  Input_parameters of the
                                                  action(mandatory).
==================== ====== ===================== =============================

Efficacy Indicator
------------------

None

Algorithm
---------

This strategy create an action plan with a predefined set of actions.

How to use it ?
---------------

.. code-block:: shell

    $ openstack optimize audittemplate create \
      at1 unclassified --strategy actuator

    $ openstack optimize audit create -a at1 \
      -p actions='[{"action_type": "migrate", "resource_id": "56a40802-6fde-4b59-957c-c84baec7eaed", "input_parameters": {"migration_type": "live", "source_node": "s01"}}]'

External Links
--------------

None
