===========
Concurrency
===========

Introduction
************

Modern processors typically contain multiple cores all capable of executing
instructions in parallel. Ensuring applications can fully utilize modern
underlying hardware requires developing with these concepts in mind. The
OpenStack foundation maintains a number of libraries to facilitate this
utilization, combined with constructs like CPython's GIL_ the proper use of
these concepts becomes more straightforward compared to other programming
languages.

The primary libraries maintained by OpenStack to facilitate concurrency are
futurist_ and taskflow_. Here futurist is a more straightforward and
lightweight library while taskflow is more advanced supporting features like
rollback mechanisms. Within Watcher both libraries are used to facilitate
concurrency.

.. _GIL: https://wiki.python.org/moin/GlobalInterpreterLock
.. _futurist: https://docs.openstack.org/futurist/latest/
.. _taskflow: https://docs.openstack.org/taskflow/latest/

Threadpool
**********

A threadpool is a collection of one or more threads typically called *workers*
to which tasks can be submitted. These submitted tasks will be scheduled by a
threadpool and subsequently executed. In the case of Python tasks typically are
bounded or unbounded methods while other programming languages like Java
require implementing an interface.

The order and amount of concurrency with which these tasks are executed is up
to the threadpool to decide. Some libraries like taskflow allow for either
strong or loose ordering of tasks while others like futurist might only support
loose ordering. Taskflow supports building tree-based hierarchies of dependent
tasks for example.

Upon submission of a task to a threadpool a so called future_ is returned.
These objects allow to determine information about the task such as if it is
currently being executed or if it has finished execution. When the task has
finished execution the future can also be used to retrieve what was returned by
the method.

Some libraries like futurist provide synchronization primitives for collections
of futures such as wait_for_any_. The following sections will cover different
types of concurrency used in various services of Watcher.

.. _future: https://docs.python.org/3/library/concurrent.futures.html
.. _wait_for_any: https://docs.openstack.org/futurist/latest/reference/index.html#waiters


Decision engine concurrency
***************************

The concurrency in the decision engine is governed by two independent
threadpools. Both of these threadpools are GreenThreadPoolExecutor_ from the
futurist_ library. One of these is used automatically and most contributors
will not interact with it while developing new features. The other threadpool
can frequently be used while developing new features or updating existing ones.
It is known as the DecisionEngineThreadpool and allows to achieve performance
improvements in network or I/O bound operations.

.. _GreenThreadPoolExecutor: https://docs.openstack.org/futurist/latest/reference/index.html#executors

AuditEndpoint
#############

The first threadpool is used to allow multiple audits to be run in parallel.
In practice, however, only one audit can be run in parallel. This is due to
the data model used by audits being a singleton. To prevent audits destroying
each others data model one must wait for the other to complete before being
allowed to access this data model. A performance improvement could be achieved
by being more intelligent in the use, caching and construction of these
data models.

DecisionEngineThreadPool
########################

The second threadpool is used for generic tasks, typically networking and I/O
could benefit the most of this threadpool. Upon execution of an audit this
threadpool can be utilized to retrieve information from the Nova compute
service for instance. This second threadpool is a singleton and is shared
amongst concurrently running audits as a result the amount of workers is static
and independent from the amount of workers in the first threadpool. The use of
the :class:`~.DecisionEngineThreadpool` while building the Nova compute data
model is demonstrated to show how it can effectively be used.

In the following example a reference to the
:class:`~.DecisionEngineThreadpool` is stored in ``self.executor``. Here two
tasks are submitted one with function ``self._collect_aggregates`` and the
other function ``self._collect_zones``. With both ``self.executor.submit``
calls subsequent arguments are passed to the function. All subsequent arguments
are passed to the function being submitted as task following the common
``(fn, *args, **kwargs)`` signature. One of the original signatures would be
``def _collect_aggregates(host_aggregates, compute_nodes)`` for example.

.. code-block:: python

    zone_aggregate_futures = {
        self.executor.submit(
            self._collect_aggregates, host_aggregates, compute_nodes),
        self.executor.submit(
            self._collect_zones, availability_zones, compute_nodes)
    }
    waiters.wait_for_all(zone_aggregate_futures)

The last statement of the example above waits on all futures to complete.
Similarly, ``waiters.wait_for_any`` will wait for any future of the specified
collection to complete. To simplify the usage of ``wait_for_any`` the
:class:`~.DecisiongEngineThreadpool` defines a ``do_while_futures`` method.
This method will iterate in a do_while loop over a collection of futures until
all of them have completed. The advantage of ``do_while_futures`` is that it
allows to immediately call a method as soon as a future finishes. The arguments
for this callback method can be supplied when calling ``do_while_futures``,
however, the first argument to the callback is always the future itself! If
the collection of futures can safely be modified ``do_while_futures_modify``
can be used and should have slightly better performance. The following example
will show how ``do_while_futures`` is used in the decision engine.

