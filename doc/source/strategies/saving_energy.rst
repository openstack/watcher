======================
Saving Energy Strategy
======================

Synopsis
--------

**display name**: ``Saving Energy Strategy``

**goal**: ``saving_energy``

    .. watcher-term:: watcher.decision_engine.strategy.strategies.saving_energy.SavingEnergy

Requirements
------------

This feature will use Ironic to do the power on/off actions, therefore
this feature requires that the ironic component is configured.
And the compute node should be managed by Ironic.

Ironic installation: https://docs.openstack.org/ironic/latest/install/index.html

Cluster data model
******************

Default Watcher's Compute cluster data model:

    .. watcher-term:: watcher.decision_engine.model.collector.nova.NovaClusterDataModelCollector

Actions
*******

    .. list-table::
       :widths: 30 30
       :header-rows: 1

       * - action
         - description
       * - ``change_node_power_state``
         - .. watcher-term:: watcher.applier.actions.change_node_power_state.ChangeNodePowerState

Planner
*******

Default Watcher's planner:

    .. watcher-term:: watcher.decision_engine.planner.weight.WeightPlanner


Configuration
-------------

Strategy parameter is:

====================== ====== ======= ======================================
parameter              type   default          description
                              Value
====================== ====== ======= ======================================
``free_used_percent``  Number  10.0   a rational number, which describes the
                                      the quotient of
                                      min_free_hosts_num/nodes_with_VMs_num
``min_free_hosts_num`` Int      1     an int number describes minimum free
                                      compute nodes
====================== ====== ======= ======================================


Efficacy Indicator
------------------

None

Algorithm
---------

For more information on the Energy Saving Strategy please refer to:
http://specs.openstack.org/openstack/watcher-specs/specs/pike/implemented/energy-saving-strategy.html

How to use it ?
---------------
step1: Add compute nodes info into ironic node management

.. code-block:: shell

    $ ironic node-create  -d pxe_ipmitool -i ipmi_address=10.43.200.184 \
      ipmi_username=root  -i ipmi_password=nomoresecret -e compute_node_id=3

step 2: Create audit to do optimization

.. code-block:: shell

    $ openstack optimize audittemplate create \
      saving_energy_template1 saving_energy --strategy saving_energy

    $ openstack optimize audit create -a saving_energy_audit1 \
      -p free_used_percent=20.0

External Links
--------------

None
