..
      Except where otherwise noted, this document is licensed under Creative
      Commons Attribution 3.0 License.  You can view the license at:

          https://creativecommons.org/licenses/by/3.0/

.. _implement_cluster_data_model_collector_plugin:

========================================
Build a new cluster data model collector
========================================

Watcher Decision Engine has an external cluster data model (CDM) plugin
interface which gives anyone the ability to integrate an external cluster data
model collector (CDMC) in order to extend the initial set of cluster data model
collectors Watcher provides.

This section gives some guidelines on how to implement and integrate custom
cluster data model collectors within Watcher.


Creating a new plugin
=====================

In order to create a new cluster data model collector, you have to:

- Extend the :py:class:`~.base.BaseClusterDataModelCollector` class.
- Implement its :py:meth:`~.BaseClusterDataModelCollector.execute` abstract
  method to return your entire cluster data model that this method should
  build.
- Implement its :py:meth:`~.BaseClusterDataModelCollector.audit_scope_handler`
  abstract property to return your audit scope handler.
- Implement its :py:meth:`~.Goal.notification_endpoints` abstract property to
  return the list of all the :py:class:`~.base.NotificationEndpoint` instances
  that will be responsible for handling incoming notifications in order to
  incrementally update your cluster data model.

First of all, you have to extend the :class:`~.BaseClusterDataModelCollector`
base class which defines the :py:meth:`~.BaseClusterDataModelCollector.execute`
abstract method you will have to implement. This method is responsible for
building an entire cluster data model.

Here is an example showing how you can write a plugin called
``DummyClusterDataModelCollector``:

.. code-block:: python

    # Filepath = <PROJECT_DIR>/thirdparty/dummy.py
    # Import path = thirdparty.dummy

    from watcher.decision_engine.model import model_root
    from watcher.decision_engine.model.collector import base


    class DummyClusterDataModelCollector(base.BaseClusterDataModelCollector):

        def execute(self):
            model = model_root.ModelRoot()
            # Do something here...
            return model

        @property
        def audit_scope_handler(self):
            return None

        @property
        def notification_endpoints(self):
            return []

This implementation is the most basic one. So in order to get a better
understanding on how to implement a more advanced cluster data model collector,
have a look at the :py:class:`~.NovaClusterDataModelCollector` class.

Define a custom model
=====================

As you may have noticed in the above example, we are reusing an existing model
provided by Watcher. However, this model can be easily customized by
implementing a new class that would implement the :py:class:`~.Model` abstract
base class. Here below is simple example on how to proceed in implementing a
custom Model:

.. code-block:: python

    # Filepath = <PROJECT_DIR>/thirdparty/dummy.py
    # Import path = thirdparty.dummy

    from watcher.decision_engine.model import base as modelbase
    from watcher.decision_engine.model.collector import base


    class MyModel(modelbase.Model):

        def to_string(self):
            return 'MyModel'


    class DummyClusterDataModelCollector(base.BaseClusterDataModelCollector):

        def execute(self):
            model = MyModel()
            # Do something here...
            return model

        @property
        def notification_endpoints(self):
            return []

Here below is the abstract ``Model`` class that every single cluster data model
should implement:

.. autoclass:: watcher.decision_engine.model.base.Model
    :members:
    :special-members: __init__
    :noindex:

Define configuration parameters
===============================

At this point, you have a fully functional cluster data model collector.
By default, cluster data model collectors define a ``period`` option (see
:py:meth:`~.BaseClusterDataModelCollector.get_config_opts`) that corresponds
to the interval of time between each synchronization of the in-memory model.

However, in more complex implementation, you may want to define some
configuration options so one can tune the cluster data model collector to your
needs. To do so, you can implement the :py:meth:`~.Loadable.get_config_opts`
class method as followed:

.. code-block:: python

    from oslo_config import cfg
    from watcher.decision_engine.model import model_root
    from watcher.decision_engine.model.collector import base


    class DummyClusterDataModelCollector(base.BaseClusterDataModelCollector):

        def execute(self):
            model = model_root.ModelRoot()
            # Do something here...
            return model

        @property
        def audit_scope_handler(self):
            return None

        @property
        def notification_endpoints(self):
            return []

        @classmethod
        def get_config_opts(cls):
            return super(
                DummyClusterDataModelCollector, cls).get_config_opts() + [
                cfg.StrOpt('test_opt', help="Demo Option.", default=0),
                # Some more options ...
            ]

