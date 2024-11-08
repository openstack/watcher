..
      Except where otherwise noted, this document is licensed under Creative
      Commons Attribution 3.0 License.  You can view the license at:

          https://creativecommons.org/licenses/by/3.0/

.. _watcher_development_environment:

=========================================
Set up a development environment manually
=========================================

This document describes getting the source from watcher `Git repository`_
for development purposes.

To install Watcher from packaging, refer instead to Watcher `User
Documentation`_.

.. _`Git Repository`: https://opendev.org/openstack/watcher
.. _`User Documentation`: https://docs.openstack.org/watcher/latest/

Prerequisites
=============

This document assumes you are using Ubuntu or Fedora, and that you have the
following tools available on your system:

- Python_ 2.7 and 3.5
- git_
- setuptools_
- pip_
- msgfmt (part of the gettext package)
- virtualenv and virtualenvwrapper_

**Reminder**: If you're successfully using a different platform, or a
different version of the above, please document your configuration here!

.. _Python: https://www.python.org/
.. _git: https://git-scm.com/
.. _setuptools: https://pypi.org/project/setuptools
.. _virtualenvwrapper: https://virtualenvwrapper.readthedocs.io/en/latest/install.html

Getting the latest code
=======================

Make a clone of the code from our ``Git repository``:

.. code-block:: bash

    $ git clone https://opendev.org/openstack/watcher.git

When that is complete, you can:

.. code-block:: bash

    $ cd watcher

Installing dependencies
=======================

Watcher maintains two lists of dependencies::

    requirements.txt
    test-requirements.txt

The first is the list of dependencies needed for running Watcher, the second
list includes dependencies used for active development and testing of Watcher
itself.

These dependencies can be installed from PyPi_ using the Python tool pip_.

.. _PyPi: https://pypi.org/
.. _pip: https://pypi.org/project/pip

However, your system *may* need additional dependencies that ``pip`` (and by
extension, PyPi) cannot satisfy. These dependencies should be installed
prior to using ``pip``, and the installation method may vary depending on
your platform.

* Ubuntu 16.04::

    $ sudo apt-get install python-dev libssl-dev libmysqlclient-dev libffi-dev

* Fedora 24+::

    $ sudo dnf install redhat-rpm-config gcc python-devel libxml2-devel

* CentOS 7::

    $ sudo yum install gcc python-devel libxml2-devel libxslt-devel mariadb-devel

PyPi Packages and VirtualEnv
----------------------------

We recommend establishing a virtualenv to run Watcher within. virtualenv
limits the Python environment to just what you're installing as dependencies,
useful to keep a clean environment for working on Watcher.

.. code-block:: bash

    $ mkvirtualenv watcher
    $ git clone https://opendev.org/openstack/watcher.git

    # Use 'python setup.py' to link Watcher into Python's site-packages
    $ cd watcher && python setup.py install

    # Install the dependencies for running Watcher
    $ pip install -r ./requirements.txt

    # Install the dependencies for developing, testing, and running Watcher
    $ pip install -r ./test-requirements.txt

This will create a local virtual environment in the directory ``$WORKON_HOME``.
The virtual environment can be disabled using the command:

.. code-block:: bash

    $ deactivate

You can re-activate this virtualenv for your current shell using:

.. code-block:: bash

    $ workon watcher

For more information on virtual environments, see virtualenv_ and
virtualenvwrapper_.

.. _virtualenv: https://pypi.org/project/virtualenv/



Verifying Watcher is set up
===========================

Once set up, either directly or within a virtualenv, you should be able to
invoke Python and import the libraries. If you're using a virtualenv, don't
forget to activate it:

.. code-block:: bash

    $ workon watcher

You should then be able to ``import watcher`` using Python without issue:

.. code-block:: bash

    $ python -c "import watcher"

If you can import watcher without a traceback, you should be ready to develop.

Run Watcher tests
=================

Watcher provides both :ref:`unit tests <unit_tests>` and
:ref:`functional/tempest tests <tempest_tests>`. Please refer to :doc:`testing`
to understand how to run them.


Build the Watcher documentation
===============================

You can easily build the HTML documentation from ``doc/source`` files, by using
``tox``:

.. code-block:: bash

    $ workon watcher

    (watcher) $ cd watcher
    (watcher) $ tox -edocs

The HTML files are available into ``doc/build`` directory.


Configure the Watcher services
==============================

Watcher services require a configuration file. Use tox to generate
a sample configuration file that can be used to get started:

.. code-block:: bash

  $ tox -e genconfig
  $ cp etc/watcher.conf.sample etc/watcher.conf

Most of the default configuration should be enough to get you going, but you
still need to configure the following sections:

- The ``[database]`` section to configure the
  :ref:`Watcher database <watcher-db_configuration>`
- The  ``[keystone_authtoken]`` section to configure the
  :ref:`Identity service <identity-service_configuration>` i.e. Keystone
- The ``[watcher_messaging]`` section to configure the OpenStack AMQP-based
  message bus
- The ``watcher_clients_auth`` section to configure Keystone client to access
  related OpenStack projects

So if you need some more details on how to configure one or more of these
sections, please do have a look at :doc:`../configuration/configuring` before
continuing.


Create Watcher SQL database
===========================

When initially getting set up, after you've configured which databases to use,
you're probably going to need to run the following to your database schema in
place:

.. code-block:: bash

    $ workon watcher

    (watcher) $ watcher-db-manage create_schema


Running Watcher services
========================

To run the Watcher API service, use:

.. code-block:: bash

    $ workon watcher

    (watcher) $ watcher-api

To run the Watcher Decision Engine service, use:

.. code-block:: bash

    $ workon watcher

    (watcher) $ watcher-decision-engine

To run the Watcher Applier service, use:

.. code-block:: bash

    $ workon watcher

    (watcher) $ watcher-applier

Default configuration of these services are available into ``/etc/watcher``
directory. See :doc:`../configuration/configuring` for details on how Watcher is
configured. By default, Watcher is configured with SQL backends.


Interact with Watcher
=====================

You can also interact with Watcher through its REST API. There is a Python
Watcher client library `python-watcherclient`_ which interacts exclusively
through the REST API, and which Watcher itself uses to provide its command-line
interface.

.. _`python-watcherclient`: https://github.com/openstack/python-watcherclient

There is also an Horizon plugin for Watcher `watcher-dashboard`_ which
allows to interact with Watcher through a web-based interface.

.. _`watcher-dashboard`: https://github.com/openstack/watcher-dashboard


Exercising the Watcher Services locally
=======================================

If you would like to exercise the Watcher services in isolation within a local
virtual environment, you can do this without starting any other OpenStack
services. For example, this is useful for rapidly prototyping and debugging
interactions over the RPC channel, testing database migrations, and so forth.

You will find in the `watcher-tools`_ project, Ansible playbooks and Docker
template files to easily play with Watcher services within a minimal OpenStack
isolated environment (Identity, Message Bus, SQL database, Horizon, ...).

.. _`watcher-tools`: https://github.com/b-com/watcher-tools
