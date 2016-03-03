..
      Except where otherwise noted, this document is licensed under Creative
      Commons Attribution 3.0 License.  You can view the license at:

          https://creativecommons.org/licenses/by/3.0/

.. _user-guide:

==================
Watcher User Guide
==================

See the
`architecture page <https://factory.b-com.com/www/watcher/doc/watcher/architecture.html>`_
for an architectural overview of the different components of Watcher and how
they fit together.

In this guide we're going to take you through the fundamentals of using
Watcher.

The following diagram shows the main interactions between the
:ref:`Administrator <administrator_definition>` and the Watcher system:

.. image:: ../images/sequence_overview_watcher_usage.png
   :width: 100%


Getting started with Watcher
----------------------------
This guide assumes you have a working installation of Watcher. If you get
"*watcher: command not found*" you may have to verify your installation.
Please refer to the `installation guide`_.
In order to use Watcher, you have to configure your credentials suitable for
watcher command-line tools.
If you need help on a specific command, you can use:

.. code:: bash

  $ watcher help COMMAND

If you want to deploy Watcher in Horizon, please refer to the `Watcher Horizon
plugin installation guide`_.

.. _`installation guide`: https://factory.b-com.com/www/watcher/doc/python-watcherclient
.. _`Watcher Horizon plugin installation guide`: https://factory.b-com.com/www/watcher/doc/watcher-dashboard/deploy/installation.html

Seeing what the Watcher CLI can do ?
------------------------------------
We can see all of the commands available with Watcher CLI by running the
watcher binary without options.

.. code:: bash

  $ watcher

How do I run an audit of my cluster ?
-------------------------------------

First, you need to create an :ref:`audit template <audit_template_definition>`.
An :ref:`audit template <audit_template_definition>` defines an optimization
:ref:`goal <goal_definition>` to achieve (i.e. the settings of your audit).
This goal should be declared in the Watcher service configuration file
**/etc/watcher/watcher.conf**.

.. code:: bash

  $ watcher audit-template-create my_first_audit DUMMY

If you get "*You must provide a username via either --os-username or via
env[OS_USERNAME]*" you may have to verify your credentials.

Then, you can create an audit. An audit is a request for optimizing your
cluster depending on the specified :ref:`goal <goal_definition>`.

You can launch an audit on your cluster by referencing the
:ref:`audit template <audit_template_definition>` (i.e. the settings of your
audit) that you want to use.

- Get the :ref:`audit template <audit_template_definition>` UUID:

.. code:: bash

  $ watcher audit-template-list

- Start an audit based on this :ref:`audit template
  <audit_template_definition>` settings:

.. code:: bash

  $ watcher audit-create -a <your_audit_template_uuid>


Watcher service will compute an :ref:`Action Plan <action_plan_definition>`
composed of a list of potential optimization :ref:`actions <action_definition>`
(instance migration, disabling of an hypervisor, ...) according to the
:ref:`goal <goal_definition>` to achieve. You can see all of the goals
available in section ``[watcher_strategies]`` of the Watcher service
configuration file.

- Wait until the Watcher audit has produced a new :ref:`action plan
  <action_plan_definition>`, and get it:

.. code:: bash

  $ watcher action-plan-list --audit <the_audit_uuid>

- Have a look on the list of optimization :ref:`actions <action_definition>`
  contained in this new :ref:`action plan <action_plan_definition>`:

.. code:: bash

  $ watcher action-list --action-plan <the_action_plan_uuid>


Once you have learned how to create an :ref:`Action Plan
<action_plan_definition>`, it's time to go further by applying it to your
cluster:

- Execute the :ref:`action plan <action_plan_definition>`:

.. code:: bash

  $ watcher action-plan-start <the_action_plan_uuid>

You can follow the states of the :ref:`actions <action_definition>` by
periodically calling:

.. code:: bash

  $ watcher action-list

You can also obtain more detailed information about a specific action:

.. code:: bash

  $ watcher action-show <the_action_uuid>

