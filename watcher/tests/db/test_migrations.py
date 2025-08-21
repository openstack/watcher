# Copyright 2025 Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#

""""Tests for database migration for Watcher.

These are "opportunistic" tests which allow testing against all three databases
(sqlite in memory, mysql, pg) in a properly configured unit test environment.

For the opportunistic testing you need to set up DBs named 'openstack_citest'
with user 'openstack_citest' and password 'openstack_citest' on localhost. The
test will then use that DB and username/password combo to run the tests. Refer
to the 'tools/test-setup.sh' for an example of how to configure this.
"""

from alembic import command as alembic_api
from alembic.script import ScriptDirectory
from oslo_config import cfg
from oslo_db.sqlalchemy import enginefacade
from oslo_db.sqlalchemy import test_fixtures
from oslo_db.sqlalchemy import utils as oslodbutils
from oslo_log import log as logging
import sqlalchemy

from watcher.common import utils as w_utils
from watcher.db import api as dbapi
from watcher.db.sqlalchemy import migration
from watcher.tests import base
from watcher.tests.db import utils

LOG = logging.getLogger(__name__)


class MySQLDbMigrationsTestCase(test_fixtures.OpportunisticDBTestMixin,
                                base.TestCase):

    FIXTURE = test_fixtures.MySQLOpportunisticFixture

    def setUp(self):
        conn_str = "mysql+pymysql://root:insecure_slave@127.0.0.1"
        # to use mysql db
        cfg.CONF.set_override("connection", conn_str,
                              group="database")
        super().setUp()
        self.engine = enginefacade.writer.get_engine()
        self.dbapi = dbapi.get_instance()
        self.alembic_config = migration._alembic_config()
        self.revisions_tested = set(["15f7375ca737", "7150a7d8f228"])

    def _apply_migration(self, connection, revision):
        if revision not in self.revisions_tested:
            # if we don't have tests for this version, just upgrade to it
            alembic_api.upgrade(self.alembic_config, revision)
            return

        pre_upgrade = getattr(self, f"_pre_upgrade_{revision}", None)
        if pre_upgrade:
            pre_upgrade(connection)

        alembic_api.upgrade(self.alembic_config, revision)

        post_upgrade = getattr(self, f"_check_{revision}", None)
        if post_upgrade:
            post_upgrade(connection)

    def _pre_upgrade_15f7375ca737(self, connection):
        inspector = sqlalchemy.inspect(connection)
        columns = inspector.get_columns("efficacy_indicators")
        for column in columns:
            if column['name'] != "value":
                continue
            value_type = column['type']
            self.assertIsInstance(value_type, sqlalchemy.Numeric)
            self.assertEqual(value_type.scale, 0)
            self.assertEqual(value_type.precision, 10)

    def _check_15f7375ca737(self, connection):
        inspector = sqlalchemy.inspect(connection)
        columns = inspector.get_columns("efficacy_indicators")
        for column in columns:
            if column['name'] == "value":
                value_type = column['type']
                self.assertIsInstance(value_type, sqlalchemy.Numeric)
                self.assertEqual(value_type.scale, 0)
                self.assertEqual(value_type.precision, 10)
            elif column['name'] == "data":
                value_type = column['type']
                self.assertIsInstance(value_type, sqlalchemy.Float)

    def test_migration_revisions(self):
        with self.engine.begin() as connection:
            self.alembic_config.attributes["connection"] = connection
            script = ScriptDirectory.from_config(self.alembic_config)
            revisions = [x.revision for x in script.walk_revisions()]

            # for some reason, 'walk_revisions' gives us the revisions in
            # reverse chronological order so we have to invert this
            revisions.reverse()

            for revision in revisions:
                LOG.info('Testing revision %s', revision)
                self._apply_migration(connection, revision)


