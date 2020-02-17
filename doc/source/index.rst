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
migration, increased energy efficiency and more!

Watcher project consists of several source code repositories:

* `watcher`_ - is the main repository. It contains code for Watcher API server,
  Watcher Decision Engine and Watcher Applier.
* `python-watcherclient`_ - Client library and CLI client for Watcher.
* `watcher-dashboard`_ - Watcher Horizon plugin.

The documentation provided here is continually kept up-to-date based
on the latest code, and may not represent the state of the project at any
specific prior release.

.. _watcher: https://opendev.org/openstack/watcher/
.. _python-watcherclient: https://opendev.org/openstack/python-watcherclient/
.. _watcher-dashboard: https://opendev.org/openstack/watcher-dashboard/

.. toctree::
  :maxdepth: 2

  architecture
  contributor/index
  install/index
  admin/index
  user/index
  configuration/index
  contributor/plugin/index
  man/index

.. toctree::
  :maxdepth: 1

  API Reference <https://docs.openstack.org/api-ref/resource-optimization/>
  Watcher API Microversion History </contributor/api_microversion_history>
  glossary
