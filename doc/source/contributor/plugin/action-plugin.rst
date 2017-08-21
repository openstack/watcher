..
      Except where otherwise noted, this document is licensed under Creative
      Commons Attribution 3.0 License.  You can view the license at:

          https://creativecommons.org/licenses/by/3.0/

.. _implement_action_plugin:

==================
Build a new action
==================

Watcher Applier has an external :ref:`action <action_definition>` plugin
interface which gives anyone the ability to integrate an external
:ref:`action <action_definition>` in order to extend the initial set of actions
Watcher provides.

This section gives some guidelines on how to implement and integrate custom
actions with Watcher.


Creating a new plugin
=====================

First of all you have to extend the base :py:class:`BaseAction` class which
defines a set of abstract methods and/or properties that you will have to
implement:

 - The :py:attr:`~.BaseAction.schema` is an abstract property that you have to
   implement. This is the first function to be called by the
   :ref:`applier <watcher_applier_definition>` before any further processing
   and its role is to validate the input parameters that were provided to it.
 - The :py:meth:`~.BaseAction.pre_condition` is called before the execution of
   an action. This method is a hook that can be used to perform some
   initializations or to make some more advanced validation on its input
   parameters. If you wish to block the execution based on this factor, you
   simply have to ``raise`` an exception.
 - The :py:meth:`~.BaseAction.post_condition` is called after the execution of
   an action. As this function is called regardless of whether an action
   succeeded or not, this can prove itself useful to perform cleanup
   operations.
 - The :py:meth:`~.BaseAction.execute` is the main component of an action.
   This is where you should implement the logic of your action.
 - The :py:meth:`~.BaseAction.revert` allows you to roll back the targeted
   resource to its original state following a faulty execution. Indeed, this
   method is called by the workflow engine whenever an action raises an
   exception.

Here is an example showing how you can write a plugin called ``DummyAction``:

.. code-block:: python

    # Filepath = <PROJECT_DIR>/thirdparty/dummy.py
    # Import path = thirdparty.dummy
    import voluptuous

    from watcher.applier.actions import base


    class DummyAction(base.BaseAction):

        @property
        def schema(self):
            return voluptuous.Schema({})

        def execute(self):
            # Does nothing
            pass  # Only returning False is considered as a failure

        def revert(self):
            # Does nothing
            pass

        def pre_condition(self):
            # No pre-checks are done here
            pass

        def post_condition(self):
            # Nothing done here
            pass


This implementation is the most basic one. So in order to get a better
understanding on how to implement a more advanced action, have a look at the
:py:class:`~watcher.applier.actions.migration.Migrate` class.

Input validation
----------------

As you can see in the previous example, we are using `Voluptuous`_ to validate
the input parameters of an action. So if you want to learn more about how to
work with `Voluptuous`_, you can have a look at their `documentation`_:

.. _Voluptuous: https://github.com/alecthomas/voluptuous
.. _documentation: https://github.com/alecthomas/voluptuous/blob/master/README.md


Define configuration parameters
===============================

At this point, you have a fully functional action. However, in more complex
implementation, you may want to define some configuration options so one can
tune the action to its needs. To do so, you can implement the
:py:meth:`~.Loadable.get_config_opts` class method as followed:

.. code-block:: python

    from oslo_config import cfg

    class DummyAction(base.BaseAction):

        # [...]

        def execute(self):
            assert self.config.test_opt == 0

        @classmethod
        def get_config_opts(cls):
            return super(
                DummyAction, cls).get_config_opts() + [
                cfg.StrOpt('test_opt', help="Demo Option.", default=0),
                # Some more options ...
            ]


The configuration options defined within this class method will be included
within the global ``watcher.conf`` configuration file under a section named by
convention: ``{namespace}.{plugin_name}``. In our case, the ``watcher.conf``
configuration would have to be modified as followed:

.. code-block:: ini

    [watcher_actions.dummy]
    # Option used for testing.
    test_opt = test_value

Then, the configuration options you define within this method will then be
injected in each instantiated object via the  ``config`` parameter of the
:py:meth:`~.BaseAction.__init__` method.


Abstract Plugin Class
=====================

Here below is the abstract ``BaseAction`` class that every single action
should implement:

.. autoclass:: watcher.applier.actions.base.BaseAction
    :members:
    :special-members: __init__
    :noindex:

    .. py:attribute:: schema

        Defines a Schema that the input parameters shall comply to

        :returns: A schema declaring the input parameters this action should be
                  provided along with their respective constraints
                  (e.g. type, value range, ...)
        :rtype: :py:class:`voluptuous.Schema` instance


Register a new entry point
==========================

In order for the Watcher Applier to load your new action, the
action must be registered as a named entry point under the
``watcher_actions`` entry point of your ``setup.py`` file. If you are using
pbr_, this entry point should be placed in your ``setup.cfg`` file.

The name you give to your entry point has to be unique.

Here below is how you would proceed to register ``DummyAction`` using pbr_:

.. code-block:: ini

    [entry_points]
    watcher_actions =
        dummy = thirdparty.dummy:DummyAction

.. _pbr: https://docs.openstack.org/pbr/latest


Using action plugins
====================

The Watcher Applier service will automatically discover any installed plugins
when it is restarted. If a Python package containing a custom plugin is
installed within the same environment as Watcher, Watcher will automatically
make that plugin available for use.

At this point, you can use your new action plugin in your :ref:`strategy plugin
<implement_strategy_plugin>` if you reference it via the use of the
:py:meth:`~.Solution.add_action` method:

.. code-block:: python

    # [...]
    self.solution.add_action(
        action_type="dummy",  # Name of the entry point we registered earlier
        applies_to="",
        input_parameters={})

By doing so, your action will be saved within the Watcher Database, ready to be
processed by the planner for creating an action plan which can then be executed
by the Watcher Applier via its workflow engine.

At the last, remember to add the action into the weights in ``watcher.conf``,
otherwise you will get an error when the action be referenced in a strategy.


Scheduling of an action plugin
==============================

Watcher provides a basic built-in :ref:`planner <watcher_planner_definition>`
which is only able to process the Watcher built-in actions. Therefore, you will
either have to use an existing third-party planner or :ref:`implement another
planner <implement_planner_plugin>` that will be able to take into account your
new action plugin.


Test your new action
====================

In order to test your new action via a manual test or a Tempest test, you can
use the  :py:class:`~.Actuator` strategy and pass it one or more actions to
execute. This way, you can isolate your action to see if it works as expected.
