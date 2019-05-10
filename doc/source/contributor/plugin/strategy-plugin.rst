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


Create a new strategy plugin
============================

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
  class method to return the translation key (actually the English display
  name) of your new strategy. The value return should be the same as the
  string translated in :py:meth:`~.BaseStrategy.get_display_name`.
- Implement its :py:meth:`~.BaseStrategy.execute` method to return the
  solution you computed within your strategy.

Here is an example showing how you can write a plugin called ``NewStrategy``:

.. code-block:: python

    # filepath: thirdparty/new.py
    # import path: thirdparty.new
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
solution is then processed by a :ref:`planner <watcher_planner_definition>` to
produce an action plan which contains the sequenced flow of actions to be
executed by the :ref:`Watcher Applier <watcher_applier_definition>`. This
solution also contains the various :ref:`efficacy indicators
<efficacy_indicator_definition>` alongside its computed :ref:`global efficacy
<efficacy_definition>`.

Please note that your strategy class will expect to find the same constructor
signature as BaseStrategy to instantiate you strategy. Therefore, you should
ensure that your ``__init__`` signature is identical to the
:py:class:`~.BaseStrategy` one.


Strategy efficacy
=================

As stated before, the ``NewStrategy`` class extends a class called
:py:class:`~.UnclassifiedStrategy`. This class actually implements a set of
abstract methods which are defined within the :py:class:`~.BaseStrategy` parent
class.

One thing this :py:class:`~.UnclassifiedStrategy` class defines is that our
``NewStrategy`` achieves the ``unclassified`` goal. This goal is a peculiar one
as it does not contain any indicator nor does it calculate a global efficacy.
This proves itself to be quite useful during the development of a new strategy
for which the goal has yet to be defined or in case a :ref:`new goal
<implement_goal_plugin>` has yet to be implemented.


Define Strategy Parameters
==========================

For each new added strategy, you can add parameters spec so that an operator
can input strategy parameters when creating an audit to control the
:py:meth:`~.BaseStrategy.execute` behavior of strategy. This is useful to
define some threshold for your strategy, and tune them at runtime.

To define parameters, just implements :py:meth:`~.BaseStrategy.get_schema` to
return parameters spec with `jsonschema
<http://json-schema.org/>`_ format.
It is strongly encouraged that provide default value for each parameter, or
else reference fails if operator specify no parameters.

Here is an example showing how you can define 2 parameters for
``DummyStrategy``:

.. code-block:: python

    class DummyStrategy(base.DummyBaseStrategy):

        @classmethod
        def get_schema(cls):
            return {
                "properties": {
                    "para1": {
                        "description": "number parameter example",
                        "type": "number",
                        "default": 3.2,
                        "minimum": 1.0,
                        "maximum": 10.2,
                    },
                    "para2": {
                        "description": "string parameter example",
                        "type": "string",
                        "default": "hello",
                    },
                },
            }


You can reference parameters in :py:meth:`~.BaseStrategy.execute`:

.. code-block:: python

    class DummyStrategy(base.DummyBaseStrategy):

        def execute(self):
            para1 = self.input_parameters.para1
            para2 = self.input_parameters.para2

            if para1 > 5:
                ...


Operator can specify parameters with following commands:

.. code:: bash

  $ watcher audit create -a <your_audit_template> -p para1=6.0 -p para2=hi

Pls. check user-guide for details.


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
as the value returned by the :py:meth:`~.BaseStrategy.get_name` class method of
your strategy.

Here below is how you would proceed to register ``NewStrategy`` using pbr_:

.. code-block:: ini

    [entry_points]
    watcher_strategies =
        new_strategy = thirdparty.new:NewStrategy


To get a better understanding on how to implement a more advanced strategy,
have a look at the :py:class:`~.BasicConsolidation` class.

.. _pbr: https://docs.openstack.org/pbr/latest

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
`DataSourceManager`_ for two data sources which are `Ceilometer`_
(with `Gnocchi`_ as API) and `Monasca`_. If you wish to query metrics from a
different data source, you can implement your own and use it via
DataSourceManager from within your new strategy. Indeed, strategies in Watcher
have the cluster data models decoupled from the data sources which means that
you may keep the former while changing the latter. The recommended way for you
to support a new data source is to implement a new helper that would
encapsulate within separate methods the queries you need to perform. To then
use it, you would just have to add it to appropriate watcher_strategies.*
section in config file.

If you want to use Ceilometer but with your own metrics database backend,
please refer to the `Ceilometer developer guide`_. The list of the available
Ceilometer backends is located here_. The `Ceilosca`_ project is a good example
of how to create your own pluggable backend. Moreover, if your strategy
requires new metrics not covered by Ceilometer, you can add them through a
`Ceilometer plugin`_.


.. _`DataSourceManager`: https://github.com/openstack/watcher/blob/master/watcher/datasource/manager.py
.. _`Ceilometer developer guide`: https://docs.openstack.org/ceilometer/latest/contributor/architecture.html#storing-accessing-the-data
.. _`Ceilometer`: https://docs.openstack.org/ceilometer/latest
.. _`Monasca`: https://github.com/openstack/monasca-api/blob/master/docs/monasca-api-spec.md
.. _`here`: https://docs.openstack.org/ceilometer/latest/contributor/install/dbreco.html#choosing-a-database-backend
.. _`Ceilometer plugin`: https://docs.openstack.org/ceilometer/latest/contributor/plugins.html
.. _`Ceilosca`: https://github.com/openstack/monasca-ceilometer/blob/master/ceilosca/ceilometer/storage/impl_monasca.py
.. _`Gnocchi`: https://gnocchi.xyz/

Read usage metrics using the Watcher Datasource Helper
------------------------------------------------------

The following code snippet shows how datasource_backend is defined:

.. code-block:: py

    from watcher.datasource import manager as ds_manager

    @property
    def datasource_backend(self):
        if not self._datasource_backend:

            # Load the global preferred datasources order but override it
            # if the strategy has a specific datasources config
            datasources = CONF.watcher_datasources
            if self.config.datasources:
                datasources = self.config

            self._datasource_backend = ds_manager.DataSourceManager(
                config=datasources,
                osc=self.osc
            ).get_backend(self.DATASOURCE_METRICS)
        return self._datasource_backend

Using that you can now query the values for that specific metric:

.. code-block:: py

    avg_meter = self.datasource_backend.statistic_aggregation(
        instance.uuid, 'cpu_util', self.periods['instance'],
        self.granularity,
        aggregation=self.aggregation_method['instance'])
