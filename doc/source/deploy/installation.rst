.. _installation:

========================
Development Installation
========================

Watcher development uses virtualenv to track and manage Python dependencies while in development and testing. This allows you to install all of the Python package dependencies in a virtual environment or “virtualenv”, instead of installing the packages at the system level.


Linux Systems
-------------

Install the prerequisite packages.

On Ubuntu (tested on 12.04-64 and 14.04-64)::

  sudo apt-get install python-dev libssl-dev python-pip git-core libmysqlclient-dev libffi-dev

On Fedora-based distributions e.g., Fedora/RHEL/CentOS/Scientific Linux (tested on CentOS 6.5)::

  sudo yum install python-virtualenv openssl-devel python-pip git gcc libffi-devel mysql-devel postgresql-devel

On openSUSE-based distributions (SLES 12, openSUSE 13.1, Factory or Tumbleweed)::

  sudo zypper install gcc git libmysqlclient-devel libopenssl-devel postgresql-devel python-devel python-pip


    Manually installing and using the virtualenv
    --------------------------------------------

    If you have `virtualenvwrapper <https://virtualenvwrapper.readthedocs.org/en/latest/install.html>`_  installed::

        $ mkvirtualenv watcher
        $ git clone https://git.openstack.org/openstack/stackforge/watcher
        $ cd watcher && python setup.py install
        $ pip install -r ./requirements.txt

    To run a specific test, use a positional argument for the unit tests::

        # run a specific test for Python 2.7
        tox -epy27 -- tests.api

    You may pass options to the test programs using positional arguments::

        # run all the Python 2.7 unit tests (in parallel!)
        tox -epy27 -- --parallel

    To run only the pep8/flake8 syntax and style checks::

        tox -epep8


Configure Identity Service for Watcher
--------------------------------------

#. Create the Watcher service user (eg ``watcher``). The service uses this to
   authenticate with the Identity Service. Use the ``service`` project and
   give the user the ``admin`` role::

    keystone user-create --name=watcher --pass=WATCHER_PASSWORD --email=watcher@example.com
    keystone user-role-add --user=watcher --tenant=service --role=admin

    or

    openstack user create  --password WATCHER_PASSWORD --enable --email watcher@example.com watcher
    openstack role add --project services --user watcher admin


#. You must register the Watcher Service with the Identity Service so that
   other OpenStack services can locate it. To register the service::

    keystone service-create --name=watcher --type=infra-optim \
    --description="Infrastructure Optimization service"

    or 

    openstack service create --name watcher infra-optim 

#. Create the endpoints by replacing YOUR_REGION and WATCHER_API_IP with your region and your Watcher Service's API node::

    keystone endpoint-create \
    --service-id=the_service_id_above \
    --publicurl=http://WATCHER_API_IP:9322 \
    --internalurl=http://WATCHER_API_IP:9322 \
    --adminurl=http://WATCHER_API_IP:9322

    or

    openstack endpoint create --region YOUR_REGION watcher public http://WATCHER_API_IP:9322
    openstack endpoint create --region YOUR_REGION watcher admin http://WATCHER_API_IP:9322
    openstack endpoint create --region YOUR_REGION watcher internal http://WATCHER_API_IP:9322



Set up the Database for Watcher
-------------------------------

The Watcher Service stores information in a database. This guide uses the
MySQL database that is used by other OpenStack services.

#. In MySQL, create an ``watcher`` database that is accessible by the
   ``watcher`` user. Replace WATCHER_DBPASSWORD
   with the actual password::

    # mysql -u root -p
    mysql> CREATE DATABASE watcher CHARACTER SET utf8;
    mysql> GRANT ALL PRIVILEGES ON watcher.* TO 'watcher'@'localhost' \
    IDENTIFIED BY 'WATCHER_DBPASSWORD';
    mysql> GRANT ALL PRIVILEGES ON watcher.* TO 'watcher'@'%' \
    IDENTIFIED BY 'WATCHER_DBPASSWORD';


Configure the Watcher Service
=============================

The Watcher Service is configured via its configuration file. This file
is typically located at ``/etc/watcher/watcher.conf``. You can copy the file ``etc/watcher/watcher.conf.sample`` from the GIT repo to your server and update it.

Although some configuration options are mentioned here, it is recommended that
you review all the available options so that the Watcher Service is
configured for your needs.

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
   address of the RabbitMQ server.::

    [DEFAULT]
    ...
    # The RabbitMQ broker address where a single node is used
    # (string value)
    rabbit_host=RABBIT_HOST

    # The RabbitMQ userid (string value)
    #rabbit_userid=guest

    # The RabbitMQ password (string value)
    #rabbit_password=guest

    # The RabbitMQ virtual host (string value)
    #rabbit_virtual_host=/

#. Configure the Watcher Service to use these credentials with the Identity
   Service. Replace IDENTITY_IP with the IP of the Identity server, and
   replace WATCHER_PASSWORD with the password you chose for the ``watcher``
   user in the Identity Service::

    [DEFAULT]
    ...
    # Method to use for authentication: noauth or keystone.
    # (string value)
    auth_strategy=keystone

    ...
    [keystone_authtoken]

    # Complete public Identity API endpoint (string value)
    #auth_uri=<None>
    auth_uri=http://IDENTITY_IP:5000/v3

    # Complete admin Identity API endpoint. This should specify the
    # unversioned root endpoint e.g. https://localhost:35357/ (string
    # value)
    #identity_uri = <None>
    identity_uri = http://IDENTITY_IP:5000

    # Keystone account username (string value)
    #admin_user=<None>
    admin_user=watcher

    # Keystone account password (string value)
    #admin_password=<None>
    admin_password=WATCHER_DBPASSWORD

    # Keystone service account tenant name to validate user tokens
    # (string value)
    #admin_tenant_name=admin
    admin_tenant_name=KEYSTONE_SERVICE_PROJECT_NAME

    # Directory used to cache files related to PKI tokens (string
    # value)
    #signing_dir=<None>


#. Create the Watcher Service database tables::

    watcher-db-manage --config-file /etc/watcher/watcher.conf create_schema

#. Start the Watcher Service::

    watcher-api &&  watcher-decision-engine && watcher-applier

===============
Important notes 
===============


#. Watcher must have admin role on supervized users' projects created on your IAAS, in order to be able to migrate project's instances if required by Watcher audits: 

    keystone user-role-add --user=watcher --tenant=<USER_PROJECT_NAME> --role=admin

    or 

    openstack role add --project <USER_PROJECT_NAME> --user watcher admin

#. Please check also your hypervisor configuration to handle correctly instance migration: 

    `OpenStack - Configure Migrations <http://docs.openstack.org/admin-guide-cloud/content/section_configuring-compute-migrations.html>`_