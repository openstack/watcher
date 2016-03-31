..
      Except where otherwise noted, this document is licensed under Creative
      Commons Attribution 3.0 License.  You can view the license at:

          https://creativecommons.org/licenses/by/3.0/

===================
Configuring Watcher
===================

This document is continually updated and reflects the latest
available code of the Watcher service.

Service overview
================

The Watcher system is a collection of services that provides support to
optimize your IAAS plateform. The Watcher service may, depending upon
configuration, interact with several other OpenStack services. This includes:

- the OpenStack Identity service (`keystone`_) for request authentication and
  to locate other OpenStack services
- the OpenStack Telemetry service (`ceilometer`_) for consuming the resources
  metrics
- the OpenStack Compute service (`nova`_) works with the Watcher service and
  acts as a user-facing API for instance migration.

The Watcher service includes the following components:

- ``watcher-decision-engine``: runs audit on part of your IAAS and return an
  action plan in order to optimize resource placement.
- ``watcher-api``: A RESTful API that processes application requests by sending
  them to the watcher-decision-engine over RPC.
- ``watcher-applier``: applies the action plan.
- `python-watcherclient`_: A command-line interface (CLI) for interacting with
  the Watcher service.
- `watcher-dashboard`_: An Horizon plugin for interacting with the Watcher
  service.

Additionally, the Bare Metal service has certain external dependencies, which
are very similar to other OpenStack services:

- A database to store audit and action plan information and state. You can set
  the database back-end type and location.
- A queue. A central hub for passing messages, such as `RabbitMQ`_.

Optionally, one may wish to utilize the following associated projects for
additional functionality:

- `watcher metering`_: an alternative to collect and push metrics to the
  Telemetry service.

.. _`keystone`: https://github.com/openstack/keystone
.. _`ceilometer`: https://github.com/openstack/ceilometer
.. _`nova`: https://github.com/openstack/nova
.. _`python-watcherclient`: https://github.com/openstack/python-watcherclient
.. _`watcher-dashboard`: https://github.com/openstack/watcher-dashboard
.. _`watcher metering`: https://github.com/b-com/watcher-metering
.. _`RabbitMQ`: https://www.rabbitmq.com/

Install and configure prerequisites
===================================

You can configure Watcher services to run on separate nodes or the same node.
In this guide, the components run on one node, typically the Controller node.

This section shows you how to install and configure the services.

It assumes that the Identity, Image, Compute, and Networking services
have already been set up.

.. _identity-service_configuration:

Configure the Identity service for the Watcher service
------------------------------------------------------

#. Create the Watcher service user (eg ``watcher``). The service uses this to
   authenticate with the Identity Service. Use the
   ``KEYSTONE_SERVICE_PROJECT_NAME`` project (named ``service`` by default in
   devstack) and give the user the ``admin`` role:

    .. code-block:: bash

      $ keystone user-create --name=watcher --pass=WATCHER_PASSWORD \
        --email=watcher@example.com \
        --tenant=KEYSTONE_SERVICE_PROJECT_NAME
      $ keystone user-role-add --user=watcher \
        --tenant=KEYSTONE_SERVICE_PROJECT_NAME --role=admin
      $ keystone user-role-add --user=watcher --tenant=admin --role=admin

   or (by using python-openstackclient 1.8.0+)

     .. code-block:: bash

      $ openstack user create  --password WATCHER_PASSWORD --enable \
        --email watcher@example.com watcher \
        --project=KEYSTONE_SERVICE_PROJECT_NAME
      $ openstack role add --project KEYSTONE_SERVICE_PROJECT_NAME \
        --user watcher admin
      $ openstack role add --user watcher --project admin admin


#. You must register the Watcher Service with the Identity Service so that
   other OpenStack services can locate it. To register the service:

    .. code-block:: bash

      $ keystone service-create --name=watcher --type=infra-optim \
        --description="Infrastructure Optimization service"

   or (by using python-openstackclient 1.8.0+)

    .. code-block:: bash

      $ openstack service create --name watcher infra-optim \
        --description="Infrastructure Optimization service"

#. Create the endpoints by replacing YOUR_REGION and
   ``WATCHER_API_[PUBLIC|ADMIN|INTERNAL]_IP`` with your region and your
   Watcher Service's API node IP addresses (or FQDN):

    .. code-block:: bash

      $ keystone endpoint-create \
      --service-id=the_service_id_above \
      --publicurl=http://WATCHER_API_PUBLIC_IP:9322 \
      --internalurl=http://WATCHER_API_INTERNAL_IP:9322 \
      --adminurl=http://WATCHER_API_ADMIN_IP:9322

   or (by using python-openstackclient 1.8.0+)

    .. code-block:: bash

      $ openstack endpoint create --region YOUR_REGION watcher \
        --publicurl http://WATCHER_API_PUBLIC_IP:9322 \
        --internalurl http://WATCHER_API_INTERNAL_IP:9322 \
        --adminurl http://WATCHER_API_ADMIN_IP:9322

