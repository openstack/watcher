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

"""Tests for custom SQLAlchemy types via Magnum DB."""

from oslo_db import exception as db_exc

from watcher.common import utils as w_utils
from watcher.db import api as dbapi
import watcher.db.sqlalchemy.api as sa_api
from watcher.db.sqlalchemy import models
from watcher.tests.db import base


class SqlAlchemyCustomTypesTestCase(base.DbTestCase):

    def setUp(self):
        super(SqlAlchemyCustomTypesTestCase, self).setUp()
        self.dbapi = dbapi.get_instance()

    def test_JSONEncodedDict_default_value(self):
        # Create audit_template w/o extra
        audit_template1_id = w_utils.generate_uuid()
        self.dbapi.create_audit_template({'uuid': audit_template1_id})
        audit_template1 = sa_api.model_query(models.AuditTemplate) \
                                .filter_by(uuid=audit_template1_id).one()
        self.assertEqual({}, audit_template1.extra)

        # Create audit_template with extra
        audit_template2_id = w_utils.generate_uuid()
        self.dbapi.create_audit_template({'uuid': audit_template2_id,
                                          'extra': {'bar': 'foo'}})
        audit_template2 = sa_api.model_query(models.AuditTemplate) \
                                .filter_by(uuid=audit_template2_id).one()
        self.assertEqual('foo', audit_template2.extra['bar'])

    def test_JSONEncodedDict_type_check(self):
        self.assertRaises(db_exc.DBError,
                          self.dbapi.create_audit_template,
                          {'extra': ['this is not a dict']})

    # def test_JSONEncodedList_default_value(self):
    #     # Create audit_template w/o images
    #     audit_template1_id = w_utils.generate_uuid()
    #     self.dbapi.create_audit_template({'uuid': audit_template1_id})
    #     audit_template1 = sa_api.model_query(models.AuditTemplate) \
    #                     .filter_by(uuid=audit_template1_id).one()
    #     self.assertEqual([], audit_template1.images)

    #     # Create audit_template with images
    #     audit_template2_id = w_utils.generate_uuid()
    #     self.dbapi.create_audit_template({'uuid': audit_template2_id,
    #                               'images': ['myimage1', 'myimage2']})
    #     audit_template2 = sa_api.model_query(models.AuditTemplate) \
    #                     .filter_by(uuid=audit_template2_id).one()
    #     self.assertEqual(['myimage1', 'myimage2'], audit_template2.images)

    # def test_JSONEncodedList_type_check(self):
    #     self.assertRaises(db_exc.DBError,
    #                       self.dbapi.create_audit_template,
    #                       {'images': {'this is not a list': 'test'}})
