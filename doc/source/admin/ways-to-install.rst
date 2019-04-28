..
      Except where otherwise noted, this document is licensed under Creative
      Commons Attribution 3.0 License.  You can view the license at:

          https://creativecommons.org/licenses/by/3.0/

=======================
Ways to install Watcher
=======================

This document describes some ways to install Watcher in order to use it.
If you are intending to develop on or with Watcher,
please read :doc:`../contributor/environment`.

Prerequisites
-------------

The source install instructions specifically avoid using platform specific
packages, instead using the source for the code and the Python Package Index
(PyPi_).

.. _PyPi: https://pypi.org/

It's expected that your system already has python2.7_, latest version of pip_,
and git_ available.

.. _python2.7: https://www.python.org
.. _pip: https://pip.pypa.io/en/latest/installing/
.. _git: https://git-scm.com/

Your system shall also have some additional system libraries:

  On Ubuntu (tested on 16.04LTS):

  .. code-block:: bash

    $ sudo apt-get install python-dev libssl-dev libmysqlclient-dev libffi-dev

  On Fedora-based distributions e.g., Fedora/RHEL/CentOS/Scientific Linux
  (tested on CentOS 7.1):

  .. code-block:: bash

    $ sudo yum install gcc python-devel openssl-devel libffi-devel mysql-devel


Installing from Source
----------------------

Clone the Watcher repository:

.. code-block:: bash

    $ git clone https://opendev.org/openstack/watcher.git
    $ cd watcher

Install the Watcher modules:

.. code-block:: bash

    # python setup.py install

The following commands should be available on the command-line path:

* ``watcher-api`` the Watcher Web service used to handle RESTful requests
* ``watcher-decision-engine`` the Watcher Decision Engine used to build action
  plans, according to optimization goals to achieve.
* ``watcher-applier`` the Watcher Applier module, used to apply action plan
* ``watcher-db-manage`` used to bootstrap Watcher data

You will find sample configuration files in ``etc/watcher``:

* ``watcher.conf.sample``

Install the Watcher modules dependencies:

.. code-block:: bash

    # pip install -r requirements.txt

From here, refer to :doc:`../configuration/configuring` to declare Watcher
as a new service into Keystone and to configure its different modules.
Once configured, you should be able to run the Watcher services by issuing
these commands:

.. code-block:: bash

    $ watcher-api
    $ watcher-decision-engine
    $ watcher-applier

By default, this will show logging on the console from which it was started.
Once started, you can use the `Watcher Client`_ to play with Watcher service.

.. _`Watcher Client`: https://opendev.org/openstack/python-watcherclient

Installing from packages: PyPI
--------------------------------

Watcher package is available on PyPI repository. To install Watcher on your
system:

.. code-block:: bash

    $ sudo pip install python-watcher

The Watcher services along with its dependencies should then be automatically
installed on your system.

Once installed, you still need to declare Watcher as a new service into
Keystone and to configure its different modules, which you can find described
in :doc:`../configuration/configuring`.


Installing from packages: Debian (experimental)
-----------------------------------------------

Experimental Debian packages are available on `Debian repositories`_. The best
way to use them is to install them into a Docker_ container.

Here is single Dockerfile snippet you can use to run your Docker container:

.. code-block:: bash

    FROM debian:experimental
    MAINTAINER David TARDIVEL <david.tardivel@b-com.com>

    RUN  apt-get update
    RUN  apt-get dist-upgrade
    RUN  apt-get install vim  net-tools
    RUN  apt-get install experimental watcher-api

    CMD ["/usr/bin/watcher-api"]

Build your container from this Dockerfile:

.. code-block:: bash

    $ docker build -t watcher/api .

To run your container, execute this command:

.. code-block:: bash

    $ docker run -d -p 9322:9322 watcher/api

Check in your logs Watcher API is started

.. code-block:: bash

    $ docker logs <container ID>

You can run similar container with Watcher Decision Engine (package
``watcher-decision-engine``) and with the Watcher Applier (package
``watcher-applier``).

.. _Docker: https://www.docker.com/
.. _`Debian repositories`: https://packages.debian.org/experimental/allpackages





