==============
watcher-status
==============

-----------------------------------------
CLI interface for Watcher status commands
-----------------------------------------

Synopsis
========

::

  watcher-status <category> <command> [<args>]

Description
===========

:program:`watcher-status` is a tool that provides routines for checking the
status of a Watcher deployment.

Options
=======

The standard pattern for executing a :program:`watcher-status` command is::

    watcher-status <category> <command> [<args>]

Run without arguments to see a list of available command categories::

    watcher-status

Categories are:

* ``upgrade``

Detailed descriptions are below:

You can also run with a category argument such as ``upgrade`` to see a list of
all commands in that category::

    watcher-status upgrade

These sections describe the available categories and arguments for
:program:`Watcher-status`.

Upgrade
~~~~~~~

.. _watcher-status-checks:

``watcher-status upgrade check``
  Performs a release-specific readiness check before restarting services with
  new code. For example, missing or changed configuration options,
  incompatible object states, or other conditions that could lead to
  failures while upgrading.

  **Return Codes**

  .. list-table::
     :widths: 20 80
     :header-rows: 1

     * - Return code
       - Description
     * - 0
       - All upgrade readiness checks passed successfully and there is nothing
         to do.
     * - 1
       - At least one check encountered an issue and requires further
         investigation. This is considered a warning but the upgrade may be OK.
     * - 2
       - There was an upgrade status check failure that needs to be
         investigated. This should be considered something that stops an
         upgrade.
     * - 255
       - An unexpected error occurred.

  **History of Checks**

  **2.0.0 (Stein)**

  * Sample check to be filled in with checks as they are added in Stein.

  **3.0.0 (Train)**

  * A check was added to enforce the minimum required version of nova API used.
