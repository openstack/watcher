# Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

import datetime

import mock
from oslo_config import cfg
from oslo_utils import timeutils
from wsme import types as wtypes

from six.moves.urllib import parse as urlparse
from watcher.api.controllers.v1 import audit as api_audit
from watcher.common import utils
from watcher.db import api as db_api
from watcher.decision_engine.framework import rpcapi as deapi
from watcher import objects
from watcher.tests.api import base as api_base
from watcher.tests.api import utils as api_utils
from watcher.tests import base
from watcher.tests.db import utils as db_utils
from watcher.tests.objects import utils as obj_utils


def post_get_test_audit(**kw):
    audit = api_utils.audit_post_data(**kw)
    audit_template = db_utils.get_test_audit_template()
    del audit['audit_template_id']
    audit['audit_template_uuid'] = kw.get('audit_template_uuid',
                                          audit_template['uuid'])
    return audit


class TestAuditObject(base.TestCase):

    def test_audit_init(self):
        audit_dict = api_utils.audit_post_data(audit_template_id=None)
        del audit_dict['state']
        audit = api_audit.Audit(**audit_dict)
        self.assertEqual(wtypes.Unset, audit.state)


class TestListAudit(api_base.FunctionalTest):

    def setUp(self):
        super(TestListAudit, self).setUp()
        obj_utils.create_test_audit_template(self.context)

    def test_empty(self):
        response = self.get_json('/audits')
        self.assertEqual([], response['audits'])

    def _assert_audit_fields(self, audit):
        audit_fields = ['type', 'deadline', 'state']
        for field in audit_fields:
            self.assertIn(field, audit)

    def test_one(self):
        audit = obj_utils.create_test_audit(self.context)
        response = self.get_json('/audits')
        self.assertEqual(audit.uuid, response['audits'][0]["uuid"])
        self._assert_audit_fields(response['audits'][0])

    def test_one_soft_deleted(self):
        audit = obj_utils.create_test_audit(self.context)
        audit.soft_delete()
        response = self.get_json('/audits',
                                 headers={'X-Show-Deleted': 'True'})
        self.assertEqual(audit.uuid, response['audits'][0]["uuid"])
        self._assert_audit_fields(response['audits'][0])

        response = self.get_json('/audits')
        self.assertEqual([], response['audits'])

    def test_get_one(self):
        audit = obj_utils.create_test_audit(self.context)
        response = self.get_json('/audits/%s' % audit['uuid'])
        self.assertEqual(audit.uuid, response['uuid'])
        self._assert_audit_fields(response)

    def test_get_one_soft_deleted(self):
        audit = obj_utils.create_test_audit(self.context)
        audit.soft_delete()
        response = self.get_json('/audits/%s' % audit['uuid'],
                                 headers={'X-Show-Deleted': 'True'})
        self.assertEqual(audit.uuid, response['uuid'])
        self._assert_audit_fields(response)

        response = self.get_json('/audits/%s' % audit['uuid'],
                                 expect_errors=True)
        self.assertEqual(404, response.status_int)

    def test_detail(self):
        audit = obj_utils.create_test_audit(self.context)
        response = self.get_json('/audits/detail')
        self.assertEqual(audit.uuid, response['audits'][0]["uuid"])
        self._assert_audit_fields(response['audits'][0])

    def test_detail_soft_deleted(self):
        audit = obj_utils.create_test_audit(self.context)
        audit.soft_delete()
        response = self.get_json('/audits/detail',
                                 headers={'X-Show-Deleted': 'True'})
        self.assertEqual(audit.uuid, response['audits'][0]["uuid"])
        self._assert_audit_fields(response['audits'][0])

        response = self.get_json('/audits/detail')
        self.assertEqual([], response['audits'])

    def test_detail_against_single(self):
        audit = obj_utils.create_test_audit(self.context)
        response = self.get_json('/audits/%s/detail' % audit['uuid'],
                                 expect_errors=True)
        self.assertEqual(404, response.status_int)

    def test_many(self):
        audit_list = []
        for id_ in range(5):
            audit = obj_utils.create_test_audit(self.context, id=id_,
                                                uuid=utils.generate_uuid())
            audit_list.append(audit.uuid)
        response = self.get_json('/audits')
        self.assertEqual(len(audit_list), len(response['audits']))
        uuids = [s['uuid'] for s in response['audits']]
        self.assertEqual(sorted(audit_list), sorted(uuids))

    def test_many_without_soft_deleted(self):
        audit_list = []
        for id_ in [1, 2, 3]:
            audit = obj_utils.create_test_audit(self.context, id=id_,
                                                uuid=utils.generate_uuid())
            audit_list.append(audit.uuid)
        for id_ in [4, 5]:
            audit = obj_utils.create_test_audit(self.context, id=id_,
                                                uuid=utils.generate_uuid())
            audit.soft_delete()
        response = self.get_json('/audits')
        self.assertEqual(3, len(response['audits']))
        uuids = [s['uuid'] for s in response['audits']]
        self.assertEqual(sorted(audit_list), sorted(uuids))

    def test_many_with_soft_deleted(self):
        audit_list = []
        for id_ in [1, 2, 3]:
            audit = obj_utils.create_test_audit(self.context, id=id_,
                                                uuid=utils.generate_uuid())
            audit_list.append(audit.uuid)
        for id_ in [4, 5]:
            audit = obj_utils.create_test_audit(self.context, id=id_,
                                                uuid=utils.generate_uuid())
            audit.soft_delete()
            audit_list.append(audit.uuid)
        response = self.get_json('/audits',
                                 headers={'X-Show-Deleted': 'True'})
        self.assertEqual(5, len(response['audits']))
        uuids = [s['uuid'] for s in response['audits']]
        self.assertEqual(sorted(audit_list), sorted(uuids))

    def test_many_with_sort_key_audit_template_uuid(self):
        audit_template_list = []
        for id_ in range(5):
            audit_template = obj_utils.create_test_audit_template(
                self.context,
                name='at' + str(id_),
                uuid=utils.generate_uuid())
            obj_utils.create_test_audit(
                self.context, id=id_, uuid=utils.generate_uuid(),
                audit_template_id=audit_template.id)
            audit_template_list.append(audit_template.uuid)

        response = self.get_json('/audits/?sort_key=audit_template_uuid')

        self.assertEqual(5, len(response['audits']))
        uuids = [s['audit_template_uuid'] for s in response['audits']]
        self.assertEqual(sorted(audit_template_list), uuids)

    def test_links(self):
        uuid = utils.generate_uuid()
        obj_utils.create_test_audit(self.context, id=1, uuid=uuid)
        response = self.get_json('/audits/%s' % uuid)
        self.assertIn('links', response.keys())
        self.assertEqual(2, len(response['links']))
        self.assertIn(uuid, response['links'][0]['href'])
        for l in response['links']:
            bookmark = l['rel'] == 'bookmark'
            self.assertTrue(self.validate_link(l['href'], bookmark=bookmark))

    def test_collection_links(self):
        for id_ in range(5):
            obj_utils.create_test_audit(self.context, id=id_,
                                        uuid=utils.generate_uuid())
        response = self.get_json('/audits/?limit=3')
        self.assertEqual(3, len(response['audits']))

        next_marker = response['audits'][-1]['uuid']
        self.assertIn(next_marker, response['next'])

    def test_collection_links_default_limit(self):
        cfg.CONF.set_override('max_limit', 3, 'api')
        for id_ in range(5):
            obj_utils.create_test_audit(self.context, id=id_,
                                        uuid=utils.generate_uuid())
        response = self.get_json('/audits')
        self.assertEqual(3, len(response['audits']))

        next_marker = response['audits'][-1]['uuid']
        self.assertIn(next_marker, response['next'])

    def test_filter_by_audit_template_uuid(self):
        audit_template_uuid = utils.generate_uuid()
        audit_template_name = 'My_Audit_Template'

        audit_template = obj_utils.create_test_audit_template(
            self.context,
            uuid=audit_template_uuid,
            name=audit_template_name)
        number_of_audits_with_audit_template_id = 5
        for id_ in range(number_of_audits_with_audit_template_id):
            obj_utils.create_test_audit(self.context, id=id_,
                                        uuid=utils.generate_uuid(),
                                        audit_template_id=audit_template.id)
        for id_ in range(6, 8):
            obj_utils.create_test_audit(self.context, id=id_,
                                        uuid=utils.generate_uuid())

        response = self.get_json('/audits/?audit_template=%s'
                                 % audit_template_uuid)

        audits = response['audits']
        self.assertEqual(5, len(audits))
        for audit in audits:
            self.assertEqual(audit_template_uuid,
                             audit['audit_template_uuid'])

    def test_filter_by_audit_template_name(self):
        audit_template_uuid = utils.generate_uuid()
        audit_template_name = 'My_Audit_Template'

        audit_template = obj_utils.create_test_audit_template(
            self.context,
            uuid=audit_template_uuid,
            name=audit_template_name)

        number_of_audits_with_audit_template_id = 5
        for id_ in range(number_of_audits_with_audit_template_id):
            obj_utils.create_test_audit(self.context, id=id_,
                                        uuid=utils.generate_uuid(),
                                        audit_template_id=audit_template.id)
        for id_ in range(6, 8):
            obj_utils.create_test_audit(self.context, id=id_,
                                        uuid=utils.generate_uuid())

        response = self.get_json('/audits/?audit_template=%s'
                                 % audit_template_name)

        audits = response['audits']
        self.assertEqual(5, len(audits))
        for audit in audits:
            self.assertEqual(audit_template_uuid,
                             audit['audit_template_uuid'])

    def test_many_by_soft_deleted_audit_template(self):
        audit_list = []
        audit_template1 = obj_utils.create_test_audit_template(
            self.context,
            uuid=utils.generate_uuid(),
            name='at1',
            id=3,
        )

        audit_template2 = obj_utils.create_test_audit_template(
            self.context,
            uuid=utils.generate_uuid(),
            name='at2',
            id=4,
        )

        for id_ in range(0, 2):
            audit = obj_utils.create_test_audit(
                self.context, id=id_,
                uuid=utils.generate_uuid(),
                audit_template_id=audit_template1.id)
            audit_list.append(audit.uuid)

        for id_ in range(2, 4):
            audit = obj_utils.create_test_audit(
                self.context, id=id_,
                uuid=utils.generate_uuid(),
                audit_template_id=audit_template2.id)
            audit_list.append(audit.uuid)

        self.delete('/audit_templates/%s' % audit_template1.uuid)

        response = self.get_json('/audits')

        self.assertEqual(len(audit_list), len(response['audits']))

        for id_ in range(0, 2):
            audit = response['audits'][id_]
            self.assertEqual(None, audit['audit_template_uuid'])

        for id_ in range(2, 4):
            audit = response['audits'][id_]
            self.assertEqual(audit_template2.uuid,
                             audit['audit_template_uuid'])


