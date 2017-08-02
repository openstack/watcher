The migrations in the alembic/versions contain the changes needed to migrate
from older Watcher releases to newer versions. A migration occurs by executing
a script that details the changes needed to upgrade/downgrade the database. The
migration scripts are ordered so that multiple scripts can run sequentially to
update the database. The scripts are executed by Watcher's migration wrapper
which uses the Alembic library to manage the migration. Watcher supports
migration from Ocata or later.


If you are a deployer or developer and want to migrate from Ocata to later
release you must first add version tracking to the database::

    $ watcher-db-manage --config-file /path/to/watcher.conf stamp ocata


You can upgrade to the latest database version via::

    $ watcher-db-manage --config-file /path/to/watcher.conf upgrade head


To check the current database version::

    $ watcher-db-manage --config-file /path/to/watcher.conf version


To create a script to run the migration offline::

    $ watcher-db-manage --config-file /path/to/watcher.conf upgrade head --sql


To run the offline migration between specific migration versions::

    $ watcher-db-manage --config-file /path/to/watcher.conf upgrade \
        <start version>:<end version> --sql


Upgrade the database incrementally::

    $ watcher-db-manage --config-file /path/to/watcher.conf upgrade --revision \
        <# of revs>


Downgrade the database by a certain number of revisions::

    $ watcher-db-manage --config-file /path/to/watcher.conf downgrade --revision \
        <# of revs>


Create new revision::

    $ watcher-db-manage --config-file /path/to/watcher.conf revision \
        -m "description of revision" --autogenerate


Create a blank file::

    $ watcher-db-manage --config-file /path/to/watcher.conf revision \
        -m "description of revision"

Please see https://alembic.readthedocs.org/en/latest/index.html for general
documentation

