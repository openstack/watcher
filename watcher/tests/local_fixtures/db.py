# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Database fixtures shared by unit and functional tests."""

import os
import sqlite3
import tempfile

import fixtures

from oslo_config import cfg
from oslo_db.sqlalchemy import enginefacade
from oslo_db.sqlalchemy import test_fixtures

from watcher.db import api as dbapi
from watcher.db.sqlalchemy import migration
from watcher.tests.local_fixtures import db_lock


CONF = cfg.CONF


class SqliteDatabaseFixture(
    test_fixtures.GeneratesSchema, test_fixtures.AdHocDbFixture
):
    """Provision a per-test SQLite database with the Watcher schema.

    Uses oslo_db's AdHocDbFixture to provision the database and
    GeneratesSchema to build the Watcher schema via migration helpers.
    """

    def __init__(self):
        super().__init__(url=CONF.database.connection)

    def generate_schema_create_all(self, engine):
        migration.create_schema(engine=engine)


class WatcherDatabase(fixtures.Fixture):
    """Full SQLite database setup for Watcher tests.

    Creates a file-backed SQLite database with WAL journaling,
    configures the oslo_db engine facade, provisions the Watcher
    schema, and adds a write lock for thread safety.

    Exposes ``self.dbapi`` after setup.
    """

    def setUp(self):
        super().setUp()

        # Creates a temporary dir to hold sqlite temp files
        # and patch tempfile to use it as default dir.
        self.useFixture(fixtures.NestedTempfile())

        # NOTE(dviroel): Using file-backed database to support multiple
        # native threads, since each one can have its own connection to
        # the database. Files created by SQLite will be cleaned up
        # by the NestedTempfile fixture.
        fd, dbfile_path = tempfile.mkstemp(
            prefix='watcher_test_', suffix='.db'
        )
        # close the file descriptor before SQLite connects
        os.close(fd)
        CONF.set_override(
            'connection', 'sqlite:///%s' % dbfile_path, group='database'
        )

        # Enable WAL journaling mode: "WAL provides more concurrency as
        # readers do not block writers and a writer does not block readers."
        # Note that WAL journal mode is persistent, if we close and reopen
        # the database, it will come back in WAL mode.
        # More info at: https://www.sqlite.org/wal.html
        with sqlite3.connect(dbfile_path) as conn:
            conn.execute('PRAGMA journal_mode=WAL')

        # NOTE(dviroel): Creates a new enginefacade for each test,
        # and use the fixture to replace the application level factory
        # with the local one. This avoids issue with factory global flags
        # that can avoid re-configuring the database.
        local_enginefacade = enginefacade.transaction_context()
        local_enginefacade.configure(
            connection=CONF.database.connection,
            sqlite_synchronous=CONF.database.sqlite_synchronous,
        )
        self.useFixture(
            test_fixtures.ReplaceEngineFacadeFixture(
                enginefacade._context_manager, local_enginefacade
            )
        )

        # Provision and configure a SQLite database for this test using
        # oslo_db's fixtures.
        self.useFixture(SqliteDatabaseFixture())
        # NOTE(dviroel): SQLite support only a single writer per database
        # and we still miss the support retrying on a "Database is Locked"
        # error.
        self.useFixture(db_lock.DatabaseWriteLock())
        self.dbapi = dbapi.get_instance()