class TestPatch(api_base.FunctionalTest):

    def setUp(self):
        super(TestPatch, self).setUp()
        obj_utils.create_test_audit_template(self.context)
        self.audit = obj_utils.create_test_audit(self.context)
        p = mock.patch.object(db_api.Connection, 'update_audit')
        self.mock_audit_update = p.start()
        self.mock_audit_update.side_effect = self._simulate_rpc_audit_update
        self.addCleanup(p.stop)

    def _simulate_rpc_audit_update(self, audit):
        audit.save()
        return audit

    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_replace_ok(self, mock_utcnow):
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time

        new_state = 'SUBMITTED'
        response = self.get_json('/audits/%s' % self.audit.uuid)
        self.assertNotEqual(new_state, response['state'])

        response = self.patch_json(
            '/audits/%s' % self.audit.uuid,
            [{'path': '/state', 'value': new_state,
             'op': 'replace'}])
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(200, response.status_code)

        response = self.get_json('/audits/%s' % self.audit.uuid)
        self.assertEqual(new_state, response['state'])
        return_updated_at = timeutils.parse_isotime(
            response['updated_at']).replace(tzinfo=None)
        self.assertEqual(test_time, return_updated_at)

    def test_replace_non_existent_audit(self):
        response = self.patch_json('/audits/%s' % utils.generate_uuid(),
                                   [{'path': '/state', 'value': 'SUBMITTED',
                                     'op': 'replace'}],
                                   expect_errors=True)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    def test_add_ok(self):
        new_state = 'SUCCESS'
        response = self.patch_json(
            '/audits/%s' % self.audit.uuid,
            [{'path': '/state', 'value': new_state, 'op': 'add'}])
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(200, response.status_int)

        response = self.get_json('/audits/%s' % self.audit.uuid)
        self.assertEqual(new_state, response['state'])

    def test_add_non_existent_property(self):
        response = self.patch_json(
            '/audits/%s' % self.audit.uuid,
            [{'path': '/foo', 'value': 'bar', 'op': 'add'}],
            expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)
        self.assertTrue(response.json['error_message'])

    def test_remove_ok(self):
        response = self.get_json('/audits/%s' % self.audit.uuid)
        self.assertIsNotNone(response['state'])

        response = self.patch_json('/audits/%s' % self.audit.uuid,
                                   [{'path': '/state', 'op': 'remove'}])
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(200, response.status_code)

        response = self.get_json('/audits/%s' % self.audit.uuid)
        self.assertIsNone(response['state'])

    def test_remove_uuid(self):
        response = self.patch_json('/audits/%s' % self.audit.uuid,
                                   [{'path': '/uuid', 'op': 'remove'}],
                                   expect_errors=True)
        self.assertEqual(400, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    def test_remove_non_existent_property(self):
        response = self.patch_json(
            '/audits/%s' % self.audit.uuid,
            [{'path': '/non-existent', 'op': 'remove'}],
            expect_errors=True)
        self.assertEqual(400, response.status_code)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])


