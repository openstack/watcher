==================================
Migrating from Prometheus to Aetos
==================================

Overview
========

This guide provides step-by-step instructions for migrating an existing
Watcher deployment from using the Prometheus datasource to the Aetos
datasource.

Why Migrate?
============

The Aetos datasource provides:

* **Multi-tenancy**: Keystone-based authentication and role validation
* **Security**: RBAC for metric access, no direct Prometheus exposure
* **Compatibility**: All Prometheus APIs available
* **Integration**: Native OpenStack service catalog integration

Prerequisites
=============

Before migrating, ensure:

1. Aetos service is deployed and operational
2. Aetos endpoint registered in Keystone with service type 'metric-storage'
3. Watcher service account has appropriate roles (admin or service role)

Migration Steps
===============

Step 1: Verify Aetos Availability
---------------------------------

.. code-block:: bash

   openstack catalog show metric-storage

Verify that the Aetos endpoint is registered and accessible.


Step 2: Backup Current Configuration
------------------------------------

.. code-block:: bash

   sudo cp /etc/watcher/watcher.conf /etc/watcher/watcher.conf.backup.$(date +%Y%m%d)

This step is not strictly required for the migration, but provides a working
configuration to revert to in case something goes wrong.

Step 3: Remove Prometheus Configuration
---------------------------------------

Edit ``/etc/watcher/watcher.conf`` and remove or comment out the
``[prometheus_client]`` section:

.. code-block:: ini

   # [prometheus_client]
   # host = prometheus.example.com
   # port = 9090
   # ... (remove all prometheus_client options)

Step 4: Update Datasource Configuration
---------------------------------------

Change the datasources option in ``[watcher_datasources]``:

.. code-block:: ini

   [watcher_datasources]
   datasources = aetos

.. note::

   If you have other datasources configured (e.g., grafana), you can keep them
   alongside aetos:

   .. code-block:: ini

      [watcher_datasources]
      datasources = aetos,grafana

Step 5: Configure Aetos Client
------------------------------

Add the ``[aetos_client]`` section with appropriate values:

.. code-block:: ini

   [aetos_client]
   # Keystone endpoint interface (public, internal, or admin)
   interface = public

   # Region name for Keystone catalog lookup
   region_name = RegionOne

   # Prometheus label for FQDN
   fqdn_label = fqdn

   # Prometheus label for instance UUID
   instance_uuid_label = resource

See the aetos datasource documentation page for more details on how to
configure it :doc:`aetos`

Step 6: Restart Watcher Services
--------------------------------

.. code-block:: bash

   sudo systemctl restart watcher-decision-engine

.. note::

   The service name may vary depending on your deployment method. In DevStack,
   it might be ``devstack@watcher-decision-engine``. Check your system's service
   naming convention.

Verification
============

After migration, verify the Aetos datasource is working:

1. Check Watcher logs for successful datasource initialization:

   .. code-block:: bash

      sudo journalctl -u watcher-decision-engine -f

   Look for messages indicating Aetos datasource loaded successfully.

2. Trigger a test audit to verify metric collection:

   .. code-block:: bash

      openstack optimize audit create -g <goal-name> -s <strategy-name>

3. Monitor audit execution and verify metrics are retrieved from Aetos.

Troubleshooting
===============

Aetos Endpoint Not Found
------------------------

**Error**: "Aetos service not registered in Keystone"

**Solution**:

- Verify Aetos is deployed: ``openstack catalog show metric-storage``
- Register Aetos endpoint if missing
- Check service type is exactly 'metric-storage'

Authentication Failures
-----------------------

**Error**: "Unauthorized" or "403 Forbidden"

**Solution**:

- Verify Watcher service account has admin or service role
- Check Keystone token is valid

Metric Labels Mismatch
----------------------

**Error**: Metrics not found or empty results

**Solution**:

- Verify ``fqdn_label`` matches your Prometheus exporter configuration
- Verify ``instance_uuid_label`` matches your Prometheus labels
- Check Prometheus metrics are properly labeled

Rollback Procedure
==================

If migration fails, rollback to Prometheus:

.. code-block:: bash

   # Restore backup
   sudo cp /etc/watcher/watcher.conf.backup.YYYYMMDD /etc/watcher/watcher.conf

   # Restart services
   sudo systemctl restart watcher-decision-engine

Additional Resources
====================

* Aetos documentation: https://docs.openstack.org/aetos/latest/
* Watcher datasources guide: :doc:`index`
* :doc:`prometheus`
* :doc:`aetos`