.. _watcher-db_configuration:

Set up the database for Watcher
-------------------------------

The Watcher service stores information in a database. This guide uses the
MySQL database that is used by other OpenStack services.

#. In MySQL, create a ``watcher`` database that is accessible by the
   ``watcher`` user. Replace WATCHER_DBPASSWORD
   with the actual password::

    $ mysql -u root -p

    mysql> CREATE DATABASE watcher CHARACTER SET utf8;
    mysql> GRANT ALL PRIVILEGES ON watcher.* TO 'watcher'@'localhost' \
    IDENTIFIED BY 'WATCHER_DBPASSWORD';
    mysql> GRANT ALL PRIVILEGES ON watcher.* TO 'watcher'@'%' \
    IDENTIFIED BY 'WATCHER_DBPASSWORD';


Configure the Watcher service
=============================

The Watcher service is configured via its configuration file. This file
is typically located at ``/etc/watcher/watcher.conf``.

You can easily generate and update a sample configuration file
named :ref:`watcher.conf.sample <watcher_sample_configuration_files>` by using
these following commands::

    $ git clone git://git.openstack.org/openstack/watcher
    $ cd watcher/
    $ tox -econfig
    $ vi etc/watcher/watcher.conf.sample


The configuration file is organized into the following sections:

* ``[DEFAULT]`` - General configuration
* ``[api]`` - API server configuration
* ``[database]`` - SQL driver configuration
* ``[keystone_authtoken]`` - Keystone Authentication plugin configuration
* ``[watcher_clients_auth]`` - Keystone auth configuration for clients
* ``[watcher_applier]`` - Watcher Applier module configuration
* ``[watcher_decision_engine]`` - Watcher Decision Engine module configuration
* ``[oslo_messaging_rabbit]`` - Oslo Messaging RabbitMQ driver configuration
* ``[ceilometer_client]`` - Ceilometer client configuration
* ``[cinder_client]`` - Cinder client configuration
* ``[glance_client]`` - Glance client configuration
* ``[nova_client]`` - Nova client configuration
* ``[neutron_client]`` - Neutron client configuration

The Watcher configuration file is expected to be named
``watcher.conf``. When starting Watcher, you can specify a different
configuration file to use with ``--config-file``. If you do **not** specify a
configuration file, Watcher will look in the following directories for a
configuration file, in order:

* ``~/.watcher/``
* ``~/``
* ``/etc/watcher/``
* ``/etc/``


Although some configuration options are mentioned here, it is recommended that
you review all the `available options
<https://git.openstack.org/cgit/openstack/watcher/tree/etc/watcher/watcher.conf.sample>`_
so that the watcher service is configured for your needs.

#. The Watcher Service stores information in a database. This guide uses the
   MySQL database that is used by other OpenStack services.

   Configure the location of the database via the ``connection`` option. In the
   following, replace WATCHER_DBPASSWORD with the password of your ``watcher``
   user, and replace DB_IP with the IP address where the DB server is located::

    [database]
    ...

    # The SQLAlchemy connection string used to connect to the
    # database (string value)
    #connection=<None>
    connection = mysql://watcher:WATCHER_DBPASSWORD@DB_IP/watcher?charset=utf8

#. Configure the Watcher Service to use the RabbitMQ message broker by
   setting one or more of these options. Replace RABBIT_HOST with the
   IP address of the RabbitMQ server, RABBITMQ_USER and RABBITMQ_PASSWORD
   by the RabbitMQ server login credentials ::

    [DEFAULT]

    # The messaging driver to use, defaults to rabbit. Other drivers
    # include qpid and zmq. (string value)
    #rpc_backend = rabbit

    # The default exchange under which topics are scoped. May be
    # overridden by an exchange name specified in the transport_url
    # option. (string value)
    control_exchange = watcher

    ...

    [oslo_messaging_rabbit]

    # The username used by the message broker (string value)
    rabbit_userid = RABBITMQ_USER

    # The password of user used by the message broker (string value)
    rabbit_password = RABBITMQ_PASSWORD

    # The host where the message brokeris installed (string value)
    rabbit_host = RABBIT_HOST

    # The port used bythe message broker (string value)
    #rabbit_port = 5672