.. code-block:: python

    # For every compute node from compute_nodes submit a task to gather the node it's information.
    # List comprehension is used to store all the futures of the submitted tasks in node_futures.
    node_futures = [self.executor.submit(
        self.nova_helper.get_compute_node_by_name,
        node, servers=True, detailed=True)
        for node in compute_nodes]
    LOG.debug("submitted {0} jobs".format(len(compute_nodes)))

    future_instances = []
    # do_while iterate over node_futures and upon completion of a future call
    # self._compute_node_future with the future and future_instances as arguments.
    self.executor.do_while_futures_modify(
        node_futures, self._compute_node_future, future_instances)

    # Wait for all instance jobs to finish
    waiters.wait_for_all(future_instances)

Finally, let's demonstrate how powerful this ``do_while_futures`` can be by
showing what the ``compute_node_future`` callback does. First, it retrieves the
result from the future and adds the compute node to the data model. Afterwards,
it checks if the compute node has any associated instances and if so it submits
an additional task to the :class:`~.DecisionEngineThreadpool`. The future is
appended to the ``future_instances`` so ``waiters.wait_for_all`` can be called
on this list. This is important as otherwise the building of the data model
might return before all tasks for instances have finished.

.. code-block:: python

    # Get the result from the future.
    node_info = future.result()[0]

    # Filter out baremetal nodes.
    if node_info.hypervisor_type == 'ironic':
        LOG.debug("filtering out baremetal node: %s", node_info)
        return

    # Add the compute node to the data model.
    self.add_compute_node(node_info)
    # Get the instances from the compute node.
    instances = getattr(node_info, "servers", None)
    # Do not submit job if there are no instances on compute node.
    if instances is None:
        LOG.info("No instances on compute_node: {0}".format(node_info))
        return
    # Submit a job to retrieve detailed information about the instances.
    future_instances.append(
        self.executor.submit(
            self.add_instance_node, node_info, instances)
    )

Without ``do_while_futures`` an additional ``waiters.wait_for_all`` would be
required in between the compute node tasks and the instance tasks. This would
cause the progress of the decision engine to stall as less and less tasks
remain active before the instance tasks could be submitted. This demonstrates
how ``do_while_futures`` can be used to achieve more constant utilization of
the underlying hardware.

Applier concurrency
*******************

The applier does not use the futurist_ GreenThreadPoolExecutor_ directly but
instead uses taskflow_. However, taskflow still utilizes a greenthreadpool.
This threadpool is initialized in the workflow engine called
:class:`~.DefaultWorkFlowEngine`. Currently Watcher supports one workflow
engine but the base class allows contributors to develop other workflow engines
as well. In taskflow tasks are created using different types of flows such as a
linear, unordered or a graph flow. The linear and graph flow allow for strong
ordering between individual tasks and it is for this reason that the workflow
engine utilizes a graph flow. The creation of tasks, subsequently linking them
into a graph like structure and submitting them is shown below.

.. code-block:: python

    self.execution_rule = self.get_execution_rule(actions)
    flow = gf.Flow("watcher_flow")
    actions_uuid = {}
    for a in actions:
        task = TaskFlowActionContainer(a, self)
        flow.add(task)
        actions_uuid[a.uuid] = task

    for a in actions:
        for parent_id in a.parents:
            flow.link(actions_uuid[parent_id], actions_uuid[a.uuid],
                      decider=self.decider)

    e = engines.load(
        flow, executor='greenthreaded', engine='parallel',
        max_workers=self.config.max_workers)
    e.run()

    return flow

In the applier tasks are contained in a :class:`~.TaskFlowActionContainer`
which allows them to trigger events in the workflow engine. This way the
workflow engine can halt or take other actions while the action plan is being
executed based on the success or failure of individual actions. However, the
base workflow engine simply uses these notifies to store the result of
individual actions in the database. Additionally, since taskflow uses a graph
flow if any of the tasks would fail all childs of this tasks not be executed
while ``do_revert`` will be triggered for all parents.

.. code-block:: python

    class TaskFlowActionContainer(...):
        ...
        def do_execute(self, *args, **kwargs):
            ...
            result = self.action.execute()
            if result is True:
                return self.engine.notify(self._db_action,
                                          objects.action.State.SUCCEEDED)
            else:
                self.engine.notify(self._db_action,
                                   objects.action.State.FAILED)

    class BaseWorkFlowEngine(...):
        ...
        def notify(self, action, state):
            db_action = objects.Action.get_by_uuid(self.context, action.uuid,
                                                   eager=True)
            db_action.state = state
            db_action.save()
            return db_action
