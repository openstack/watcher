..
      Except where otherwise noted, this document is licensed under Creative
      Commons Attribution 3.0 License.  You can view the license at:

          https://creativecommons.org/licenses/by/3.0/

.. _implement_strategy_plugin:

=================================
Build a new optimization strategy
=================================

Watcher Decision Engine has an external :ref:`strategy <strategy_definition>`
plugin interface which gives anyone the ability to integrate an external
strategy in order to make use of placement algorithms.

This section gives some guidelines on how to implement and integrate custom
strategies with Watcher. If you wish to create a third-party package for your
plugin, you can refer to our :ref:`documentation for third-party package
creation <plugin-base_setup>`.


Pre-requisites
==============

Before using any strategy, you should make sure you have your Telemetry service
configured so that it would provide you all the metrics you need to be able to
use your strategy.


Create a new plugin
===================

In order to create a new strategy, you have to:

- Extend the :py:class:`~.UnclassifiedStrategy` class
- Implement its :py:meth:`~.BaseStrategy.get_name` class method to return the
  **unique** ID of the new strategy you want to create. This unique ID should
  be the same as the name of :ref:`the entry point we will declare later on
  <strategy_plugin_add_entrypoint>`.
- Implement its :py:meth:`~.BaseStrategy.get_display_name` class method to
  return the translated display name of the strategy you want to create.
  Note: Do not use a variable to return the translated string so it can be
  automatically collected by the translation tool.
- Implement its :py:meth:`~.BaseStrategy.get_translatable_display_name`
  class method to return the translation key (actually the english display
  name) of your new strategy. The value return should be the same as the
  string translated in :py:meth:`~.BaseStrategy.get_display_name`.
- Implement its :py:meth:`~.BaseStrategy.execute` method to return the
  solution you computed within your strategy.

Here is an example showing how you can write a plugin called ``NewStrategy``:

.. code-block:: python

    import abc

    import six

    from watcher._i18n import _
    from watcher.decision_engine.strategy.strategies import base


    class NewStrategy(base.UnclassifiedStrategy):

        def __init__(self, osc=None):
            super(NewStrategy, self).__init__(osc)

        def execute(self, original_model):
            self.solution.add_action(action_type="nop",
                                     input_parameters=parameters)
            # Do some more stuff here ...
            return self.solution

        @classmethod
        def get_name(cls):
            return "new_strategy"

        @classmethod
        def get_display_name(cls):
            return _("New strategy")

        @classmethod
        def get_translatable_display_name(cls):
            return "New strategy"


As you can see in the above example, the :py:meth:`~.BaseStrategy.execute`
method returns a :py:class:`~.BaseSolution` instance as required. This solution
is what wraps the abstract set of actions the strategy recommends to you. This
solution is then processed by a :ref:`planner <planner_definition>` to produce
an action plan which contains the sequenced flow of actions to be
executed by the :ref:`Watcher Applier <watcher_applier_definition>`.

Please note that your strategy class will expect to find the same constructor
signature as BaseStrategy to instantiate you strategy. Therefore, you should
ensure that your ``__init__`` signature is identical to the
:py:class:`~.BaseStrategy` one.


Create a new goal
=================

As stated before, the ``NewStrategy`` class extends a class called
:py:class:`~.UnclassifiedStrategy`. This class actually implements a set of
abstract methods which are defined within the :py:class:`~.BaseStrategy` parent
class.

Once you are confident in your strategy plugin, the next step is now to
classify your goal by assigning it a proper goal. To do so, you can either
reuse existing goals defined in Watcher. As of now, four goal-oriented abstract
classes are defined in Watcher:

- :py:class:`~.UnclassifiedStrategy` which is the one I mentioned up until now.
- :py:class:`~.DummyBaseStrategy` which is used by :py:class:`~.DummyStrategy`
  for testing purposes.
- :py:class:`~.ServerConsolidationBaseStrategy`
- :py:class:`~.ThermalOptimizationBaseStrategy`

