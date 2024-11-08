==================
Grafana datasource
==================

Synopsis
--------

Grafana can interface with many different types of storage backends that
Grafana calls datasources_. Since the term datasources causes significant
confusion by overlapping definitions used in Watcher these **datasources are
called projects instead**. Some examples of supported projects are InfluxDB
or Elasticsearch while others might be more familiar such as Monasca or
Gnocchi. The Grafana datasource provides the functionality to retrieve metrics
from Grafana for different projects. This functionality is achieved by using
the proxy interface exposed in Grafana to communicate with Grafana projects
directly.

Background
**********

Since queries to retrieve metrics from Grafana are proxied to the project the
format of these queries will change significantly depending on the type of
project. The structure of the projects themselves will also change
significantly as they are structured by users and administrators. For instance,
some developers might decide to store metrics about compute_nodes in MySQL and
use the UUID as primary key while others use InfluxDB and use the hostname as
primary key. Furthermore, datasources in Watcher should return metrics in
specific units strictly defined in the baseclass_ depending on how the units
are stored in the projects they might require conversion before being returned.
The flexible configuration parameters of the Grafana datasource allow to
specify exactly how the deployment is configured and this will enable to
correct retrieval of metrics and with the correct units.

.. _datasources: https://grafana.com/plugins?type=datasource
.. _baseclass: https://github.com/openstack/watcher/blob/584eeefdc8/watcher/datasources/base.py

Requirements
------------

The use of the Grafana datasource requires a reachable Grafana endpoint and an
authentication token for access to the desired projects. The projects behind
Grafana will need to contain the metrics for compute_nodes_ or instances_ and
these need to be identifiable by an attribute of the Watcher datamodel_ for
instance hostname or UUID.

.. _compute_nodes: https://opendev.org/openstack/watcher/src/branch/master/watcher/decision_engine/model/element/node.py
.. _instances: https://opendev.org/openstack/watcher/src/branch/master/watcher/decision_engine/model/element/instance.py
.. _datamodel: https://opendev.org/openstack/watcher/src/branch/master/watcher/decision_engine/model/element

Limitations
***********

