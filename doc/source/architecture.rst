.. _architecture:

===================
System Architecture
===================


This page presents the current technical Architecture of the Watcher system.

.. _architecture_overview:

Overview
========

Below you will find a diagram, showing the main components of Watcher:

.. image:: ./images/architecture.svg
   :width: 100%


.. _components_definition:

Components
==========

.. _amqp_bus_definition:

AMQP Bus
--------

The AMQP message bus handles asynchronous communications between the different
Watcher components.

.. _cluster_history_db_definition:

Cluster History Database
------------------------

This component stores the data related to the
:ref:`Cluster History <cluster_history_definition>`.

It can potentially rely on any appropriate storage system (InfluxDB, OpenTSDB,
MongoDB,...) but will probably be more performant when using
`Time Series Databases <https://en.wikipedia.org/wiki/Time_series_database>`_
which are optimized for handling time series data, which are arrays of numbers
indexed by time (a datetime or a datetime range).

.. _watcher_api_definition:

Watcher API
-----------

This component implements the REST API provided by the Watcher system to the
external world.

It enables the :ref:`Administrator <administrator_definition>` of a
:ref:`Cluster <cluster_definition>` to control and monitor the Watcher system
via any interaction mechanism connected to this API:

-   :ref:`CLI <watcher_cli_definition>`
-   Horizon plugin
-   Python SDK

You can also read the detailed description of `Watcher API`_.

.. _watcher_applier_definition:

Watcher Applier
---------------

This component is in charge of executing the :ref:`Action Plan <action_plan_definition>`
built by the :ref:`Watcher Decision Engine <watcher_decision_engine_definition>`.

It connects to the :ref:`message bus <amqp_bus_definition>` and launches the
:ref:`Action Plan <action_plan_definition>` whenever a triggering message is
received on a dedicated AMQP queue.

The triggering message contains the Action Plan UUID.

It then gets the detailed information about the
:ref:`Action Plan <action_plan_definition>` from the
:ref:`Watcher Database <watcher_database_definition>` which contains the list
of :ref:`Actions <action_definition>` to launch.

It then loops on each :ref:`Action <action_definition>`, gets the associated
class and calls the execute() method of this class.
Most of the time, this method will first request a token to the Keystone API
and if it is allowed, sends a request to the REST API of the OpenStack service
which handles this kind of :ref:`atomic Action <action_definition>`.

Note that as soon as :ref:`Watcher Applier <watcher_applier_definition>` starts
handling a given :ref:`Action <action_definition>` from the list, a
notification message is sent on the :ref:`message bus <amqp_bus_definition>`
indicating that the state of the action has changed to **ONGOING**.

If the :ref:`Action <action_definition>` is successful, the :ref:`Watcher Applier <watcher_applier_definition>`
sends a notification message on :ref:`the bus <amqp_bus_definition>` informing
the other components of this.

If the :ref:`Action <action_definition>` fails, the
:ref:`Watcher Applier <watcher_applier_definition>` tries to rollback to the
previous state of the :ref:`Managed resource <managed_resource_definition>`
(i.e. before the command was sent to the underlying OpenStack service).

.. _watcher_cli_definition:

Watcher CLI
-----------

The watcher command-line interface (CLI) can be used to interact with the
Watcher system in order to control it or to know its current status.

Please, read `the detailed documentation about Watcher CLI <https://factory.b-com.com/www/watcher/doc/python-watcherclient/>`_

.. _watcher_database_definition:

Watcher Database
----------------

This database stores all the Watcher domain objects which can be requested
by the :ref:`Watcher API <watcher_api_definition>` or the
:ref:`Watcher CLI <watcher_cli_definition>`:

-  :ref:`Audit templates <audit_template_definition>`
-  :ref:`Audits <audit_definition>`
-  :ref:`Action plans <action_plan_definition>`
-  :ref:`Actions <action_definition>`
-  :ref:`Goals <goal_definition>`

The Watcher domain being here "*optimization of some resources provided by an
OpenStack system*".

.. _watcher_decision_engine_definition:

Watcher Decision Engine
-----------------------

This component is responsible for computing a set of potential optimization
:ref:`Actions <action_definition>` in order to fulfill the :ref:`Goal <goal_definition>`
of an :ref:`Audit <audit_definition>`.

It first reads the parameters of the :ref:`Audit <audit_definition>` from the
associated :ref:`Audit Template <audit_template_definition>` and knows the
:ref:`Goal <goal_definition>` to achieve.

It then selects the most appropriate :ref:`Strategy <strategy_definition>`
depending on how Watcher was configured for this :ref:`Goal <goal_definition>`.

The :ref:`Strategy <strategy_definition>` is then dynamically loaded (via
`stevedore <https://github.com/openstack/stevedore/>`_). The
:ref:`Watcher Decision Engine <watcher_decision_engine_definition>` calls the
**execute()** method of the :ref:`Strategy <strategy_definition>` class which
generates a set of :ref:`Actions <action_definition>`.

These :ref:`Actions <action_definition>` are scheduled in time by the
:ref:`Watcher Planner <watcher_planner_definition>` (i.e., it generates an
:ref:`Action Plan <action_plan_definition>`).

In order to compute the potential :ref:`Solution <solution_definition>` for the
Audit, the :ref:`Strategy <strategy_definition>` relies on two sets of data:

-   the current state of the :ref:`Managed resources <managed_resource_definition>`
    (e.g., the data stored in the Nova database)
-   the data stored in the :ref:`Cluster History Database <cluster_history_db_definition>`
    which provides information about the past of the :ref:`Cluster <cluster_definition>`

So far, only one :ref:`Strategy <strategy_definition>` can be associated to a
given :ref:`Goal <goal_definition>` via the main Watcher configuration file.

.. _Watcher API: webapi/v1.html
