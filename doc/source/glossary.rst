..
      Except where otherwise noted, this document is licensed under Creative
      Commons Attribution 3.0 License.  You can view the license at:

          https://creativecommons.org/licenses/by/3.0/

========
Glossary
========

.. _glossary:
   :sorted:

This page explains the different terms used in the Watcher system.

They are sorted in alphabetical order.

.. _action_definition:

Action
======

.. watcher-term:: watcher.api.controllers.v1.action

.. _action_plan_definition:

Action Plan
===========

.. watcher-term:: watcher.api.controllers.v1.action_plan

.. _administrator_definition:

Administrator
=============

The :ref:`Administrator <administrator_definition>` is any user who has admin
access on the OpenStack cluster. This user is allowed to create new projects
for tenants, create new users and assign roles to each user.

The :ref:`Administrator <administrator_definition>` usually has remote access
to any host of the cluster in order to change the configuration and restart any
OpenStack service, including Watcher.

In the context of Watcher, the :ref:`Administrator <administrator_definition>`
is a role for users which allows them to run any Watcher commands, such as:

-  Create/Delete an :ref:`Audit Template <audit_template_definition>`
-  Launch an :ref:`Audit <audit_definition>`
-  Get the :ref:`Action Plan <action_plan_definition>`
-  Launch a recommended :ref:`Action Plan <action_plan_definition>` manually
-  Archive previous :ref:`Audits <audit_definition>` and
   :ref:`Action Plans <action_plan_definition>`


The :ref:`Administrator <administrator_definition>` is also allowed to modify
any Watcher configuration files and to restart Watcher services.

.. _audit_definition:

Audit
=====

.. watcher-term:: watcher.api.controllers.v1.audit

.. _audit_template_definition:

Audit Scope
===========

An Audit Scope is a set of audited resources. Audit Scope should be defined
in each Audit Template (which contains the Audit settings).

.. _audit_scope_definition:

Audit Template
==============

.. watcher-term:: watcher.api.controllers.v1.audit_template

.. _availability_zone_definition:

Availability Zone
=================

Please, read `the official OpenStack definition of an Availability Zone <https://docs.openstack.org/nova/latest/user/aggregates.html#availability-zones-azs>`_.

.. _cluster_definition:

Cluster
=======

A :ref:`Cluster <cluster_definition>` is a set of physical machines which
provide compute, storage and networking resources and are managed by the same
OpenStack Controller node.
A :ref:`Cluster <cluster_definition>` represents a set of resources that a
cloud provider is able to offer to his/her
:ref:`customers <customer_definition>`.

A data center may contain several clusters.

The :ref:`Cluster <cluster_definition>` may be divided in one or several
:ref:`Availability Zone(s) <availability_zone_definition>`.

.. _cluster_data_model_definition:

Cluster Data Model (CDM)
========================

.. watcher-term:: watcher.decision_engine.model.collector.base


.. _controller_node_definition:

Controller Node
===============

Please, read `the official OpenStack definition of a Controller Node
<https://docs.openstack.org/nova/latest/install/overview.html#controller>`_.

In many configurations, Watcher will reside on a controller node even if it
can potentially be hosted on a dedicated machine.

.. _compute_node_definition:

Compute node
============

Please, read `the official OpenStack definition of a Compute Node
<https://docs.openstack.org/nova/latest/install/overview.html#compute>`_.

.. _customer_definition:

Customer
========

A :ref:`Customer <customer_definition>` is the person or company which
subscribes to the cloud provider offering. A customer may have several
:ref:`Project(s) <project_definition>`
hosted on the same :ref:`Cluster <cluster_definition>` or dispatched on
different clusters.

In the private cloud context, the :ref:`Customers <customer_definition>` are
different groups within the same organization (different departments, project
teams, branch offices and so on). Cloud infrastructure includes the ability to
precisely track each customer's service usage so that it can be charged back to
them, or at least reported to them.

.. _goal_definition:

Goal
====

.. watcher-term:: watcher.api.controllers.v1.goal


.. _host_aggregates_definition:

Host Aggregate
==============

Please, read `the official OpenStack definition of a Host Aggregate
<https://docs.openstack.org/nova/latest/user/aggregates.html>`_.

.. _instance_definition:

Instance
========

A running virtual machine, or a virtual machine in a known state such as
suspended, that can be used like a hardware server.

.. _managed_resource_definition:

Managed resource
================

A :ref:`Managed resource <managed_resource_definition>` is one instance of
:ref:`Managed resource type <managed_resource_type_definition>` in a topology
with particular properties and dependencies on other
:ref:`Managed resources <managed_resource_definition>` (relationships).

For example, a :ref:`Managed resource <managed_resource_definition>` can be one
virtual machine (i.e., an :ref:`instance <instance_definition>`) hosted on a
:ref:`compute node <compute_node_definition>` and connected to another virtual
machine through a network link (represented also as a
:ref:`Managed resource <managed_resource_definition>` in the
:ref:`Cluster Data Model <cluster_data_model_definition>`).

.. _managed_resource_type_definition:

Managed resource type
=====================

A :ref:`Managed resource type <managed_resource_definition>` is a type of
hardware or software element of the :ref:`Cluster <cluster_definition>` that
the Watcher system can act on.

Here are some examples of
:ref:`Managed resource types <managed_resource_definition>`:

