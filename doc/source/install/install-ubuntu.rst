.. _install-ubuntu:

Install and configure for Ubuntu
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This section describes how to install and configure the Infrastructure
Optimization service for Ubuntu 16.04 (LTS).

.. include:: common_prerequisites.rst

Install and configure components
--------------------------------

1. Install the packages:

   .. code-block:: console

      # apt install watcher-api watcher-decision-engine \
        watcher-applier

      # apt install python-watcherclient

.. include:: common_configure.rst

Finalize installation
---------------------

Start the Infrastructure Optimization services and configure them to start when
the system boots:

.. code-block:: console

   # systemctl enable watcher-api.service \
     watcher-decision-engine.service \
     watcher-applier.service

   # systemctl start watcher-api.service \
     watcher-decision-engine.service \
     watcher-applier.service