#. Watcher API shall validate the token provided by every incoming request,
   via keystonemiddleware, which requires the Watcher service to be configured
   with the right credentials for the Identity service.

   In the configuration section here below:

   * replace IDENTITY_IP with the IP of the Identity server
   * replace WATCHER_PASSWORD with the password you chose for the ``watcher``
     user
   * replace KEYSTONE_SERVICE_PROJECT_NAME with the name of project created
     for OpenStack services (e.g. ``service``) ::

        [keystone_authtoken]

        # Authentication type to load (unknown value)
        # Deprecated group/name - [DEFAULT]/auth_plugin
        #auth_type = <None>
        auth_type = password

        # Authentication URL (unknown value)
        #auth_url = <None>
        auth_url = http://IDENTITY_IP:35357

        # Username (unknown value)
        # Deprecated group/name - [DEFAULT]/username
        #username = <None>
        username=watcher

        # User's password (unknown value)
        #password = <None>
        password = WATCHER_PASSWORD

        # Domain ID containing project (unknown value)
        #project_domain_id = <None>
        project_domain_id = default

        # User's domain id (unknown value)
        #user_domain_id = <None>
        user_domain_id = default

        # Project name to scope to (unknown value)
        # Deprecated group/name - [DEFAULT]/tenant-name
        #project_name = <None>
        project_name = KEYSTONE_SERVICE_PROJECT_NAME

#. Watcher's decision engine and applier interact with other OpenStack
   projects through those projects' clients. In order to instantiate these
   clients, Watcher needs to request a new session from the Identity service
   using the right credentials.

   In the configuration section here below:

   * replace IDENTITY_IP with the IP of the Identity server
   * replace WATCHER_PASSWORD with the password you chose for the ``watcher``
     user
   * replace KEYSTONE_SERVICE_PROJECT_NAME with the name of project created
     for OpenStack services (e.g. ``service``) ::

        [watcher_clients_auth]

        # Authentication type to load (unknown value)
        # Deprecated group/name - [DEFAULT]/auth_plugin
        #auth_type = <None>
        auth_type = password

        # Authentication URL (unknown value)
        #auth_url = <None>
        auth_url = http://IDENTITY_IP:35357

        # Username (unknown value)
        # Deprecated group/name - [DEFAULT]/username
        #username = <None>
        username=watcher

        # User's password (unknown value)
        #password = <None>
        password = WATCHER_PASSWORD

        # Domain ID containing project (unknown value)
        #project_domain_id = <None>
        project_domain_id = default

        # User's domain id (unknown value)
        #user_domain_id = <None>
        user_domain_id = default

        # Project name to scope to (unknown value)
        # Deprecated group/name - [DEFAULT]/tenant-name
        #project_name = <None>
        project_name = KEYSTONE_SERVICE_PROJECT_NAME

#. Configure the clients to use a specific version if desired. For example, to
   configure Watcher to use a Nova client with version 2.1, use::

    [nova_client]

    # Version of Nova API to use in novaclient. (string value)
    #api_version = 2
    api_version = 2.1

#. Create the Watcher Service database tables::

    $ watcher-db-manage --config-file /etc/watcher/watcher.conf create_schema

#. Start the Watcher Service::

    $ watcher-api &&  watcher-decision-engine && watcher-applier

Configure Nova compute
======================

Please check your hypervisor configuration to correctly handle
`instance migration`_.

.. _`instance migration`: http://docs.openstack.org/admin-guide-cloud/compute-configuring-migrations.html

Configure Measurements
======================

You can configure and install Ceilometer by following the documentation below :

#. http://docs.openstack.org/developer/ceilometer
#. http://docs.openstack.org/kilo/install-guide/install/apt/content/ceilometer-nova.html

The built-in strategy 'basic_consolidation' provided by watcher requires
"**compute.node.cpu.percent**" and "**cpu_util**" measurements to be collected
by Ceilometer.
The measurements available depend on the hypervisors that OpenStack manages on
the specific implementation.
You can find the measurements available per hypervisor and OpenStack release on
the OpenStack site.
You can use 'ceilometer meter-list' to list the available meters.

For more information:
http://docs.openstack.org/developer/ceilometer/measurements.html

Ceilometer is designed to collect measurements from OpenStack services and from
other external components. If you would like to add new meters to the currently
existing ones, you need to follow the documentation below:

#. http://docs.openstack.org/developer/ceilometer/new_meters.html

The Ceilometer collector uses a pluggable storage system, meaning that you can
pick any database system you prefer.
The original implementation has been based on MongoDB but you can create your
own storage driver using whatever technology you want.
For more information : https://wiki.openstack.org/wiki/Gnocchi


Workers
=======

You can define a number of workers for the Decision Engine and the Applier.

If you want to create and run more audits simultaneously, you have to raise
the number of workers used by the Decision Engine::

    [watcher_decision_engine]

    ...

    # The maximum number of threads that can be used to execute strategies
    # (integer value)
    #max_workers = 2


If you want to execute simultaneously more recommended action plans, you
have to raise the number of workers used by the Applier::

    [watcher_applier]

    ...

    # Number of workers for applier, default value is 1. (integer value)
    # Minimum value: 1
    #workers = 1