-  `Nova Host Aggregates <https://docs.openstack.org/heat/latest/template_guide/openstack.html#OS::Nova::HostAggregate>`_
-  `Nova Servers <https://docs.openstack.org/heat/latest/template_guide/openstack.html#OS::Nova::Server>`_
-  `Cinder Volumes <https://docs.openstack.org/heat/latest/template_guide/openstack.html#OS::Cinder::Volume>`_
-  `Neutron Routers <https://docs.openstack.org/heat/latest/template_guide/openstack.html#OS::Neutron::Router>`_
-  `Neutron Networks <https://docs.openstack.org/heat/latest/template_guide/openstack.html#OS::Neutron::Net>`_
-  `Neutron load-balancers <https://docs.openstack.org/heat/latest/template_guide/openstack.html#OS::Neutron::LoadBalancer>`_
-  `Sahara Hadoop Cluster <https://docs.openstack.org/heat/latest/template_guide/openstack.html#OS::Sahara::Cluster>`_
-  ...

It can be any of `the official list of available resource types defined in
OpenStack for HEAT
<https://docs.openstack.org/heat/latest/template_guide/openstack.html>`_.

.. _efficacy_indicator_definition:

Efficacy Indicator
==================

.. watcher-term:: watcher.api.controllers.v1.efficacy_indicator

.. _efficacy_specification_definition:

Efficacy Specification
======================

.. watcher-term:: watcher.decision_engine.goal.efficacy.base

.. _efficacy_definition:

Optimization Efficacy
=====================

The :ref:`Optimization Efficacy <efficacy_definition>` is the objective
measure of how much of the :ref:`Goal <goal_definition>` has been achieved in
respect with constraints and :ref:`SLAs <sla_definition>` defined by the
:ref:`Customer <customer_definition>`.

The way efficacy is evaluated will depend on the :ref:`Goal <goal_definition>`
to achieve.

Of course, the efficacy will be relevant only as long as the
:ref:`Action Plan <action_plan_definition>` is relevant
(i.e., the current state of the :ref:`Cluster <cluster_definition>`
has not changed in a way that a new :ref:`Audit <audit_definition>` would need
to be launched).

For example, if the :ref:`Goal <goal_definition>` is to lower the energy
consumption, the :ref:`Efficacy <efficacy_definition>` will be computed
using several :ref:`efficacy indicators <efficacy_indicator_definition>`
(KPIs):

-  the percentage of energy gain (which must be the highest possible)
-  the number of :ref:`SLA violations <sla_violation_definition>`
   (which must be the lowest possible)
-  the number of virtual machine migrations (which must be the lowest possible)

All those indicators are computed within a given timeframe, which is the
time taken to execute the whole :ref:`Action Plan <action_plan_definition>`.

The efficacy also enables the :ref:`Administrator <administrator_definition>`
to objectively compare different :ref:`Strategies <strategy_definition>` for
the same goal and same workload of the :ref:`Cluster <cluster_definition>`.

.. _project_definition:

Project
=======

:ref:`Projects <project_definition>` represent the base unit of "ownership"
in OpenStack, in that all :ref:`resources <managed_resource_definition>` in
OpenStack should be owned by a specific :ref:`project <project_definition>`.
In OpenStack Identity, a :ref:`project <project_definition>` must be owned by a
specific domain.

Please, read `the official OpenStack definition of a Project
<https://docs.openstack.org/doc-contrib-guide/common/glossary.html>`_.

.. _scoring_engine_definition:

Scoring Engine
==============

.. watcher-term::  watcher.api.controllers.v1.scoring_engine

.. _sla_definition:

SLA
===

:ref:`SLA <sla_definition>` means Service Level Agreement.

The resources are negotiated between the :ref:`Customer <customer_definition>`
and the Cloud Provider in a contract.

Most of the time, this contract is composed of two documents:

-  :ref:`SLA <sla_definition>` : Service Level Agreement
-  :ref:`SLO <slo_definition>` : Service Level Objectives

Note that the :ref:`SLA <sla_definition>` is more general than the
:ref:`SLO <slo_definition>` in the sense that the former specifies what service
is to be provided, how it is supported, times, locations, costs, performance,
and responsibilities of the parties involved while the
:ref:`SLO <slo_definition>` focuses on more measurable characteristics such as
availability, throughput, frequency, response time or quality.

You can also read `the Wikipedia page for SLA <https://en.wikipedia.org/wiki/Service-level_agreement>`_
which provides a good definition.

.. _sla_violation_definition:

SLA violation
=============

A :ref:`SLA violation <sla_violation_definition>` happens when a
:ref:`SLA <sla_definition>` defined with a given
:ref:`Customer <customer_definition>` could not be respected by the
cloud provider within the timeframe defined by the official contract document.

.. _slo_definition:

SLO
===

A Service Level Objective (SLO) is a key element of a
:ref:`SLA <sla_definition>` between a service provider and a
:ref:`Customer <customer_definition>`. SLOs are agreed as a means of measuring
the performance of the Service Provider and are outlined as a way of avoiding
disputes between the two parties based on misunderstanding.

You can also read `the Wikipedia page for SLO <https://en.wikipedia.org/wiki/Service_level_objective>`_
which provides a good definition.

.. _solution_definition:

Solution
========

.. watcher-term:: watcher.decision_engine.solution.base

.. _strategy_definition:

Strategy
========

.. watcher-term::  watcher.api.controllers.v1.strategy

.. _watcher_applier_definition:

Watcher Applier
===============

.. watcher-term:: watcher.applier.base

.. _watcher_database_definition:

Watcher Database
================

This database stores all the Watcher domain objects which can be requested
by the Watcher API or the Watcher CLI:

-  Audit templates
-  Audits
-  Action plans
-  Actions
-  Goals

The Watcher domain being here "*optimization of some resources provided by an
OpenStack system*".

See :doc:`architecture` for more details on this component.

.. _watcher_decision_engine_definition:

Watcher Decision Engine
=======================

.. watcher-term::  watcher.decision_engine.manager

.. _watcher_planner_definition:

Watcher Planner
===============

.. watcher-term:: watcher.decision_engine.planner.base
