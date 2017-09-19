..
      Except where otherwise noted, this document is licensed under Creative
      Commons Attribution 3.0 License.  You can view the license at:

          https://creativecommons.org/licenses/by/3.0/

.. _implement_goal_plugin:

================
Build a new goal
================

Watcher Decision Engine has an external :ref:`goal <goal_definition>`
plugin interface which gives anyone the ability to integrate an external
goal which can be achieved by a :ref:`strategy <strategy_definition>`.

This section gives some guidelines on how to implement and integrate custom
goals with Watcher. If you wish to create a third-party package for your
plugin, you can refer to our :ref:`documentation for third-party package
creation <plugin-base_setup>`.


Pre-requisites
==============

Before using any goal, please make sure that none of the existing goals fit
your needs. Indeed, the underlying value of defining a goal is to be able to
compare the efficacy of the action plans resulting from the various strategies
satisfying the same goal. By doing so, Watcher can assist the administrator
in his choices.


Create a new plugin
===================

In order to create a new goal, you have to:

- Extend the :py:class:`~.base.Goal` class.
- Implement its :py:meth:`~.Goal.get_name` class method to return the
  **unique** ID of the new goal you want to create. This unique ID should
  be the same as the name of :ref:`the entry point you will declare later on
  <goal_plugin_add_entrypoint>`.
- Implement its :py:meth:`~.Goal.get_display_name` class method to
  return the translated display name of the goal you want to create.
  Note: Do not use a variable to return the translated string so it can be
  automatically collected by the translation tool.
- Implement its :py:meth:`~.Goal.get_translatable_display_name`
  class method to return the translation key (actually the english display
  name) of your new goal. The value return should be the same as the
  string translated in :py:meth:`~.Goal.get_display_name`.
- Implement its :py:meth:`~.Goal.get_efficacy_specification` method to return
  the :ref:`efficacy specification <efficacy_specification_definition>` for
  your goal.

Here is an example showing how you can define a new ``NewGoal`` goal plugin:

.. code-block:: python

    # filepath: thirdparty/new.py
    # import path: thirdparty.new

    from watcher._i18n import _
    from watcher.decision_engine.goal import base
    from watcher.decision_engine.goal.efficacy import specs

    class NewGoal(base.Goal):

        @classmethod
        def get_name(cls):
            return "new_goal"  # Will be the name of the entry point

        @classmethod
        def get_display_name(cls):
            return _("New Goal")

        @classmethod
        def get_translatable_display_name(cls):
            return "New Goal"

        @classmethod
        def get_efficacy_specification(cls):
            return specs.Unclassified()


As you may have noticed, the :py:meth:`~.Goal.get_efficacy_specification`
method returns an :py:meth:`~.Unclassified` instance which
is provided by Watcher. This efficacy specification is useful during the
development process of your goal as it corresponds to an empty specification.
If you want to learn more about what efficacy specifications are used for or to
define your own efficacy specification, please refer to the :ref:`related
section below <implement_efficacy_specification>`.


Abstract Plugin Class
=====================

Here below is the abstract :py:class:`~.base.Goal` class:

.. autoclass:: watcher.decision_engine.goal.base.Goal
    :members:
    :noindex:

.. _goal_plugin_add_entrypoint:

Add a new entry point
=====================

In order for the Watcher Decision Engine to load your new goal, the
goal must be registered as a named entry point under the ``watcher_goals``
entry point namespace of your ``setup.py`` file. If you are using pbr_, this
entry point should be placed in your ``setup.cfg`` file.

The name you give to your entry point has to be unique and should be the same
as the value returned by the :py:meth:`~.base.Goal.get_name` class method of
your goal.

Here below is how you would proceed to register ``NewGoal`` using pbr_:

.. code-block:: ini

    [entry_points]
    watcher_goals =
        new_goal = thirdparty.new:NewGoal


To get a better understanding on how to implement a more advanced goal, have
a look at the
:py:class:`watcher.decision_engine.goal.goals.ServerConsolidation` class.

.. _pbr: https://docs.openstack.org/pbr/latest

.. _implement_efficacy_specification:

Implement a customized efficacy specification
=============================================

What is it for?
---------------

Efficacy specifications define a set of specifications for a given goal.
These specifications actually define a list of indicators which are to be used
to compute a global efficacy that outlines how well a strategy performed when
trying to achieve the goal it is associated to.

The idea behind such specification is to give the administrator the possibility
to run an audit using different strategies satisfying the same goal and be able
to judge how they performed at a glance.


Implementation
--------------

In order to create a new efficacy specification, you have to:

- Extend the :py:class:`~.EfficacySpecification` class.
- Implement :py:meth:`~.EfficacySpecification.get_indicators_specifications`
  by returning a list of :py:class:`~.IndicatorSpecification` instances.

  * Each :py:class:`~.IndicatorSpecification` instance should actually extend
    the latter.
  * Each indicator specification should have a **unique name** which should be
    a valid Python variable name.
  * They should implement the :py:attr:`~.EfficacySpecification.schema`
    abstract property by returning a :py:class:`~.voluptuous.Schema` instance.
    This schema is the contract the strategy will have to comply with when
    setting the value associated to the indicator specification within its
    solution (see the :ref:`architecture of Watcher
    <sequence_diagrams_create_and_launch_audit>` for more information on
    the audit execution workflow).

- Implement the :py:meth:`~.EfficacySpecification.get_global_efficacy` method:
  it should compute the global efficacy for the goal it achieves based on the
  efficacy indicators you just defined.

Here below is an example of an efficacy specification containing one indicator
specification:

.. code-block:: python

    from watcher._i18n import _
    from watcher.decision_engine.goal.efficacy import base as efficacy_base
    from watcher.decision_engine.goal.efficacy import indicators
    from watcher.decision_engine.solution import efficacy


    class IndicatorExample(IndicatorSpecification):
        def __init__(self):
            super(IndicatorExample, self).__init__(
                name="indicator_example",
                description=_("Example of indicator specification."),
                unit=None,
            )

        @property
        def schema(self):
            return voluptuous.Schema(voluptuous.Range(min=0), required=True)


    class UnclassifiedStrategySpecification(efficacy_base.EfficacySpecification):

        def get_indicators_specifications(self):
            return [IndicatorExample()]

        def get_global_efficacy(self, indicators_map):
            return efficacy.Indicator(
              name="global_efficacy_indicator",
              description="Example of global efficacy indicator",
              unit="%",
              value=indicators_map.indicator_example % 100)


To get a better understanding on how to implement an efficacy specification,
have a look at :py:class:`~.ServerConsolidationSpecification`.

Also, if you want to see a concrete example of an indicator specification,
have a look at :py:class:`~.ReleasedComputeNodesCount`.
