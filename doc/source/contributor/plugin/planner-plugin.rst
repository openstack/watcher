..
      Except where otherwise noted, this document is licensed under Creative
      Commons Attribution 3.0 License.  You can view the license at:

          https://creativecommons.org/licenses/by/3.0/

.. _implement_planner_plugin:

===================
Build a new planner
===================

Watcher :ref:`Decision Engine <watcher_decision_engine_definition>` has an
external :ref:`planner <watcher_planner_definition>` plugin interface which
gives anyone the ability to integrate an external :ref:`planner
<watcher_planner_definition>` in order to extend the initial set of planners
Watcher provides.

This section gives some guidelines on how to implement and integrate custom
planners with Watcher.

.. _Decision Engine: watcher_decision_engine_definition

Creating a new plugin
=====================

First of all you have to extend the base :py:class:`~.BasePlanner` class which
defines an abstract method that you will have to implement. The
:py:meth:`~.BasePlanner.schedule` is the method being called by the Decision
Engine to schedule a given solution (:py:class:`~.BaseSolution`) into an
:ref:`action plan <action_plan_definition>` by ordering/sequencing an unordered
set of actions contained in the proposed solution (for more details, see
:ref:`definition of a solution <solution_definition>`).

Here is an example showing how you can write a planner plugin called
``DummyPlanner``:

.. code-block:: python

    # Filepath = third-party/third_party/dummy.py
    # Import path = third_party.dummy
    from oslo_utils import uuidutils
    from watcher.decision_engine.planner import base


    class DummyPlanner(base.BasePlanner):

        def _create_action_plan(self, context, audit_id):
            action_plan_dict = {
                'uuid': uuidutils.generate_uuid(),
                'audit_id': audit_id,
                'first_action_id': None,
                'state': objects.action_plan.State.RECOMMENDED
            }

            new_action_plan = objects.ActionPlan(context, **action_plan_dict)
            new_action_plan.create(context)
            new_action_plan.save()
            return new_action_plan

        def schedule(self, context, audit_id, solution):
            # Empty action plan
            action_plan = self._create_action_plan(context, audit_id)
            # todo: You need to create the workflow of actions here
            # and attach it to the action plan
            return action_plan

This implementation is the most basic one. So if you want to have more advanced
examples, have a look at the implementation of planners already provided by
Watcher like :py:class:`~.DefaultPlanner`. A list with all available planner
plugins can be found :ref:`here <watcher_planners>`.


Define configuration parameters
===============================

At this point, you have a fully functional planner. However, in more complex
implementation, you may want to define some configuration options so one can
tune the planner to its needs. To do so, you can implement the
:py:meth:`~.Loadable.get_config_opts` class method as followed:

.. code-block:: python

    from oslo_config import cfg

    class DummyPlanner(base.BasePlanner):

        # [...]

        def schedule(self, context, audit_uuid, solution):
            assert self.config.test_opt == 0
            # [...]

        @classmethod
        def get_config_opts(cls):
            return super(
                DummyPlanner, cls).get_config_opts() + [
                cfg.StrOpt('test_opt', help="Demo Option.", default=0),
                # Some more options ...
            ]

The configuration options defined within this class method will be included
within the global ``watcher.conf`` configuration file under a section named by
convention: ``{namespace}.{plugin_name}``. In our case, the ``watcher.conf``
configuration would have to be modified as followed:

.. code-block:: ini

    [watcher_planners.dummy]
    # Option used for testing.
    test_opt = test_value

Then, the configuration options you define within this method will then be
injected in each instantiated object via the  ``config`` parameter of the
:py:meth:`~.BasePlanner.__init__` method.


Abstract Plugin Class
=====================

Here below is the abstract ``BasePlanner`` class that every single planner
should implement:

.. autoclass:: watcher.decision_engine.planner.base.BasePlanner
    :members:
    :special-members: __init__
    :noindex:


Register a new entry point
==========================

In order for the Watcher Decision Engine to load your new planner, the
latter must be registered as a new entry point under the
``watcher_planners`` entry point namespace of your ``setup.py`` file. If you
are using pbr_, this entry point should be placed in your ``setup.cfg`` file.

The name you give to your entry point has to be unique.

Here below is how you would proceed to register ``DummyPlanner`` using pbr_:

.. code-block:: ini

    [entry_points]
    watcher_planners =
        dummy = third_party.dummy:DummyPlanner

.. _pbr: https://docs.openstack.org/pbr/latest


Using planner plugins
=====================

The :ref:`Watcher Decision Engine <watcher_decision_engine_definition>` service
will automatically discover any installed plugins when it is started. This
means that if Watcher is already running when you install your plugin, you will
have to restart the related Watcher services. If a Python package containing a
custom plugin is installed within the same environment as Watcher, Watcher will
automatically make that plugin available for use.

At this point, Watcher will use your new planner if you referenced it in the
``planner`` option under the ``[watcher_planner]`` section of your
``watcher.conf`` configuration file when you started it. For example, if you
want to use the ``dummy`` planner you just installed, you would have to
select it as followed:

.. code-block:: ini

    [watcher_planner]
    planner = dummy

As you may have noticed, only a single planner implementation can be activated
at a time, so make sure it is generic enough to support all your strategies
and actions.
