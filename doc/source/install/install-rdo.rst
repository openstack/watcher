.. _install-rdo:

Install and configure for Red Hat Enterprise Linux and CentOS
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


This section describes how to install and configure the Infrastructure
Optimization service for Red Hat Enterprise Linux 7 and CentOS 7.

.. include:: common_prerequisites.rst

Install and configure components
--------------------------------

1. Install the packages:

   .. code-block:: console

      # sudo yum install openstack-watcher-api openstack-watcher-applier \
        openstack-watcher-decision-engine

.. include:: common_configure.rst

Finalize installation
---------------------

Start the Infrastructure Optimization services and configure them to start when
the system boots:

.. code-block:: console

   # systemctl enable openstack-watcher-api.service \
     openstack-watcher-decision-engine.service \
     openstack-watcher-applier.service

   # systemctl start openstack-watcher-api.service \
     openstack-watcher-decision-engine.service \
     openstack-watcher-applier.service