* Only the InfluxDB project is currently supported [#f1]_.
* All metrics must be retrieved from the same Grafana endpoint (same URL).
* All metrics must be retrieved with the same authentication token.

.. [#f1] A base class for projects is available_ and easily extensible.
.. _available: https://review.opendev.org/#/c/649341/24/watcher/datasources/grafana_translator/base.py

Configuration
-------------

Several steps are required in order to use the Grafana datasource, Most steps
are related configuring Watcher to match the deployed Grafana setup such as
queries proxied to the project or the type of project for any given metric.
Most of the configuration can either be supplied via the traditional
configuration file or in a `special yaml`_ file.

.. _special yaml: https://specs.openstack.org/openstack/watcher-specs/specs/train/approved/file-based-metricmap.html

token
*****

First step is to generate an access token with access to the required projects.
This can be done from the api_ or from the web interface_. Tokens generated
from the web interface will have the same access to projects as the user that
created them while using the cli allows to generate a key for a specific
role.The token will only be displayed once so store it well. This token will go
into the configuration file later and this parameter can not be placed in the
yaml.

.. _api: https://grafana.com/docs/http_api/auth/#create-api-key
.. _interface: https://grafana.com/docs/http_api/auth/#create-api-token

base_url
********

Next step is supplying the base url of the Grafana endpoint. The base url
parameter will need to specify the type of http protocol and the use of
plain text http is strongly discouraged due to the transmission of the access
token. Additionally the path to the proxy interface needs to be supplied as
well in case Grafana is placed in a sub directory of the web server. An example
would be: ``https://mygrafana.org/api/datasource/proxy/`` were
``/api/datasource/proxy`` is the default path without any subdirectories.
Likewise, this parameter can not be placed in the yaml.

To prevent many errors from occurring and potentially filing the logs files it
is advised to specify the desired datasource in the configuration as it would
prevent the datasource manager from having to iterate and try possible
datasources with the launch of each audit. To do this specify
``datasources`` in the ``[watcher_datasources]`` group.

The current configuration that is required to be placed in the traditional
configuration file would look like the following:

.. code-block:: shell

    [grafana_client]
    token = 0JLbF0oB4R3Q2Fl337Gh4Df5VN12D3adBE3f==
    base_url = https://mygranfa.org/api/datasource/proxy

    [watcher_datasources]
    datasources = grafana

metric parameters
*****************

The last five remaining configuration parameters can all be placed both in the
traditional configuration file or in the yaml, however, it is not advised to
mix and match but in the case it does occur the yaml would override the
settings from the traditional configuration file. All five of these parameters
are dictionaries mapping specific metrics to a configuration parameter. For
instance the ``project_id_map`` will specify the specific project id in Grafana
to be used. The parameters are named as follow:

* project_id_map
* database_map
* translator_map
* attribute_map
* query_map

These five parameters are named differently if configured using the yaml
configuration file. The parameters are named as follows and are in
identical order as to the list of the traditional configuration file:

* project
* db
* translator
* attribute
* query

When specified in the yaml the parameters are no longer dictionaries instead
each parameter needs to be defined per metric as sub-parameters. Examples of
these parameters configured for both the yaml and traditional configuration
are described at the end of this document.

project_id
**********

The project id's can only be determined by someone with the admin role in
Grafana as that role is required to open the list of projects. The list of
projects can be found on ``/datasources`` in the web interface but
unfortunately it does not immediately display the project id. To display
the id one can best hover the mouse over the projects and the url will show the
project id's for example ``/datasources/edit/7563``. Alternatively the entire
list of projects can be retrieved using the `REST api`_. To easily make
requests to the REST api a tool such as Postman can be used.

.. _REST api: https://grafana.com/docs/http_api/data_source/#get-all-datasources

database
********

The database is the parameter for the schema / database that is actually
defined in the project. For instance, if the project would be based on MySQL
this is were the name of schema used within the MySQL server would be
specified. For many different projects it is possible to list all the databases
currently available. Tools like Postman can be used to list all the available
databases per project. For InfluxDB based projects this would be with the
following path and query, however be sure to construct these request in Postman
as the header needs to contain the authorization token:

.. code-block:: shell

    https://URL.DOMAIN/api/datasources/proxy/PROJECT_ID/query?q=SHOW%20DATABASES

translator
**********

Each translator is for a specific type of project will have a uniquely
identifiable name and the baseclass allows to easily support new types of
projects such as elasticsearch or prometheus. Currently only InfluxDB based
projects are supported as a result the only valid value for this parameter is `
influxdb`.

attribute
*********

The attribute parameter specifies which attribute to use from Watcher's
data model in order to construct the query. The available attributes differ
per type of object in the data model but the following table shows the
attributes for ComputeNodes, Instances and IronicNodes.

+-----------------+-----------------+--------------------+
| ComputeNode     | Instance        | IronicNode         |
+=================+=================+====================+
| uuid            | uuid            | uuid               |
+-----------------+-----------------+--------------------+
| id              | name            | human_id           |
+-----------------+-----------------+--------------------+
| hostname        | project_id      | power_state        |
+-----------------+-----------------+--------------------+
| status          | watcher_exclude | maintenance        |
+-----------------+-----------------+--------------------+
| disabled_reason | locked          | maintenance_reason |
+-----------------+-----------------+--------------------+
| state           | metadata        | extra              |
+-----------------+-----------------+--------------------+
| memory          | state           |                    |
+-----------------+-----------------+--------------------+
| disk            | memory          |                    |
+-----------------+-----------------+--------------------+
| disk_capacity   | disk            |                    |
+-----------------+-----------------+--------------------+
| vcpus           | disk_capacity   |                    |
+-----------------+-----------------+--------------------+
|                 | vcpus           |                    |
+-----------------+-----------------+--------------------+

Many if not all of these attributes map to attributes of the objects that are
fetched from clients such as Nova. To see how these attributes are put into the
data model the following source files can be analyzed for Nova_ and Ironic_.

.. _Nova: https://opendev.org/openstack/watcher/src/branch/master/watcher/decision_engine/model/collector/nova.py#L304
.. _Ironic: https://opendev.org/openstack/watcher/src/branch/master/watcher/decision_engine/model/collector/ironic.py#L85

query
*****

The query is the single most important parameter it will be passed to the
project and should return the desired metric for the specific host and return
the value in the correct unit. The units for all available metrics are
documented in the `datasource baseclass`_. This might mean the query specified
in this parameter is responsible for converting the unit. The following query
demonstrates how such a conversion could be achieved and demonstrates the
conversion from bytes to megabytes.

.. code-block:: shell

    SELECT value/1000000 FROM memory...

Queries will be formatted using the .format string method within Python.
This format will currently have give attributes exposed to it labeled
``{0}`` through ``{4}``.
Every occurrence of these characters within the string will be replaced
with the specific attribute.

{0}
    is the aggregate typically ``mean``, ``min``, ``max`` but ``count``
    is also supported.
{1}
    is the attribute as specified in the attribute parameter.
{2}
    is the period of time to aggregate data over in seconds.
{3}
    is the granularity or the interval between data points in seconds.
{4}
    is translator specific and in the case of InfluxDB it will be used for
    retention_periods.

**InfluxDB**

Constructing the queries or rather anticipating how the results should look to
be correctly interpreted by Watcher can be a challenge. The following json
example demonstrates how what the result should look like and the query used to
get this result.

.. code-block:: json

    {
    "results": [
        {
            "statement_id": 0,
            "series": [
                {
                    "name": "vmstats",
                    "tags": {
                        "host": "autoserver01"
                    },
                    "columns": [
                        "time",
                        "mean"
                    ],
                    "values": [
                        [
                            1560848284284,
                            7680000
                        ]
                    ]
                }
            ]
        }
    ]
    }

.. code-block:: shell

    SELECT {0}("{0}_value") FROM "vmstats" WHERE host =~ /^{1}$/ AND
    "type_instance" =~ /^mem$/ AND time >= now() - {2}s GROUP BY host

.. _datasource baseclass: https://opendev.org/openstack/watcher/src/branch/master/watcher/datasources/base.py

Example configuration
---------------------

The example configurations will show both how to achieve the entire
configuration in the config file or use a combination of the regular file and
yaml. Using yaml to define all the parameters for each metric is recommended
since it has better human readability and supports mutli-line option
definitions.

Configuration file
******************

**It is important to note that the line breaks shown in between assignments of
parameters can not be used in the actual configuration and these are simply here
for readability reasons.**

.. code-block:: shell

    [grafana_client]
    # Authentication token to gain access (string value)
    # Note: This option can be changed without restarting.
    token = eyJrIjoiT0tTcG1pUlY2RnVKZTFVaDFsNFZXdE9ZWmNrMkZYbk==

    # first part of the url (including https:// or http://) up until project id
    # part. Example: https://secure.org/api/datasource/proxy/ (string value)
    # Note: This option can be changed without restarting.
    base_url = https://monitoring-grafana.com/api/datasources/proxy/

    # Project id as in url (integer value)
    # Note: This option can be changed without restarting.
    project_id_map = host_cpu_usage:1337,host_ram_usage:6969,
    instance_cpu_usage:1337,instance_ram_usage:9696

    # Mapping of grafana databases to datasource metrics. (dict value)
    # Note: This option can be changed without restarting.
    database_map = host_cpu_usage:monit_production,
    host_ram_usage:monit_production,instance_cpu_usage:prod_cloud,
    instance_ram_usage:prod_cloud

    translator_map = host_cpu_usage:influxdb,host_ram_usage:influxdb,
    instance_cpu_usage:influxdb,instance_ram_usage:influxdb

    attribute_map = host_cpu_usage:hostname,host_ram_usage:hostname,
    instance_cpu_usage:name,instance_ram_usage:name

    query_map = host_cpu_usage:SELECT 100-{0}("{0}_value") FROM {4}.cpu WHERE
    ("host" =~ /^{1}$/ AND "type_instance" =~/^idle$/ AND time > now()-{2}s),
    host_ram_usage:SELECT {0}("{0}_value")/1000000 FROM {4}.memory WHERE
     ("host" =~ /^{1}$/) AND "type_instance" =~ /^used$/ AND time >= now()-{2}s
     GROUP BY "type_instance",instance_cpu_usage:SELECT {0}("{0}_value") FROM
     "vmstats" WHERE host =~ /^{1}$/ AND "type_instance" =~ /^cpu$/ AND time >=
     now() - {2}s GROUP BY host,instance_ram_usage:SELECT {0}("{0}_value") FROM
     "vmstats" WHERE host =~ /^{1}$/ AND "type_instance" =~ /^mem$/ AND time >=
     now() - {2}s GROUP BY host

    [grafana_translators]

    retention_periods = one_week:10080,one_month:302400,five_years:525600

    [watcher_datasources]
    datasources = grafana

yaml
****

When using the yaml configuration file some parameters still need to be defined
using the regular configuration such as the path for the yaml file these
parameters are detailed below:

.. code-block:: shell

    [grafana_client]
    token = eyJrIjoiT0tTcG1pUlY2RnVKZTFVaDFsNFZXdE9ZWmNrMkZYbk==

    base_url = https://monitoring-grafana.com/api/datasources/proxy/

    [watcher_datasources]
    datasources = grafana

    [watcher_decision_engine]
    metric_map_path = /etc/watcher/metric_map.yaml

Using the yaml allows to more effectively define the parameters per metric with
greater human readability due to the availability of multi line options. These
multi line options are demonstrated in the query parameters.

.. code-block:: yaml

  grafana:
    host_cpu_usage:
      project: 1337
      db: monit_production
      translator: influxdb
      attribute: hostname
      query: >
          SELECT 100-{0}("{0}_value") FROM {4}.cpu
          WHERE ("host" =~ /^{1}$/ AND "type_instance" =~/^idle$/ AND
          time > now()-{2}s)
    host_ram_usage:
      project: 6969
      db: monit_production
      translator: influxdb
      attribute: hostname
      query: >
          SELECT {0}("{0}_value")/1000000 FROM {4}.memory WHERE
           ("host" =~ /^{1}$/) AND "type_instance" =~ /^used$/ AND time >=
           now()-{2}s GROUP BY "type_instance"
    instance_cpu_usage:
      project: 1337
      db: prod_cloud
      translator: influxdb
      attribute: name
      query: >
          SELECT {0}("{0}_value") FROM
           "vmstats" WHERE host =~ /^{1}$/ AND "type_instance" =~ /^cpu$/ AND
           time >= now() - {2}s GROUP BY host
    instance_ram_usage:
      project: 9696
      db: prod_cloud
      translator: influxdb
      attribute: name
      query: >
          SELECT {0}("{0}_value") FROM
           "vmstats" WHERE host =~ /^{1}$/ AND "type_instance" =~ /^mem$/ AND
           time >= now() - {2}s GROUP BY host

External Links
--------------

- `List of Grafana datasources <https://grafana.com/plugins?type=datasource>`_
