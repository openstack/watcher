======
Delete
======

Synopsis
--------

**action name**: ``delete``

Deletes a server instance

This action will allow you to delete a server instance, removing it and all
associated resources. This is a destructive and irreversible action.

Configuration
-------------

Action parameters:

.. list-table::
   :widths: 25 10 10 55
   :header-rows: 1

   * - parameter
     - type
     - required
     - description
   * - ``resource_id``
     - string
     - yes
     - UUID of the server instance to delete

Skipping conditions
--------------------

Delete actions will be automatically skipped in the pre_condition phase in
the following cases:

- The server does not exist