class TestPost(api_base.FunctionalTest):

    def setUp(self):
        super(TestPost, self).setUp()
        obj_utils.create_test_audit_template(self.context)
        p = mock.patch.object(db_api.Connection, 'create_audit')
        self.mock_create_audit = p.start()
        self.mock_create_audit.side_effect = (
            self._simulate_rpc_audit_create)
        self.addCleanup(p.stop)

    def _simulate_rpc_audit_create(self, audit):
        audit.create()
        return audit

    @mock.patch.object(deapi.DecisionEngineAPI, 'trigger_audit')
    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_create_audit(self, mock_utcnow, mock_trigger_audit):
        mock_trigger_audit.return_value = mock.ANY
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time

        audit_dict = post_get_test_audit()

        response = self.post_json('/audits', audit_dict)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(201, response.status_int)
        # Check location header
        self.assertIsNotNone(response.location)
        expected_location = '/v1/audits/%s' % audit_dict['uuid']
        self.assertEqual(urlparse.urlparse(response.location).path,
                         expected_location)
        self.assertEqual(audit_dict['uuid'], response.json['uuid'])
        self.assertEqual(objects.audit.AuditStatus.PENDING,
                         response.json['state'])
        self.assertNotIn('updated_at', response.json.keys)
        self.assertNotIn('deleted_at', response.json.keys)
        return_created_at = timeutils.parse_isotime(
            response.json['created_at']).replace(tzinfo=None)
        self.assertEqual(test_time, return_created_at)

    @mock.patch.object(deapi.DecisionEngineAPI, 'trigger_audit')
    def test_create_audit_doesnt_contain_id(self, mock_trigger_audit):
        mock_trigger_audit.return_value = mock.ANY

        audit_dict = post_get_test_audit(state='ONGOING')
        with mock.patch.object(self.dbapi, 'create_audit',
                               wraps=self.dbapi.create_audit) as cn_mock:
            response = self.post_json('/audits', audit_dict)
            self.assertEqual(audit_dict['state'], response.json['state'])
            cn_mock.assert_called_once_with(mock.ANY)
            # Check that 'id' is not in first arg of positional args
            self.assertNotIn('id', cn_mock.call_args[0][0])

    @mock.patch.object(deapi.DecisionEngineAPI, 'trigger_audit')
    def test_create_audit_generate_uuid(self, mock_trigger_audit):
        mock_trigger_audit.return_value = mock.ANY

        audit_dict = post_get_test_audit()
        del audit_dict['uuid']

        response = self.post_json('/audits', audit_dict)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(201, response.status_int)
        self.assertEqual(objects.audit.AuditStatus.PENDING,
                         response.json['state'])
        self.assertTrue(utils.is_uuid_like(response.json['uuid']))

    def test_create_audit_trigger_decision_engine(self):
        with mock.patch.object(deapi.DecisionEngineAPI,
                               'trigger_audit') as de_mock:
            audit_dict = post_get_test_audit(state='ONGOING')
            self.post_json('/audits', audit_dict)
            de_mock.assert_called_once_with(mock.ANY, audit_dict['uuid'])


