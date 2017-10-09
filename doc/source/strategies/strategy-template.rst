=============
Strategy name
=============

Synopsis
--------

**display name**:

**goal**:

Add here a complete description of your strategy

Requirements
------------

Metrics
*******

Write here the list of metrics required by your strategy algorithm (in the form
 of a table). If these metrics requires specific Telemetry plugin or other
 additional software, please explain here how to deploy them (and add link to
 dedicated installation guide).

Example:

======================= ============ ======= =======
metric                  service name plugins comment
======================= ============ ======= =======
compute.node.*          ceilometer_  none    one point every 60s
vm.cpu.utilization_perc monasca_     none
power                   ceilometer_  kwapi_  one point every 60s
======================= ============ ======= =======


.. _ceilometer: https://docs.openstack.org/ceilometer/latest/admin/telemetry-measurements.html#openstack-compute
.. _monasca: https://github.com/openstack/monasca-agent/blob/master/docs/Libvirt.md
.. _kwapi: https://kwapi.readthedocs.io/en/latest/index.html


Cluster data model
******************

Default Watcher's cluster data model.

or

If your strategy implementation requires a new cluster data model, please
 describe it in this section, with a link to model plugin's installation guide.

Actions
*******

Default Watcher's actions.

or

If your strategy implementation requires new actions, add the list of Action
 plugins here (in the form of a table) with a link to the plugin's installation
 procedure.

======== =================
action   description
======== =================
action1_ This action1 ...
action2_ This action2 ...
======== =================

.. _action1 : https://github.com/myrepo/watcher/plugins/action1
.. _action2 : https://github.com/myrepo/watcher/plugins/action2

Planner
*******

Default Watcher's planner.

or

If your strategy requires also a new planner to schedule built actions in time,
 please describe it in this section, with a link to planner plugin's
 installation guide.

Configuration
-------------

If your strategy use configurable parameters, explain here how to tune them.


Efficacy Indicator
------------------

Add here the Efficacy indicator computed by your strategy.

Algorithm
---------

Add here either the description of your algorithm or
link to the existing description.

How to use it ?
---------------

.. code-block:: shell

    $ Write the command line to create an audit with your strategy.

External Links
--------------

If you have written papers, blog articles .... about your strategy into Watcher,
 or if your strategy is based from external publication(s), please add HTTP
 links and references in this section.

- `link1 <http://www.link1.papers.com>`_
- `link2 <http://www.link2.papers.com>`_
