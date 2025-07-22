================
Aetos datasource
================

Synopsis
--------
The Aetos datasource allows Watcher to use an Aetos reverse proxy server as the
source for collected metrics used by the Watcher decision engine. Aetos is a
multi-tenant aware reverse proxy that sits in front of a Prometheus server and
provides Keystone authentication and role-based access control. The Aetos
datasource uses Keystone service discovery to locate the Aetos endpoint and
requires authentication via Keystone tokens.

Requirements
-------------
The Aetos datasource has the following requirements:

* An Aetos reverse proxy server deployed in front of Prometheus
* Aetos service registered in Keystone with service type 'metric-storage'
* Valid Keystone credentials for Watcher with admin or service role
* Prometheus metrics with appropriate labels (same as direct Prometheus access)

Like the Prometheus datasource, it is required that Prometheus metrics contain
a label to identify the hostname of the exporter from which the metric was
collected. This is used to match against the Watcher cluster model
``ComputeNode.hostname``. The default for this label is ``fqdn`` and in the
prometheus scrape configs would look like:

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
the list of values assigned to the label in the Prometheus targets.
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
override this default to any other label name that stores the ``uuid``.

Limitations
-----------
The Aetos datasource shares the same limitations as the Prometheus datasource:

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
``DataSourceBase`` metrics providers. In the case of Aetos (like Prometheus),
we do not fetch and then process individual metrics across the specified time
period. Instead we use the PromQL querying operators and functions, so that the
server itself will process the request across the specified parameters and
then return the result. So ``granularity`` parameter is redundant and remains
unused for the Aetos implementation of ``statistic_aggregation``. The
granularity of the data fetched by Prometheus server is specified in
configuration as the server ``scrape_interval`` (current default 15 seconds).

Additionally, there is a slight performance impact compared to direct
Prometheus access. Since Aetos acts as a reverse proxy in front of Prometheus,
there is an additional step for each request, resulting in slightly longer
delays.

Configuration
-------------
A deployer must set the ``datasources`` parameter to include ``aetos``
under the watcher_datasources section of watcher.conf (or add ``aetos`` in
datasources for a specific strategy if preferred eg. under the
``[watcher_strategies.workload_stabilization]`` section).

.. note::
   Having both Prometheus and Aetos datasources configured at the same time
   is not supported and will result in a configuration error. Allowing this
   can be investigated in the future if a need or a proper use case is
   identified.

The watcher.conf configuration file is also used to set the parameter values
required by the Watcher Aetos data source. The configuration can be
added under the ``[aetos_client]`` section and the available options are
duplicated below from the code as they are self documenting:

.. code-block::

    cfg.StrOpt('interface',
               default='public',
               choices=['internal', 'public', 'admin'],
               help="Type of endpoint to use in keystoneclient."),
    cfg.StrOpt('region_name',
               help="Region in Identity service catalog to use for "
                    "communication with the OpenStack service."),
    cfg.StrOpt('fqdn_label',
               default='fqdn',
               help="The label that Prometheus uses to store the fqdn of "
                    "exporters. Defaults to 'fqdn'."),
    cfg.StrOpt('instance_uuid_label',
               default='resource',
               help="The label that Prometheus uses to store the uuid of "
                    "OpenStack instances. Defaults to 'resource'."),


Authentication and Service Discovery
------------------------------------
Unlike the Prometheus datasource which requires explicit host and port
configuration, the Aetos datasource uses Keystone service discovery to
automatically locate the Aetos endpoint. The datasource:

1. Uses the configured Keystone credentials to authenticate
2. Searches the service catalog for a service with type 'metric-storage'
3. Uses the discovered endpoint URL to connect to Aetos
4. Attaches a Keystone token to each request for authentication

If the Aetos service is not registered in Keystone, the datasource will
fail to initialize and prevent the decision engine from starting.

So a sample watcher.conf configured to use the Aetos datasource would look
like the following:

.. code-block::

    [watcher_datasources]

    datasources = aetos

    [aetos_client]

    interface = public
    region_name = RegionOne
    fqdn_label = fqdn
