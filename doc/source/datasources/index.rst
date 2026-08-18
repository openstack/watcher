Datasources
===========

.. note::
   The Prometheus datasource is deprecated as of the 2026.1 release and will
   be removed in a future release. Use the Aetos datasource instead, which
   provides the same functionality with added multi-tenancy and Keystone
   authentication support. See the :doc:`migrate-prometheus-to-aetos` guide.

.. toctree::
   :maxdepth: 1

   aetos
   grafana
   migrate-prometheus-to-aetos
   prometheus

DataSource base class
---------------------

All datasource backends inherit from ``DataSourceBase`` and share a common
metric-retrieval interface.

Metric retrieval
~~~~~~~~~~~~~~~~

``statistic_aggregation(resource, resource_type, meter_name, period,
aggregate, granularity)`` is the **public** method used by strategies to
retrieve a metric value. It is implemented in the base class and manages a
per-instance in-memory cache backed by
:class:`~watcher.decision_engine.datasources.cache.MetricDataCache`.
The cache key encodes all five parameters: ``(resource.uuid, meter_name,
aggregate, period, granularity)``. On the first call for a given combination
of these five values, the result is fetched from the backend and stored in the
cache. Subsequent calls with identical arguments return the cached value
without contacting the backend again.

Each concrete datasource implements ``_statistic_aggregation`` with the same
signature. That private method contains the backend-specific query logic and
is called by the base class on a cache miss.

Cache injection
~~~~~~~~~~~~~~~

``inject_metric(resource_uuid, metric, aggregation, period, value,
granularity=300)`` writes a value directly into the cache without querying the
backend. Any subsequent ``statistic_aggregation`` call with the same
``resource_uuid``, ``metric``, ``aggregation``, ``period``, and
``granularity`` will return the injected value.

+-------------------+----------------------------------------------+
| Parameter         | Description                                  |
+===================+==============================================+
| ``resource_uuid`` | UUID of the resource                         |
+-------------------+----------------------------------------------+
| ``metric``        | Metric name as a key from ``METRIC_MAP``     |
+-------------------+----------------------------------------------+
| ``aggregation``   | Aggregation method (e.g. ``'mean'``)         |
+-------------------+----------------------------------------------+
| ``period``        | Time span in seconds the value covers        |
+-------------------+----------------------------------------------+
| ``value``         | The metric value to store                    |
+-------------------+----------------------------------------------+
| ``granularity``   | Granularity in seconds (default ``300``)     |
+-------------------+----------------------------------------------+

Implementing a new datasource
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A new datasource must:

* Inherit from ``DataSourceBase`` and call ``super().__init__()`` to
  initialise the metric cache.
* Override ``_statistic_aggregation`` with the backend-specific query logic.
* Override the remaining abstract methods defined in ``DataSourceBase``
  (``check_availability``, ``list_metrics``, ``statistic_series``, and the
  ``get_host_*`` / ``get_instance_*`` convenience methods).

.. warning::

   Overriding ``statistic_aggregation`` in a concrete datasource will bypass
   the base-class caching system. If you do so, the datasource becomes
   responsible for implementing its own caching strategy and must also provide
   its own ``inject_metric`` implementation so that callers can pre-populate
   the cache with externally computed values.