# class TestDelete(api_base.FunctionalTest):

#     def setUp(self):
#         super(TestDelete, self).setUp()
#         self.audit = obj_utils.create_test_audit(self.context)
#         p = mock.patch.object(db_api.Connection, 'destroy_audit')
#         self.mock_audit_delete = p.start()
#         self.mock_audit_delete.side_effect = self._simulate_rpc_audit_delete
#         self.addCleanup(p.stop)

#     def _simulate_rpc_audit_delete(self, audit_uuid):
#         audit = objects.Audit.get_by_uuid(self.context, audit_uuid)
#         audit.destroy()

#     def test_delete_audit(self):
#         self.delete('/audits/%s' % self.audit.uuid)
#         response = self.get_json('/audits/%s' % self.audit.uuid,
#                                  expect_errors=True)
#         self.assertEqual(404, response.status_int)
#         self.assertEqual('application/json', response.content_type)
#         self.assertTrue(response.json['error_message'])

#     def test_delete_audit_not_found(self):
#         uuid = utils.generate_uuid()
#         response = self.delete('/audits/%s' % uuid, expect_errors=True)
#         self.assertEqual(404, response.status_int)
#         self.assertEqual('application/json', response.content_type)
#         self.assertTrue(response.json['error_message'])

class TestDelete(api_base.FunctionalTest):

    def setUp(self):
        super(TestDelete, self).setUp()
        obj_utils.create_test_audit_template(self.context)
        self.audit = obj_utils.create_test_audit(self.context)
        p = mock.patch.object(db_api.Connection, 'update_audit')
        self.mock_audit_update = p.start()
        self.mock_audit_update.side_effect = self._simulate_rpc_audit_update
        self.addCleanup(p.stop)

    def _simulate_rpc_audit_update(self, audit):
        audit.save()
        return audit

    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_delete_audit(self, mock_utcnow):
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time
        self.delete('/audits/%s' % self.audit.uuid)
        response = self.get_json('/audits/%s' % self.audit.uuid,
                                 expect_errors=True)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

        self.context.show_deleted = True
        audit = objects.Audit.get_by_uuid(self.context, self.audit.uuid)

        return_deleted_at = timeutils.strtime(audit['deleted_at'])
        self.assertEqual(timeutils.strtime(test_time), return_deleted_at)
        self.assertEqual(audit['state'], 'DELETED')

    def test_delete_audit_not_found(self):
        uuid = utils.generate_uuid()
        response = self.delete('/audits/%s' % uuid, expect_errors=True)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])
