..
      Except where otherwise noted, this document is licensed under Creative
      Commons Attribution 3.0 License.  You can view the license at:

          https://creativecommons.org/licenses/by/3.0/

.. _watcher-db-manage:

=================
watcher-db-manage
=================

The :command:`watcher-db-manage` utility is used to create the database schema
tables that the watcher services will use for storage. It can also be used to
upgrade (or downgrade) existing database tables when migrating between
different versions of watcher.

The `Alembic library <http://alembic.readthedocs.org>`_ is used to perform
the database migrations.

Options
=======

This is a partial list of the most useful options. To see the full list,
run the following::

  watcher-db-manage --help

.. program:: watcher-db-manage

.. option:: -h, --help

  Show help message and exit.

.. option:: --config-dir <DIR>

  Path to a config directory with configuration files.

.. option:: --config-file <PATH>

  Path to a configuration file to use.

.. option:: -d, --debug

  Print debugging output.

.. option:: -v, --verbose

  Print more verbose output.

.. option:: --version

  Show the program's version number and exit.

.. option:: upgrade, downgrade, stamp, revision, version, create_schema, purge

  The :ref:`command <db-manage_cmds>` to run.

Usage
=====

Options for the various :ref:`commands <db-manage_cmds>` for
:command:`watcher-db-manage` are listed when the :option:`-h` or
:option:`--help`
option is used after the command.

For example::

  watcher-db-manage create_schema --help

Information about the database is read from the watcher configuration file
used by the API server and conductor services. This file must be specified
with the :option:`--config-file` option::

  watcher-db-manage --config-file /path/to/watcher.conf create_schema

The configuration file defines the database backend to use with the
*connection* database option::

  [database]
  connection=mysql://root@localhost/watcher

If no configuration file is specified with the :option:`--config-file` option,
:command:`watcher-db-manage` assumes an SQLite database.

.. _db-manage_cmds:

Command Options
===============

:command:`watcher-db-manage` is given a command that tells the utility
what actions to perform.
These commands can take arguments. Several commands are available:

.. _create_schema:

create_schema
-------------

.. program:: create_schema

.. option:: -h, --help

  Show help for create_schema and exit.

This command will create database tables based on the most current version.
It assumes that there are no existing tables.

An example of creating database tables with the most recent version::

  watcher-db-manage --config-file=/etc/watcher/watcher.conf create_schema

downgrade
---------

.. program:: downgrade

.. option:: -h, --help

  Show help for downgrade and exit.

.. option:: --revision <REVISION>

  The revision number you want to downgrade to.

This command will revert existing database tables to a previous version.
The version can be specified with the :option:`--revision` option.

An example of downgrading to table versions at revision 2581ebaf0cb2::

  watcher-db-manage --config-file=/etc/watcher/watcher.conf downgrade --revision 2581ebaf0cb2

revision
--------

.. program:: revision

.. option:: -h, --help

  Show help for revision and exit.

.. option:: -m <MESSAGE>, --message <MESSAGE>

  The message to use with the revision file.

.. option:: --autogenerate

  Compares table metadata in the application with the status of the database
  and generates migrations based on this comparison.

This command will create a new revision file. You can use the
:option:`--message` option to comment the revision.

This is really only useful for watcher developers making changes that require
database changes. This revision file is used during database migration and
will specify the changes that need to be made to the database tables. Further
discussion is beyond the scope of this document.

stamp
-----

.. program:: stamp

.. option:: -h, --help

  Show help for stamp and exit.

.. option:: --revision <REVISION>

  The revision number.

This command will 'stamp' the revision table with the version specified with
the :option:`--revision` option. It will not run any migrations.

upgrade
-------

.. program:: upgrade

.. option:: -h, --help

  Show help for upgrade and exit.

.. option:: --revision <REVISION>

  The revision number to upgrade to.

This command will upgrade existing database tables to the most recent version,
or to the version specified with the :option:`--revision` option.

If there are no existing tables, then new tables are created, beginning
with the oldest known version, and successively upgraded using all of the
database migration files, until they are at the specified version. Note
that this behavior is different from the :ref:`create_schema` command
that creates the tables based on the most recent version.

An example of upgrading to the most recent table versions::

  watcher-db-manage --config-file=/etc/watcher/watcher.conf upgrade

.. note::

  This command is the default if no command is given to
  :command:`watcher-db-manage`.

.. warning::

  The upgrade command is not compatible with SQLite databases since it uses
  ALTER TABLE commands to upgrade the database tables. SQLite supports only
  a limited subset of ALTER TABLE.

version
-------

.. program:: version

.. option:: -h, --help

  Show help for version and exit.

This command will output the current database version.

purge
-----

.. program:: purge

.. option:: -h, --help

  Show help for purge and exit.

.. option:: -d, --age-in-days

  The number of days (starting from today) before which we consider soft
  deleted objects as expired and should hence be erased. By default, all
  objects soft deleted are considered expired. This can be useful as removing
  a significant amount of objects may cause a performance issues.

.. option:: -n, --max-number

  The maximum number of database objects we expect to be deleted. If exceeded,
  this will prevent any deletion.

.. option:: -t, --goal

  Either the UUID or name of the goal to purge.

.. option:: -e, --exclude-orphans

  This is a flag to indicate when we want to exclude orphan objects from
  deletion.

.. option:: --dry-run

  This is a flag to indicate when we want to perform a dry run. This will show
  the objects that would be deleted instead of actually deleting them.

This command will purge the current database by removing both its soft deleted
and orphan objects.
