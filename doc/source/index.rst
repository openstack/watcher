..
      Except where otherwise noted, this document is licensed under Creative
      Commons Attribution 3.0 License.  You can view the license at:

          https://creativecommons.org/licenses/by/3.0/

================================
Welcome to Watcher documentation
================================

OpenStack Watcher provides a flexible and scalable resource optimization
service for multi-tenant OpenStack-based clouds.
Watcher provides a complete optimization loop—including everything from a
metrics receiver, complex event processor and profiler, optimization processor
and an action plan applier. This provides a robust framework to realize a wide
range of cloud optimization goals, including the reduction of data center
operating costs, increased system performance via intelligent virtual machine
migration, increased energy efficiency—and more!

Watcher project consists of several source code repositories:

* `watcher`_ - is the main repository. It contains code for Watcher API server,
  Watcher Decision Engine and Watcher Applier.
* `python-watcherclient`_ - Client library and CLI client for Watcher.
* `watcher-dashboard`_ - Watcher Horizon plugin.

The documentation provided here is continually kept up-to-date based
on the latest code, and may not represent the state of the project at any
specific prior release.

.. _watcher: https://git.openstack.org/cgit/openstack/watcher/
.. _python-watcherclient: https://git.openstack.org/cgit/openstack/python-watcherclient/
.. _watcher-dashboard: https://git.openstack.org/cgit/openstack/watcher-dashboard/

Developer Guide
===============

Introduction
------------

.. toctree::
  :maxdepth: 1

  glossary
  architecture
  contributor/contributing


Getting Started
---------------

.. toctree::
  :maxdepth: 1

  contributor/index

API References
--------------

.. toctree::
  :maxdepth: 1

  api/index

Plugins
-------

.. toctree::
  :maxdepth: 1

  contributor/plugin/index

Installation
============
.. toctree::
  :maxdepth: 2

  install/index

Watcher Configuration Options
=============================

.. toctree::
  :maxdepth: 2

  configuration/index

Admin Guide
===========

.. toctree::
  :maxdepth: 2

  admin/index

User Guide
==========

.. toctree::
  :maxdepth: 2

  user/index

Watcher Manual Pages
====================

.. toctree::
   :glob:
   :maxdepth: 1

   man/index

.. # NOTE(mriedem): This is the section where we hide things that we don't
   # actually want in the table of contents but sphinx build would fail if
   # they aren't in the toctree somewhere. For example, we hide api/autoindex
   # since that's already covered with modindex below.
.. toctree::
   :hidden:

   api/autoindex


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
