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
