 .. _user-guide:

=================================
Welcome to the Watcher User Guide
=================================

In the `architecture <https://wiki.openstack.org/wiki/WatcherArchitecture>`_ you got information about how it works.
In this guide we're going to take you through the fundamentals of using Watcher.


Getting started with Watcher
----------------------------
This guide assumes you have a working installation of Watcher. If you get "*watcher: command not found*" you may have to verify your installation.
Please refer to installation guide.
In order to use Watcher, you have to configure your credentials suitable for watcher command-line tools.
If you need help on a specific command, you can use:

.. code:: bash

  $ watcher help COMMAND

Seeing what the Watcher CLI can do ?
------------------------------------
We can see all of the commands available with Watcher CLI by running the watcher binary without options.

.. code:: bash

  $ watcher

How do I run an audit of my cluster ?
-------------------------------------

First, you need to create an audit template. An audit template defines an optimization goal to achieve (i.e. the settings of your audit).
This goal should be declared in the Watcher service configuration file **/etc/watcher/watcher.conf**.

.. code:: bash

  $ watcher audit-template-create my_first_audit SERVERS_CONSOLIDATION

If you get "*You must provide a username via either --os-username or via env[OS_USERNAME]*" you may have to verify your credentials

Then, you can create an audit. An audit is a request for optimizing your cluster depending on the specified goal.

You can launch an audit on your cluster by referencing the audit template (i.e. the settings of your audit) that you want to use.

- Get the audit template UUID:

.. code:: bash

  $ watcher audit-template-list

- Start an audit based on this audit template settings:

.. code:: bash

  $ watcher audit-create -a <your_audit_template_uuid>


Watcher service will compute an Action Plan composed of a list of potential optimization actions (instance migration, disabling of an hypervisor, ...) according to the goal to achieve.
You can see all of the goals available in section ``[watcher_strategies]`` of the Watcher service configuration file.

- Wait until the Watcher audit has produced a new action plan, and get it:

.. code:: bash

  $ watcher action-plan-list --audit <the_audit_uuid>

- Have a look on the list of optimization actions contained in this new action plan:

.. code:: bash

  $ watcher action-list --action-plan <the_action_plan_uuid>


Once you've learned how to create an Action Plan, it's time to go further by applying it to your cluster:

- Execute the action plan:

.. code:: bash

  $ watcher action-plan-start <the_action_plan_uuid>

You can follow the states of the actions by calling periodically:

.. code:: bash

  $ watcher action-list

You can also obtain more detailed information about a specific action:

.. code:: bash

  $ watcher action-show <the_action_uuid>


