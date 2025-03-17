=====================
Prometheus datasource
=====================

Synopsis
--------
The Prometheus datasource allows Watcher to use a Prometheus server as the
source for collected metrics used by the Watcher decision engine. At minimum
deployers must configure the ``host`` and ``port`` at which the Prometheus
server is listening.

Requirements
-------------
It is required that Prometheus metrics contain a label to identify the hostname
of the exporter from which the metric was collected. This is used to match
against the Watcher cluster model ``ComputeNode.hostname``. The default for
this label is ``fqdn`` and in the prometheus scrape configs would look like:

.. code-block::

    scrape_configs:
    - job_name: node
      static_configs:
     - targets: ['10.1.2.3:9100']
        labels:
          fqdn: "testbox.controlplane.domain"

This default can be overridden when a deployer uses a different label to
identify the exporter host (for example ``hostname`` or ``host``, or any other
label, as long as it identifies the host).

Internally this label is used in creating ``fqdn_instance_labels``, containing
the list of values assigned to the the label in the Prometheus targets.
The elements of the resulting fqdn_instance_labels are expected to match the
``ComputeNode.hostname`` used in the Watcher decision engine cluster model.
An example ``fqdn_instance_labels`` is the following:

.. code-block::

    [
     'ena.controlplane.domain',
     'dio.controlplane.domain',
     'tria.controlplane.domain',
    ]

For instance metrics, it is required that Prometheus contains a label
with the uuid of the OpenStack instance in each relevant metric. By default,
the datasource will look for the label ``resource``. The
``instance_uuid_label`` config option in watcher.conf allows deployers to
override this default to any other label name that stores the  ``uuid``.

Limitations
-----------
The current implementation doesn't support the ``statistic_series`` function of
the Watcher ``class DataSourceBase``. It is expected that the
``statistic_aggregation`` function (which is implemented) is sufficient in
providing the **current** state of the managed resources in the cluster.
The ``statistic_aggregation`` function defaults to querying back 300 seconds,
starting from the present time (the time period is a function parameter and
can be set to a value as required). Implementing the ``statistic_series`` can
always be re-visited if the requisite interest and work cycles are volunteered
by the interested parties.

One further note about a limitation in the implemented
``statistic_aggregation`` function. This function is defined with a
``granularity`` parameter, to be used when querying whichever of the Watcher
``DataSourceBase`` metrics providers. In the case of Prometheus, we do not
fetch and then process individual metrics across the specified time period.
Instead we use the PromQL querying operators and functions, so that the
server itself will process the request across the specified parameters and
then return the result. So ``granularity`` parameter is redundant and remains
unused for the Prometheus implementation of ``statistic_aggregation``. The
granularity of the data fetched by Prometheus server is specified in
configuration as the server ``scrape_interval`` (current default 15 seconds).

Configuration
-------------
A deployer must set the ``datasources`` parameter to include ``prometheus``
under the watcher_datasources section of watcher.conf (or add ``prometheus`` in
datasources for a specific strategy if preferred eg. under the
``[watcher_strategies.workload_stabilization]`` section).

The watcher.conf configuration file is also used to set the parameter values
required by the Watcher Prometheus data source. The configuration can be
added under the ``[prometheus_client]`` section and the available options are
duplicated below from the code as they are self documenting:

.. code-block::

    cfg.StrOpt('host',
               help="The hostname or IP address for the prometheus server."),
    cfg.StrOpt('port',
               help="The port number used by the prometheus server."),
    cfg.StrOpt('fqdn_label',
               default="fqdn",
               help="The label that Prometheus uses to store the fqdn of "
                    "exporters. Defaults to 'fqdn'."),
    cfg.StrOpt('instance_uuid_label',
               default="resource",
               help="The label that Prometheus uses to store the uuid of "
                    "OpenStack instances. Defaults to 'resource'."),
    cfg.StrOpt('username',
               help="The basic_auth username to use to authenticate with the "
                    "Prometheus server."),
    cfg.StrOpt('password',
               secret=True,
               help="The basic_auth password to use to authenticate with the "
                    "Prometheus server."),
    cfg.StrOpt('cafile',
               help="Path to the CA certificate for establishing a TLS "
                    "connection with the Prometheus server."),
    cfg.StrOpt('certfile',
               help="Path to the client certificate for establishing a TLS "
                    "connection with the Prometheus server."),
    cfg.StrOpt('keyfile',
               help="Path to the client key for establishing a TLS "
                    "connection with the Prometheus server."),

The ``host`` and ``port`` are **required** configuration options which have
no set default. These specify the hostname (or IP) and port for at which
the Prometheus server is listening. The ``fqdn_label`` allows deployers to
override the required metric label used to match Prometheus node exporters
against the Watcher ComputeNodes in the Watcher decision engine cluster data
model. The default is ``fqdn`` and deployers can specify any other value
(e.g. if they have an equivalent but different label such as ``host``).

So a sample watcher.conf configured to use the Prometheus server at
``10.2.3.4:9090`` would look like the following:

.. code-block::

    [watcher_datasources]

    datasources = prometheus

    [prometheus_client]

    host = 10.2.3.4
    port = 9090
    fqdn_label = fqdn
