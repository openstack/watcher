Prerequisites
-------------

Before you install and configure the Infrastructure Optimization service,
you must create a database, service credentials, and API endpoints.

1. Create the database, complete these steps:

   * Use the database access client to connect to the database
     server as the ``root`` user:

     .. code-block:: console

        # mysql

   * Create the ``watcher`` database:

     .. code-block:: console

        CREATE DATABASE watcher CHARACTER SET utf8;

   * Grant proper access to the ``watcher`` database:

     .. code-block:: console

        GRANT ALL PRIVILEGES ON watcher.* TO 'watcher'@'localhost' \
          IDENTIFIED BY 'WATCHER_DBPASS';
        GRANT ALL PRIVILEGES ON watcher.* TO 'watcher'@'%' \
          IDENTIFIED BY 'WATCHER_DBPASS';

     Replace ``WATCHER_DBPASS`` with a suitable password.

   * Exit the database access client.

     .. code-block:: console

        exit;

2. Source the ``admin`` credentials to gain access to
   admin-only CLI commands:

   .. code-block:: console

      $ . admin-openrc

3. To create the service credentials, complete these steps:

   * Create the ``watcher`` user:

     .. code-block:: console

        $ openstack user create --domain default --password-prompt watcher
          User Password:
          Repeat User Password:
          +---------------------+----------------------------------+
          | Field               | Value                            |
          +---------------------+----------------------------------+
          | domain_id           | default                          |
          | enabled             | True                             |
          | id                  | b18ee38e06034b748141beda8fc8bfad |
          | name                | watcher                          |
          | options             | {}                               |
          | password_expires_at | None                             |
          +---------------------+----------------------------------+


   * Add the ``admin`` role to the ``watcher`` user:

     .. code-block:: console

        $ openstack role add --project service --user watcher admin

     .. note::

        This command produces no output.

   * Create the watcher service entities:

     .. code-block:: console

        $ openstack service create --name watcher --description "Infrastructure Optimization" infra-optim
          +-------------+----------------------------------+
          | Field       | Value                            |
          +-------------+----------------------------------+
          | description | Infrastructure Optimization      |
          | enabled     | True                             |
          | id          | d854f6fff0a64f77bda8003c8dedfada |
          | name        | watcher                          |
          | type        | infra-optim                      |
          +-------------+----------------------------------+


4. Create the Infrastructure Optimization service API endpoints:

   .. code-block:: console

      $ openstack endpoint create --region RegionOne \
        infra-optim public http://controller:9322
        +-------------+----------------------------------+
        | Field       | Value                            |
        +-------------+----------------------------------+
        | description | Infrastructure Optimization      |
        | enabled     | True                             |
        | id          | d854f6fff0a64f77bda8003c8dedfada |
        | name        | watcher                          |
        | type        | infra-optim                      |
        +-------------+----------------------------------+

      $ openstack endpoint create --region RegionOne \
        infra-optim internal http://controller:9322
        +--------------+----------------------------------+
        | Field        | Value                            |
        +--------------+----------------------------------+
        | enabled      | True                             |
        | id           | 225aef8465ef4df48a341aaaf2b0a390 |
        | interface    | internal                         |
        | region       | RegionOne                        |
        | region_id    | RegionOne                        |
        | service_id   | d854f6fff0a64f77bda8003c8dedfada |
        | service_name | watcher                          |
        | service_type | infra-optim                      |
        | url          | http://controller:9322           |
        +--------------+----------------------------------+

      $ openstack endpoint create --region RegionOne \
        infra-optim admin http://controller:9322
        +--------------+----------------------------------+
        | Field        | Value                            |
        +--------------+----------------------------------+
        | enabled      | True                             |
        | id           | 375eb5057fb546edbdf3ee4866179672 |
        | interface    | admin                            |
        | region       | RegionOne                        |
        | region_id    | RegionOne                        |
        | service_id   | d854f6fff0a64f77bda8003c8dedfada |
        | service_name | watcher                          |
        | service_type | infra-optim                      |
        | url          | http://controller:9322           |
        +--------------+----------------------------------+