class MySQLDbDataMigrationsTestCase(MySQLDbMigrationsTestCase):
    def _transform_mutable_fields_to_text(self, obj_values):
        transformed = {}
        for key, value in obj_values.items():
            if type(value) in (dict, list):
                transformed[key] = str(value)
            else:
                transformed[key] = value
        return transformed

    def _create_manual_action_plan(self, connection, **kwargs):
        ap_values = utils.get_test_action_plan(**kwargs)
        ap_values = self._transform_mutable_fields_to_text(ap_values)
        metadata = sqlalchemy.MetaData()
        metadata.reflect(bind=self.engine)
        ap_table = sqlalchemy.Table('action_plans', metadata)
        with connection.begin():
            connection.execute(ap_table.insert(), ap_values)

    def _create_manual_audit(self, connection, **kwargs):
        audit_values = utils.get_test_audit(**kwargs)
        audit_values = self._transform_mutable_fields_to_text(audit_values)
        metadata = sqlalchemy.MetaData()
        metadata.reflect(bind=self.engine)
        audit_table = sqlalchemy.Table('audits', metadata)
        with connection.begin():
            connection.execute(audit_table.insert(), audit_values)

    def _create_manual_efficacy_indicator(self, connection, **kwargs):
        eff_ind_values = utils.get_test_efficacy_indicator(**kwargs)
        metadata = sqlalchemy.MetaData()
        metadata.reflect(bind=self.engine)
        eff_ind_table = sqlalchemy.Table('efficacy_indicators', metadata)
        with connection.begin():
            connection.execute(eff_ind_table.insert(), eff_ind_values)

    def _read_efficacy_indicator(self, connection, id):
        metadata = sqlalchemy.MetaData()
        metadata.reflect(bind=self.engine)
        eff_ind_table = sqlalchemy.Table('efficacy_indicators', metadata)
        with connection.begin():

            return connection.execute(
                sqlalchemy.select(eff_ind_table.c.data).where(
                    eff_ind_table.c.id == id
                    )
                ).one()

    def _pre_upgrade_15f7375ca737(self, connection):
        """Add data to the database before applying the 15f7375ca737 revision.

        This data will then be checked after applying the revision to ensure it
        was not affected by the db upgrade.

        """
        self.goal = utils.create_test_goal(
            id=1, uuid=w_utils.generate_uuid(),
            name="GOAL_1", display_name='Goal 1')
        self.strategy = utils.create_test_strategy(
            id=1, uuid=w_utils.generate_uuid(),
            name="STRATEGY_ID_1", display_name='My Strategy 1')
        self.audit_template = utils.create_test_audit_template(
            name="Audit Template", id=1, uuid=None)
        self._create_manual_audit(
            connection,
            audit_template_id=self.audit_template.id, id=1, uuid=None,
            name="AUDIT_1")
        self._create_manual_action_plan(
            connection,
            audit_id=1, id=1, uuid=None)

        self._create_manual_efficacy_indicator(
            connection,
            action_plan_id=1, id=1, uuid=None,
            name="efficacy_indicator1", description="Test Indicator 1",
            value=1.01234567912345678)
        self._create_manual_efficacy_indicator(
            connection,
            action_plan_id=1, id=2, uuid=None,
            name="efficacy_indicator2", description="Test Indicator 2",
            value=2.01234567912345678)

    def _check_15f7375ca737(self, connection):
        """Check data integrity after the database migration."""
        # check that creating a new efficacy_indicator after the migration
        # works
        utils.create_test_efficacy_indicator(
            action_plan_id=1, id=3, uuid=None,
            name="efficacy_indicator3", description="Test Indicator 3",
            value=0.01234567912345678)
        db_efficacy_indicator = self.dbapi.get_efficacy_indicator_by_id(
            self.context, 3)
        self.assertAlmostEqual(db_efficacy_indicator.value, 0.012, places=3)
        # check that the 'data' column of the efficacy_indicator created before
        # applying the revision is null for both efficacy_indicators
        self.assertIsNone(self._read_efficacy_indicator(connection, 1)[0])
        self.assertIsNone(self._read_efficacy_indicator(connection, 2)[0])

        # check that the existing data is there after the migration
        db_efficacy_indicator_1 = self.dbapi.get_efficacy_indicator_by_id(
            self.context, 1)
        self.assertAlmostEqual(db_efficacy_indicator_1.data,
                               1.00, places=2)
        self.assertAlmostEqual(db_efficacy_indicator_1.value,
                               1.00, places=2)
        self.assertEqual(db_efficacy_indicator_1.name, "efficacy_indicator1")
        # check that the 'data' column of the efficacy_indicator1 is now the
        # same as the 'value' column, i.e the data migration on load worked
        eff_ind_1_data = self._read_efficacy_indicator(connection, 1)[0]
        self.assertAlmostEqual(eff_ind_1_data,
                               1.00, places=2)

        # check that getting the efficacy_indicator using the
        # get_efficacy_indicator_list method reports the correct values
        efficacy_indicators = self.dbapi.get_efficacy_indicator_list(
            self.context)
        self.assertEqual(len(efficacy_indicators), 3)
        self.assertEqual(efficacy_indicators[0].id, 1)
        self.assertAlmostEqual(efficacy_indicators[0].value,
                               1.00, places=3)
        self.assertEqual(efficacy_indicators[1].id, 2)
        self.assertAlmostEqual(efficacy_indicators[1].value,
                               2.00, places=3)

        self.assertEqual(efficacy_indicators[2].id, 3)
        self.assertAlmostEqual(efficacy_indicators[2].value,
                               0.012, places=3)
        # check that the 'data' column of the efficacy_indicator1 is now the
        # same as the 'value' column, i.e the data migration on load worked
        # after the call to get_efficacy_indicator_list
        eff_ind_2_data = self._read_efficacy_indicator(connection, 2)[0]
        self.assertAlmostEqual(eff_ind_2_data,
                               2.00, places=2)

    def _check_7150a7d8f228(self, connection):
        """Check new columen status_message have been created."""
        self.assertTrue(
            oslodbutils.column_exists(
                connection, "action_plans", "status_message")
        )
        self.assertTrue(
            oslodbutils.column_exists(
                connection, "actions", "status_message")
        )
        self.assertTrue(
            oslodbutils.column_exists(
                connection, "audits", "status_message")
        )

    def test_migration_revisions(self):
        with self.engine.connect() as connection:
            self.alembic_config.attributes["connection"] = connection
            script = ScriptDirectory.from_config(self.alembic_config)
            revisions = [x.revision for x in script.walk_revisions()]

            # for some reason, 'walk_revisions' gives us the revisions in
            # reverse chronological order so we have to invert this
            revisions.reverse()

            for revision in revisions:
                LOG.info('Testing revision %s', revision)
                self._apply_migration(connection, revision)