The configuration options defined within this class method will be included
within the global ``watcher.conf`` configuration file under a section named by
convention: ``{namespace}.{plugin_name}`` (see section :ref:`Register a new
entry point <register_new_cdmc_entrypoint>`). The namespace for CDMC plugins is
``watcher_cluster_data_model_collectors``, so in our case, the ``watcher.conf``
configuration would have to be modified as followed:

.. code-block:: ini

    [watcher_cluster_data_model_collectors.dummy]
    # Option used for testing.
    test_opt = test_value

Then, the configuration options you define within this method will then be
injected in each instantiated object via the  ``config`` parameter of the
:py:meth:`~.BaseClusterDataModelCollector.__init__` method.


Abstract Plugin Class
=====================

Here below is the abstract ``BaseClusterDataModelCollector`` class that every
single cluster data model collector should implement:

.. autoclass:: watcher.decision_engine.model.collector.base.BaseClusterDataModelCollector
    :members:
    :special-members: __init__
    :noindex:


.. _register_new_cdmc_entrypoint:

Register a new entry point
==========================

In order for the Watcher Decision Engine to load your new cluster data model
collector, the latter must be registered as a named entry point under the
``watcher_cluster_data_model_collectors`` entry point namespace of your
``setup.py`` file. If you are using pbr_, this entry point should be placed in
your ``setup.cfg`` file.

The name you give to your entry point has to be unique.

Here below is how to register ``DummyClusterDataModelCollector`` using pbr_:

.. code-block:: ini

    [entry_points]
    watcher_cluster_data_model_collectors =
        dummy = thirdparty.dummy:DummyClusterDataModelCollector

.. _pbr: https://docs.openstack.org/pbr/latest/


Add new notification endpoints
==============================

At this point, you have a fully functional cluster data model collector.
However, this CDMC is only refreshed periodically via a background scheduler.
As you may sometimes execute a strategy with a stale CDM due to a high activity
on your infrastructure, you can define some notification endpoints that will be
responsible for incrementally updating the CDM based on notifications emitted
by other services such as Nova. To do so, you can implement and register a new
``DummyEndpoint`` notification endpoint regarding a ``dummy`` event as shown
below:

.. code-block:: python

    from watcher.decision_engine.model import model_root
    from watcher.decision_engine.model.collector import base


    class DummyNotification(base.NotificationEndpoint):

        @property
        def filter_rule(self):
            return filtering.NotificationFilter(
                publisher_id=r'.*',
                event_type=r'^dummy$',
            )

        def info(self, ctxt, publisher_id, event_type, payload, metadata):
            # Do some CDM modifications here...
            pass


    class DummyClusterDataModelCollector(base.BaseClusterDataModelCollector):

        def execute(self):
            model = model_root.ModelRoot()
            # Do something here...
            return model

        @property
        def notification_endpoints(self):
            return [DummyNotification(self)]


Note that if the event you are trying to listen to is published by a new
service, you may have to also add a new topic Watcher will have to subscribe to
in the ``notification_topics`` option of the ``[watcher_decision_engine]``
section.


Using cluster data model collector plugins
==========================================

The Watcher Decision Engine service will automatically discover any installed
plugins when it is restarted. If a Python package containing a custom plugin is
installed within the same environment as Watcher, Watcher will automatically
make that plugin available for use.

At this point, you can use your new cluster data model plugin in your
:ref:`strategy plugin <implement_strategy_plugin>` by using the
:py:attr:`~.BaseStrategy.collector_manager` property as followed:

.. code-block:: python

    # [...]
    dummy_collector = self.collector_manager.get_cluster_model_collector(
        "dummy")  # "dummy" is the name of the entry point we declared earlier
    dummy_model = dummy_collector.get_latest_cluster_data_model()
    # Do some stuff with this model