If none of the above actually correspond to the goal your new strategy
achieves, you can define a brand new one. To do so, you need to:

- Extend the :py:class:`~.BaseStrategy` class to make your new goal-oriented
  strategy abstract class :
- Implement its :py:meth:`~.BaseStrategy.get_goal_name` class method to
  return the **unique** ID of the goal you want to achieve.
- Implement its :py:meth:`~.BaseStrategy.get_goal_display_name` class method
  to return the translated display name of the goal you want to achieve.
  Note: Do not use a variable to return the translated string so it can be
  automatically collected by the translation tool.
- Implement its :py:meth:`~.BaseStrategy.get_translatable_goal_display_name`
  class method to return the goal translation key (actually the english
  display name). The value return should be the same as the string translated
  in :py:meth:`~.BaseStrategy.get_goal_display_name`.

Here is an example showing how you can define a new ``NEW_GOAL`` goal and
modify your ``NewStrategy`` plugin so it now achieves the latter:

.. code-block:: python

    import abc

    import six

    from watcher._i18n import _
    from watcher.decision_engine.strategy.strategies import base

    @six.add_metaclass(abc.ABCMeta)
    class NewGoalBaseStrategy(base.BaseStrategy):

        @classmethod
        def get_goal_name(cls):
            return "NEW_GOAL"

        @classmethod
        def get_goal_display_name(cls):
            return _("New goal")

        @classmethod
        def get_translatable_goal_display_name(cls):
            return "New goal"


    class NewStrategy(NewGoalBaseStrategy):

        def __init__(self, config, osc=None):
            super(NewStrategy, self).__init__(config, osc)

        def execute(self, original_model):
            self.solution.add_action(action_type="nop",
                                     input_parameters=parameters)
            # Do some more stuff here ...
            return self.solution

        @classmethod
        def get_name(cls):
            return "new_strategy"

        @classmethod
        def get_display_name(cls):
            return _("New strategy")

        @classmethod
        def get_translatable_display_name(cls):
            return "New strategy"


Define configuration parameters
===============================

At this point, you have a fully functional strategy. However, in more complex
implementation, you may want to define some configuration options so one can
tune the strategy to its needs. To do so, you can implement the
:py:meth:`~.Loadable.get_config_opts` class method as followed:

.. code-block:: python

    from oslo_config import cfg

    class NewStrategy(NewGoalBaseStrategy):

        # [...]

        def execute(self, original_model):
            assert self.config.test_opt == 0
            # [...]

        def get_config_opts(self):
            return [
                cfg.StrOpt('test_opt', help="Demo Option.", default=0),
                # Some more options ...
            ]


The configuration options defined within this class method will be included
within the global ``watcher.conf`` configuration file under a section named by
convention: ``{namespace}.{plugin_name}``. In our case, the ``watcher.conf``
configuration would have to be modified as followed:

.. code-block:: ini

    [watcher_strategies.new_strategy]
    # Option used for testing.
    test_opt = test_value

Then, the configuration options you define within this method will then be
injected in each instantiated object via the  ``config`` parameter of the
:py:meth:`~.BaseStrategy.__init__` method.


Abstract Plugin Class
=====================

Here below is the abstract :py:class:`~.BaseStrategy` class:

.. autoclass:: watcher.decision_engine.strategy.strategies.base.BaseStrategy
    :members:
    :special-members: __init__
    :noindex:

.. _strategy_plugin_add_entrypoint:

Add a new entry point
=====================

In order for the Watcher Decision Engine to load your new strategy, the
strategy must be registered as a named entry point under the
``watcher_strategies`` entry point of your ``setup.py`` file. If you are using
pbr_, this entry point should be placed in your ``setup.cfg`` file.

The name you give to your entry point has to be unique and should be the same
as the value returned by the :py:meth:`~.BaseStrategy.get_id` class method of
your strategy.

