 .. _user-guide:

=================================
Welcome to the Watcher User Guide
=================================

In the `architecture <https://wiki.openstack.org/wiki/WatcherArchitecture>`_ you got information about how it works.
In this guide we're going to take you through the fundamentals of using Watcher.


Getting started with Watcher
----------------------------
This guide assumes you have a working installation of Watcher. If you get "watcher: command not found" you may have to verify your installation.
Please refer to installation guide.
In order to use Watcher, you have to configure your credentials suitable for watcher command-line tools.
I you need help on a specific command, you can use "watcher help COMMAND"

Seeing what the Watcher CLI can do ?
------------------------------------
We can see all of the commands available with Watcher CLI by running the watcher binary without options.

``watcher``

How do I run an audit of my cluster ?
-------------------------------------

First, you need to create an audit template. An audit template defines an optimization goal to achieve.
This goal should be declared in the Watcher service configuration file.

``$ watcher audit-template-create my_first_audit SERVERS_CONSOLIDATION``

If you get "You must provide a username via either --os-username or via env[OS_USERNAME]" you may have to verify your credentials

Then, you can create an audit. An audit is a request for optimizing your cluster depending on the specified goal.

You can launch an audit on your cluster by referencing the audit template (i.e. the goal) that you want to use.

- Get the audit template UUID::
	``$ watcher audit-template-list``
- Start an audit based on this audit template settings::
	``$ watcher audit-create -a <your_audit_template_uuid>``


Watcher service will compute an Action Plan composed of a list of potential optimization actions according to the goal to achieve.
You can see all of the goals available in the Watcher service configuration file, section ``[watcher_strategies]``.

- Wait until the Watcher audit has produced a new action plan, and get it::
	``$ watcher action-plan-list --audit <the_audit_uuid>``

- Have a look on the list of optimization of this new action plan::
	``$ watcher action-list --action-plan <the_action_plan_uuid>``


Once you've learnt how to create an Action Plan it's time to go further by applying it to your cluster :

- Execute the action plan::
	``$ watcher action-plan-start <the_action_plan_uuid>``

You can follow the states of the actions by calling periodically ``watcher action-list``

Frequently Asked Questions
--------------------------

Under specific circumstances, you may encounter the following errors :

- Why do I get a 'Unable to establish connection to ....' error message ?

You typically get this error when one of the watcher services is not running.
You can make sure every Watcher service is running by launching the following command :
``
initctl list | grep watcher
watcher-api start/running, process 33062
watcher-decision-engine start/running, process 35511
watcher-applier start/running, process 47359
``