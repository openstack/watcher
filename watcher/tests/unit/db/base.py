# Copyright (c) 2012 NTT DOCOMO, INC.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""Watcher DB test base class."""

from oslo_config import cfg
from oslo_db.sqlalchemy import enginefacade
from oslo_db.sqlalchemy import test_fixtures

from watcher.db import api as dbapi
from watcher.db.sqlalchemy import migration
from watcher.tests.local_fixtures import db as db_fixture
from watcher.tests.unit import base
from watcher.tests.unit.db import utils


CONF = cfg.CONF

CONF.import_opt('enable_authentication', 'watcher.api.acl')


class DbTestCase(base.TestCase):
    def get_next_id(self):
        return next(self._id_gen)

    def setUp(self):
        CONF.set_override("enable_authentication", False)
        super().setUp()
        self._db = self.useFixture(db_fixture.WatcherDatabase())
        self.dbapi = self._db.dbapi
        self._id_gen = utils.id_generator()


class MySQLDbTestCase(test_fixtures.OpportunisticDBTestMixin, base.TestCase):
    FIXTURE = test_fixtures.MySQLOpportunisticFixture

    def setUp(self):
        conn_str = "mysql+pymysql://root:insecure_slave@127.0.0.1"
        # to use mysql db
        cfg.CONF.set_override("connection", conn_str, group="database")
        super().setUp()
        self.engine = enginefacade.writer.get_engine()
        self.dbapi = dbapi.get_instance()
        migration.create_schema()