Here below is how you would proceed to register ``DummyStrategy`` using pbr_:

.. code-block:: ini

    [entry_points]
    watcher_strategies =
        dummy_strategy = thirdparty.dummy:DummyStrategy


To get a better understanding on how to implement a more advanced strategy,
have a look at the :py:class:`~.BasicConsolidation` class.

.. _pbr: http://docs.openstack.org/developer/pbr/

Using strategy plugins
======================

The Watcher Decision Engine service will automatically discover any installed
plugins when it is restarted. If a Python package containing a custom plugin is
installed within the same environment as Watcher, Watcher will automatically
make that plugin available for use.

At this point, Watcher will scan and register inside the :ref:`Watcher Database
<watcher_database_definition>` all the strategies (alongside the goals they
should satisfy) you implemented upon restarting the :ref:`Watcher Decision
Engine <watcher_decision_engine_definition>`.

You should take care when installing strategy plugins. By their very nature,
there are no guarantees that utilizing them as is will be supported, as
they may require a set of metrics which is not yet available within the
Telemetry service. In such a case, please do make sure that you first
check/configure the latter so your new strategy can be fully functional.

Querying metrics
----------------

A large set of metrics, generated by OpenStack modules, can be used in your
strategy implementation. To collect these metrics, Watcher provides a
`Helper`_ to the Ceilometer API, which makes this API reusable and easier
to used.

If you want to use your own metrics database backend, please refer to the
`Ceilometer developer guide`_. Indeed, Ceilometer's pluggable model allows
for various types of backends.  A list of the available backends is located
here_. The Ceilosca project is a good example of how to create your own
pluggable backend.

Finally, if your strategy requires new metrics not covered by Ceilometer, you
can add them through a Ceilometer `plugin`_.

.. _`Helper`: https://github.com/openstack/watcher/blob/master/watcher/metrics_engine/cluster_history/ceilometer.py#L31
.. _`Ceilometer developer guide`: http://docs.openstack.org/developer/ceilometer/architecture.html#storing-the-data
.. _`here`: http://docs.openstack.org/developer/ceilometer/install/dbreco.html#choosing-a-database-backend
.. _`plugin`: http://docs.openstack.org/developer/ceilometer/plugins.html
.. _`Ceilosca`: https://github.com/openstack/monasca-ceilometer/blob/master/ceilosca/ceilometer/storage/impl_monasca.py


Read usage metrics using the Python binding
-------------------------------------------

You can find the information about the Ceilometer Python binding on the
OpenStack `ceilometer client python API documentation
<http://docs.openstack.org/developer/python-ceilometerclient/api.html>`_

To facilitate the process, Watcher provides the ``osc`` attribute to every
strategy which includes clients to major OpenStack services, including
Ceilometer. So to access it within your strategy, you can do the following:

.. code-block:: py

    # Within your strategy "execute()"
    cclient = self.osc.ceilometer
    # TODO: Do something here

Using that you can now query the values for that specific metric:

.. code-block:: py

    query = None  # e.g. [{'field': 'foo', 'op': 'le', 'value': 34},]
    value_cpu = cclient.samples.list(
        meter_name='cpu_util',
        limit=10, q=query)


Read usage metrics using the Watcher Cluster History Helper
-----------------------------------------------------------

Here below is the abstract ``BaseClusterHistory`` class of the Helper.

.. autoclass:: watcher.metrics_engine.cluster_history.base.BaseClusterHistory
    :members:
    :noindex:


The following code snippet shows how to create a Cluster History class:

.. code-block:: py

    from watcher.metrics_engine.cluster_history import ceilometer as ceil

    query_history  = ceil.CeilometerClusterHistory()

Using that you can now query the values for that specific metric:

.. code-block:: py

    query_history.statistic_aggregation(resource_id=hypervisor.uuid,
                                  meter_name='compute.node.cpu.percent',
                                  period="7200",
                                  aggregate='avg'
                                  )
