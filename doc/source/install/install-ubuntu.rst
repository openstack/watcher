.. _install-ubuntu:

Install and configure for Ubuntu
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This section describes how to install and configure the Infrastructure
Optimization service for Ubuntu 14.04 (LTS).

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

Restart the Infrastructure Optimization services:

.. code-block:: console

   # service watcher-api restart
   # service watcher-decision-engine restart
   # service watcher-applier restart
