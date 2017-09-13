..
      Except where otherwise noted, this document is licensed under Creative
      Commons Attribution 3.0 License.  You can view the license at:

          https://creativecommons.org/licenses/by/3.0/

.. _implement_scoring_engine_plugin:

==========================
Build a new scoring engine
==========================

Watcher Decision Engine has an external :ref:`scoring engine
<scoring_engine_definition>` plugin interface which gives anyone the ability
to integrate an external scoring engine in order to make use of it in a
:ref:`strategy <strategy_definition>`.

This section gives some guidelines on how to implement and integrate custom
scoring engines with Watcher. If you wish to create a third-party package for
your plugin, you can refer to our :ref:`documentation for third-party package
creation <plugin-base_setup>`.


Pre-requisites
==============

Because scoring engines execute a purely mathematical tasks, they typically do
not have any additional dependencies. Additional requirements might be defined
by specific scoring engine implementations. For example, some scoring engines
might require to prepare learning data, which has to be loaded during the
scoring engine startup. Some other might require some external services to be
available (e.g. if the scoring infrastructure is running in the cloud).


Create a new scoring engine plugin
==================================

In order to create a new scoring engine you have to:

- Extend the :py:class:`watcher.decision_engine.scoring.base.ScoringEngine`
  class
- Implement its :py:meth:`~.ScoringEngine.get_name` method to return the
  **unique** ID of the new scoring engine you want to create. This unique ID
  should be the same as the name of :ref:`the entry point we will declare later
  on <scoring_engine_plugin_add_entrypoint>`.
- Implement its :py:meth:`~.ScoringEngine.get_description` method to return the
  user-friendly description of the implemented scoring engine. It might contain
  information about algorithm used, learning data etc.
- Implement its :py:meth:`~.ScoringEngine.get_metainfo` method to return the
  machine-friendly metadata about this scoring engine. For example, it could be
  a JSON formatted text with information about the data model used, its input
  and output data format, column names, etc.
- Implement its :py:meth:`~.ScoringEngine.calculate_score` method to return the
  result calculated by this scoring engine.

Here is an example showing how you can write a plugin called ``NewScorer``:

.. code-block:: python

    # filepath: thirdparty/new.py
    # import path: thirdparty.new
    from watcher.decision_engine.scoring import base


    class NewScorer(base.ScoringEngine):

        def get_name(self):
            return 'new_scorer'

        def get_description(self):
            return ''

        def get_metainfo(self):
            return """{
                "feature_columns": [
                    "column1",
                    "column2",
                    "column3"],
                "result_columns": [
                    "value",
                    "probability"]
                }"""

        def calculate_score(self, features):
            return '[12, 0.83]'

As you can see in the above example, the
:py:meth:`~.ScoringEngine.calculate_score` method returns a string. Both this
class and the client (caller) should perform all the necessary serialization
or deserialization.


(Optional) Create a new scoring engine container plugin
=======================================================

Optionally, it's possible to implement a container plugin, which can return a
list of scoring engines. This list can be re-evaluated multiple times during
the lifecycle of :ref:`Watcher Decision Engine
<watcher_decision_engine_definition>` and synchronized with :ref:`Watcher
Database <watcher_database_definition>` using the ``watcher-sync`` command line
tool.

Below is an example of a container using some scoring engine implementation
that is simply made of a client responsible for communicating with a real
scoring engine deployed as a web service on external servers:

.. code-block:: python

    class NewScoringContainer(base.ScoringEngineContainer):

        @classmethod
        def get_scoring_engine_list(self):
            return [
                RemoteScoringEngine(
                    name='scoring_engine1',
                    description='Some remote Scoring Engine 1',
                    remote_url='http://engine1.example.com/score'),
                RemoteScoringEngine(
                    name='scoring_engine2',
                    description='Some remote Scoring Engine 2',
                    remote_url='http://engine2.example.com/score'),
            ]


Abstract Plugin Class
=====================

Here below is the abstract
:py:class:`watcher.decision_engine.scoring.base.ScoringEngine` class:

.. autoclass:: watcher.decision_engine.scoring.base.ScoringEngine
    :members:
    :special-members: __init__
    :noindex:


Abstract Plugin Container Class
===============================

Here below is the abstract :py:class:`~.ScoringContainer` class:

.. autoclass:: watcher.decision_engine.scoring.base.ScoringEngineContainer
    :members:
    :special-members: __init__
    :noindex:


.. _scoring_engine_plugin_add_entrypoint:

Add a new entry point
=====================

In order for the Watcher Decision Engine to load your new scoring engine, it
must be registered as a named entry point under the ``watcher_scoring_engines``
entry point of your ``setup.py`` file. If you are using pbr_, this entry point
should be placed in your ``setup.cfg`` file.

The name you give to your entry point has to be unique and should be the same
as the value returned by the :py:meth:`~.ScoringEngine.get_name` method of your
strategy.

Here below is how you would proceed to register ``NewScorer`` using pbr_:

.. code-block:: ini

    [entry_points]
    watcher_scoring_engines =
        new_scorer = thirdparty.new:NewScorer


To get a better understanding on how to implement a more advanced scoring
engine, have a look at the :py:class:`~.DummyScorer` class. This implementation
is not really using machine learning, but other than that it contains all the
pieces which the "real" implementation would have.

In addition, for some use cases there is a need to register a list (possibly
dynamic, depending on the implementation and configuration) of scoring engines
in a single plugin, so there is no need to restart :ref:`Watcher Decision
Engine <watcher_decision_engine_definition>` every time such list changes. For
these cases, an additional ``watcher_scoring_engine_containers`` entry point
can be used.

For the example how to use scoring engine containers, please have a look at
the :py:class:`~.DummyScoringContainer` and the way it is configured in
``setup.cfg``. For new containers it could be done like this:

.. code-block:: ini

    [entry_points]
    watcher_scoring_engine_containers =
        new_scoring_container = thirdparty.new:NewContainer

.. _pbr: https://docs.openstack.org/pbr/latest/


Using scoring engine plugins
============================

The Watcher Decision Engine service will automatically discover any installed
plugins when it is restarted. If a Python package containing a custom plugin is
installed within the same environment as Watcher, Watcher will automatically
make that plugin available for use.

At this point, Watcher will scan and register inside the :ref:`Watcher Database
<watcher_database_definition>` all the scoring engines you implemented upon
restarting the :ref:`Watcher Decision Engine
<watcher_decision_engine_definition>`.

In addition, ``watcher-sync`` tool can be used to trigger :ref:`Watcher
Database <watcher_database_definition>` synchronization. This might be used for
"dynamic" scoring containers, which can return different scoring engines based
on some external configuration (if they support that).
