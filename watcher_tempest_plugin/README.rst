..
      Except where otherwise noted, this document is licensed under Creative
      Commons Attribution 3.0 License.  You can view the license at:

          https://creativecommons.org/licenses/by/3.0/

.. _tempest_tests:

Tempest tests
=============

The following procedure gets you started with Tempest testing but you can also
refer to the `Tempest documentation`_ for more details.

.. _Tempest documentation: http://docs.openstack.org/developer/tempest/


Tempest installation
--------------------

To install Tempest you can issue the following commands::

    $ git clone https://github.com/openstack/tempest/
    $ cd tempest/
    $ pip install .

The folder you are into now will be called ``<TEMPEST_DIR>`` from now onwards.

Please note that although it is fully working outside a virtual environment, it
is recommended to install within a `venv`.


Watcher Tempest testing setup
-----------------------------

You can now install Watcher alongside it in development mode by issuing the
following command::

    $  pip install -e <WATCHER_SRC_DIR>

Then setup a local working environment (here ``watcher-cloud``) for running
Tempest for Watcher which shall contain the configuration for your OpenStack
integration platform.

In a virtual environment, you can do so by issuing the following command::

    $ cd <TEMPEST_DIR>
    $ tempest init watcher-cloud

Otherwise, if you are not using a virtualenv::

    $ cd <TEMPEST_DIR>
    $ tempest init --config-dir ./etc watcher-cloud

By default the configuration file is empty so before starting, you need to
issue the following commands::

    $ cd <TEMPEST_DIR>/watcher-cloud/etc
    $ cp tempest.conf.sample tempest.conf

At this point you need to edit the ``watcher-cloud/etc/tempest.conf``
file as described in the `Tempest configuration guide`_.
Shown below is a minimal configuration you need to set within your
``tempest.conf`` configuration file which can get you started.

For Keystone V3::

    [identity]
    uri_v3 = http://<KEYSTONE_PUBLIC_ENDPOINT_IP>:<KEYSTONE_PORT>/v3
    auth_version = v3

    [auth]
    admin_username = <ADMIN_USERNAME>
    admin_password = <ADMIN_PASSWORD>
    admin_tenant_name = <ADMIN_TENANT_NAME>
    admin_domain_name = <ADMIN_DOMAIN_NAME>

    [identity-feature-enabled]
    api_v2 = false
    api_v3 = true

For Keystone V2::

    [identity]
    uri = http://<KEYSTONE_PUBLIC_ENDPOINT_IP>:<KEYSTONE_PORT>/v2.0
    auth_version = v2

    [auth]
    admin_tenant_name = <ADMIN_TENANT_NAME>
    admin_username = <ADMIN_USERNAME>
    admin_password = <ADMIN_PASSWORD>

In both cases::

    [network]
    public_network_id = <PUBLIC_NETWORK_ID>

You now have the minimum configuration for running Watcher Tempest tests on a
single node.

Since deploying Watcher with only a single compute node is not very useful, a
few more configuration have to be set in your ``tempest.conf`` file in order to
enable the execution of multi-node scenarios::

    [compute]
    # To indicate Tempest test that you have provided enough compute nodes
    min_compute_nodes = 2

    # Image UUID you can get using the "glance image-list" command
    image_ref = <IMAGE_UUID>


For more information, please refer to:

- Keystone connection: http://docs.openstack.org/developer/tempest/configuration.html#keystone-connection-info
- Dynamic Keystone Credentials: http://docs.openstack.org/developer/tempest/configuration.html#dynamic-credentials

.. _virtual environment: http://docs.python-guide.org/en/latest/dev/virtualenvs/
.. _Tempest configuration guide: http://docs.openstack.org/developer/tempest/configuration.html


Watcher Tempest tests execution
-------------------------------

To list all Watcher Tempest cases, you can issue the following commands::

    $ cd <TEMPEST_DIR>
    $ testr list-tests watcher

To run only these tests in Tempest, you can then issue these commands::

    $ ./run_tempest.sh --config watcher-cloud/etc/tempest.conf -N -- watcher

Or alternatively the following commands if you are::

    $ cd <TEMPEST_DIR>/watcher-cloud
    $ ../run_tempest.sh -N -- watcher

To run a single test case, go to Tempest directory, then run with test case
name, e.g.::

    $ cd <TEMPEST_DIR>
    $ ./run_tempest.sh --config watcher-cloud/etc/tempest.conf -N \
        -- watcher_tempest_plugin.tests.api.admin.test_audit_template.TestCreateDeleteAuditTemplate.test_create_audit_template

Alternatively, you can also run the Watcher Tempest plugin tests using tox. But
before you can do so, you need to follow the Tempest explanation on running
`tox with plugins`_. Then, run::

    $ export TEMPEST_CONFIG_DIR=<TEMPEST_DIR>/watcher-cloud/etc/
    $ tox -eall-plugin watcher

.. _tox with plugins: http://docs.openstack.org/developer/tempest/plugin.html#notes-for-using-plugins-with-virtualenvs

And, to run a specific test::

    $ export TEMPEST_CONFIG_DIR=<TEMPEST_DIR>/watcher-cloud/etc/
    $ tox -eall-plugin watcher_tempest_plugin.tests.api.admin.test_audit_template.TestCreateDeleteAuditTemplate.test_create_audit_template
