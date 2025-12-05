====
Stop
====

Synopsis
--------

**action name**: ``stop``

Stops a server instance

This action will allow you to stop a server instance on a compute host.

Configuration
-------------

Action parameters:

======================== ====== ======== ===================================
parameter                type   required description
======================== ====== ======== ===================================
``resource_id``          string yes      UUID of the server instance to stop
======================== ====== ======== ===================================

Skipping conditions
--------------------

Stop actions will be automatically skipped in the pre_condition phase in
the following cases:

- The server does not exist
- The server is already stopped
