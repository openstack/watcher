2. Edit the ``/etc/watcher/watcher.conf`` file and complete the following
   actions:

   * In the ``[database]`` section, configure database access:

     .. code-block:: ini

        [database]
        ...
        connection = mysql+pymysql://watcher:WATCHER_DBPASS@controller/watcher?charset=utf8

   * In the `[DEFAULT]` section, configure the transport url for RabbitMQ message broker.

     .. code-block:: ini

        [DEFAULT]
        ...
        control_exchange = watcher
        transport_url = rabbit://openstack:RABBIT_PASS@controller

     Replace the RABBIT_PASS with the password you chose for OpenStack user in RabbitMQ.

   * In the `[keystone_authtoken]` section, configure Identity service access.

     .. code-block:: ini

        [keystone_authtoken]
        ...
        www_authenticate_uri = http://controller:5000
        auth_url = http://controller:5000
        memcached_servers = controller:11211
        auth_type = password
        project_domain_name = default
        user_domain_name = default
        project_name = service
        username = watcher
        password = WATCHER_PASS

     Replace WATCHER_PASS with the password you chose for the watcher user in the Identity service.

   * Watcher interacts with other OpenStack projects via project clients, in order to instantiate these
     clients, Watcher requests new session from Identity service. In the `[watcher_clients_auth]` section,
     configure the identity service access to interact with other OpenStack project clients.

     .. code-block:: ini

        [watcher_clients_auth]
        ...
        auth_type = password
        auth_url = http://controller:5000
        username = watcher
        password = WATCHER_PASS
        project_domain_name = default
        user_domain_name = default
        project_name = service

     Replace WATCHER_PASS with the password you chose for the watcher user in the Identity service.

   * In the `[api]` section, configure host option.

     .. code-block:: ini

        [api]
        ...
        host = controller

     Replace controller with the IP address of the management network interface on your controller node, typically 10.0.0.11 for the first node in the example architecture.

   * In the `[oslo_messaging_notifications]` section, configure the messaging driver.

     .. code-block:: ini

        [oslo_messaging_notifications]
        ...
        driver = messagingv2

3. Populate watcher database:

   .. code-block:: ini

     su -s /bin/sh -c "watcher-db-manage --config-file /etc/watcher/watcher.conf upgrade"
