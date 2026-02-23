======
Resize
======

Synopsis
--------

**action name**: ``resize``

Resizes a server to the specified flavor

This action will allow you to resize a server to another flavor.

Configuration
-------------

Action parameters:

======================== ====== ======== ===================================
parameter                type   required description
======================== ====== ======== ===================================
``resource_id``          string yes      UUID of the server to resize
``flavor``               string yes      ID or Name of Flavor (Nova accepts
                                         either ID or Name)
======================== ====== ======== ===================================

Skipping conditions
--------------------

Resize actions will be automatically skipped in the pre_condition phase in
the following case:

- The server does not exist

On other condition the action will be FAILED in the pre_condition check:

- Destination flavor does not exist

