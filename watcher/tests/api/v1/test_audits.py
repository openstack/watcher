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
import json
import mock

from oslo_config import cfg
from oslo_utils import timeutils
from wsme import types as wtypes

from six.moves.urllib import parse as urlparse
from watcher.api.controllers.v1 import audit as api_audit
from watcher.common import utils
from watcher.db import api as db_api
from watcher.decision_engine import rpcapi as deapi
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


def post_get_test_audit_with_predefined_strategy(**kw):
    spec = kw.pop('strategy_parameters_spec', {})
    strategy_id = 2
    strategy = db_utils.get_test_strategy(parameters_spec=spec, id=strategy_id)

    audit_template = db_utils.get_test_audit_template(
        strategy_id=strategy['id'])

    audit = api_utils.audit_post_data(**kw)
    del audit['audit_template_id']
    audit['audit_template_uuid'] = audit_template['uuid']

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
        audit_fields = ['audit_type', 'deadline', 'state']
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
                name='at{0}'.format(id_),
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
        cfg.CONF.set_override('max_limit', 3, 'api',
                              enforce_type=True)
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

    def test_detail_filter_by_audit_template_uuid(self):
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

        response = self.get_json('/audits/detail?audit_template=%s'
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
            self.assertIsNone(audit['audit_template_uuid'])

        for id_ in range(2, 4):
            audit = response['audits'][id_]
            self.assertEqual(audit_template2.uuid,
                             audit['audit_template_uuid'])


class TestPatch(api_base.FunctionalTest):

    def setUp(self):
        super(TestPatch, self).setUp()
        obj_utils.create_test_audit_template(self.context)
        self.audit = obj_utils.create_test_audit(self.context)
        p = mock.patch.object(db_api.BaseConnection, 'update_audit')
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
        new_state = 'SUCCEEDED'
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
        p = mock.patch.object(db_api.BaseConnection, 'create_audit')
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

        audit_dict = post_get_test_audit(state=objects.audit.State.PENDING)
        del audit_dict['uuid']
        del audit_dict['state']
        del audit_dict['interval']

        response = self.post_json('/audits', audit_dict)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(201, response.status_int)
        # Check location header
        self.assertIsNotNone(response.location)
        expected_location = '/v1/audits/%s' % response.json['uuid']
        self.assertEqual(urlparse.urlparse(response.location).path,
                         expected_location)
        self.assertEqual(objects.audit.State.PENDING,
                         response.json['state'])
        self.assertNotIn('updated_at', response.json.keys)
        self.assertNotIn('deleted_at', response.json.keys)
        return_created_at = timeutils.parse_isotime(
            response.json['created_at']).replace(tzinfo=None)
        self.assertEqual(test_time, return_created_at)

    @mock.patch.object(deapi.DecisionEngineAPI, 'trigger_audit')
    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_create_audit_with_state_not_allowed(self, mock_utcnow,
                                                 mock_trigger_audit):
        mock_trigger_audit.return_value = mock.ANY
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time

        audit_dict = post_get_test_audit(state=objects.audit.State.SUCCEEDED)

        response = self.post_json('/audits', audit_dict, expect_errors=True)
        self.assertEqual(400, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_create_audit_invalid_audit_template_uuid(self, mock_utcnow):
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time

        audit_dict = post_get_test_audit()
        del audit_dict['uuid']
        del audit_dict['state']
        del audit_dict['interval']
        # Make the audit template UUID some garbage value
        audit_dict['audit_template_uuid'] = (
            '01234567-8910-1112-1314-151617181920')

        response = self.post_json('/audits', audit_dict, expect_errors=True)
        self.assertEqual(400, response.status_int)
        self.assertEqual("application/json", response.content_type)
        expected_error_msg = ('The audit template UUID or name specified is '
                              'invalid')
        self.assertTrue(response.json['error_message'])
        self.assertTrue(expected_error_msg in response.json['error_message'])

    @mock.patch.object(deapi.DecisionEngineAPI, 'trigger_audit')
    def test_create_audit_doesnt_contain_id(self, mock_trigger_audit):
        mock_trigger_audit.return_value = mock.ANY

        audit_dict = post_get_test_audit(state=objects.audit.State.PENDING)
        state = audit_dict['state']
        del audit_dict['uuid']
        del audit_dict['state']
        del audit_dict['interval']
        with mock.patch.object(self.dbapi, 'create_audit',
                               wraps=self.dbapi.create_audit) as cn_mock:
            response = self.post_json('/audits', audit_dict)
            self.assertEqual(state, response.json['state'])
            cn_mock.assert_called_once_with(mock.ANY)
            # Check that 'id' is not in first arg of positional args
            self.assertNotIn('id', cn_mock.call_args[0][0])

    @mock.patch.object(deapi.DecisionEngineAPI, 'trigger_audit')
    def test_create_audit_generate_uuid(self, mock_trigger_audit):
        mock_trigger_audit.return_value = mock.ANY

        audit_dict = post_get_test_audit()
        del audit_dict['uuid']
        del audit_dict['state']
        del audit_dict['interval']

        response = self.post_json('/audits', audit_dict)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(201, response.status_int)
        self.assertEqual(objects.audit.State.PENDING,
                         response.json['state'])
        self.assertTrue(utils.is_uuid_like(response.json['uuid']))

    @mock.patch.object(deapi.DecisionEngineAPI, 'trigger_audit')
    def test_create_continuous_audit_with_period(self, mock_trigger_audit):
        mock_trigger_audit.return_value = mock.ANY

        audit_dict = post_get_test_audit()
        del audit_dict['uuid']
        del audit_dict['state']
        audit_dict['audit_type'] = objects.audit.AuditType.CONTINUOUS.value
        audit_dict['interval'] = 1200

        response = self.post_json('/audits', audit_dict)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(201, response.status_int)
        self.assertEqual(objects.audit.State.PENDING,
                         response.json['state'])
        self.assertEqual(audit_dict['interval'], response.json['interval'])
        self.assertTrue(utils.is_uuid_like(response.json['uuid']))

    @mock.patch.object(deapi.DecisionEngineAPI, 'trigger_audit')
    def test_create_continuous_audit_without_period(self, mock_trigger_audit):
        mock_trigger_audit.return_value = mock.ANY

        audit_dict = post_get_test_audit()
        del audit_dict['uuid']
        del audit_dict['state']
        audit_dict['audit_type'] = objects.audit.AuditType.CONTINUOUS.value
        del audit_dict['interval']

        response = self.post_json('/audits', audit_dict, expect_errors=True)
        self.assertEqual(400, response.status_int)
        self.assertEqual('application/json', response.content_type)
        expected_error_msg = ('Interval of audit must be specified '
                              'for CONTINUOUS.')
        self.assertTrue(response.json['error_message'])
        self.assertTrue(expected_error_msg in response.json['error_message'])

    @mock.patch.object(deapi.DecisionEngineAPI, 'trigger_audit')
    def test_create_oneshot_audit_with_period(self, mock_trigger_audit):
        mock_trigger_audit.return_value = mock.ANY

        audit_dict = post_get_test_audit()
        del audit_dict['uuid']
        del audit_dict['state']
        audit_dict['audit_type'] = objects.audit.AuditType.ONESHOT.value
        audit_dict['interval'] = 1200

        response = self.post_json('/audits', audit_dict, expect_errors=True)
        self.assertEqual(400, response.status_int)
        self.assertEqual('application/json', response.content_type)
        expected_error_msg = 'Interval of audit must not be set for ONESHOT.'
        self.assertTrue(response.json['error_message'])
        self.assertTrue(expected_error_msg in response.json['error_message'])

    def test_create_audit_trigger_decision_engine(self):
        with mock.patch.object(deapi.DecisionEngineAPI,
                               'trigger_audit') as de_mock:
            audit_dict = post_get_test_audit(state=objects.audit.State.PENDING)
            del audit_dict['uuid']
            del audit_dict['state']
            del audit_dict['interval']
            response = self.post_json('/audits', audit_dict)
            de_mock.assert_called_once_with(mock.ANY, response.json['uuid'])

    @mock.patch.object(deapi.DecisionEngineAPI, 'trigger_audit')
    def test_create_audit_with_uuid(self, mock_trigger_audit):
        mock_trigger_audit.return_value = mock.ANY

        audit_dict = post_get_test_audit(state=objects.audit.State.PENDING)
        response = self.post_json('/audits', audit_dict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)
        assert not mock_trigger_audit.called

    @mock.patch.object(deapi.DecisionEngineAPI, 'trigger_audit')
    def test_create_audit_parameters_no_predefined_strategy(
            self, mock_trigger_audit):
        mock_trigger_audit.return_value = mock.ANY
        audit_dict = post_get_test_audit(parameters={'name': 'Tom'})
        del audit_dict['uuid']
        del audit_dict['state']
        del audit_dict['interval']

        response = self.post_json('/audits', audit_dict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)
        expected_error_msg = ('Specify parameters but no predefined '
                              'strategy for audit template, or no '
                              'parameter spec in predefined strategy')
        self.assertTrue(response.json['error_message'])
        self.assertTrue(expected_error_msg in response.json['error_message'])
        assert not mock_trigger_audit.called

    @mock.patch.object(deapi.DecisionEngineAPI, 'trigger_audit')
    def test_create_audit_parameters_no_schema(
            self, mock_trigger_audit):
        mock_trigger_audit.return_value = mock.ANY
        audit_dict = post_get_test_audit_with_predefined_strategy(
            parameters={'name': 'Tom'})
        del audit_dict['uuid']
        del audit_dict['state']
        del audit_dict['interval']

        response = self.post_json('/audits', audit_dict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)
        expected_error_msg = ('Specify parameters but no predefined '
                              'strategy for audit template, or no '
                              'parameter spec in predefined strategy')
        self.assertTrue(response.json['error_message'])
        self.assertTrue(expected_error_msg in response.json['error_message'])
        assert not mock_trigger_audit.called


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
        p = mock.patch.object(db_api.BaseConnection, 'update_audit')
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
        self.assertEqual('DELETED', audit['state'])

    def test_delete_audit_not_found(self):
        uuid = utils.generate_uuid()
        response = self.delete('/audits/%s' % uuid, expect_errors=True)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])


class TestAuaditPolicyEnforcement(api_base.FunctionalTest):

    def _common_policy_check(self, rule, func, *arg, **kwarg):
        self.policy.set_rules({
            "admin_api": "(role:admin or role:administrator)",
            "default": "rule:admin_api",
            rule: "rule:defaut"})
        response = func(*arg, **kwarg)
        self.assertEqual(403, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(
            "Policy doesn't allow %s to be performed." % rule,
            json.loads(response.json['error_message'])['faultstring'])

    def test_policy_disallow_get_all(self):
        self._common_policy_check(
            "audit:get_all", self.get_json, '/audits',
            expect_errors=True)

    def test_policy_disallow_get_one(self):
        audit = obj_utils.create_test_audit(self.context)
        self._common_policy_check(
            "audit:get", self.get_json,
            '/audits/%s' % audit.uuid,
            expect_errors=True)

    def test_policy_disallow_detail(self):
        self._common_policy_check(
            "audit:detail", self.get_json,
            '/audits/detail',
            expect_errors=True)

    def test_policy_disallow_update(self):
        audit = obj_utils.create_test_audit(self.context)
        self._common_policy_check(
            "audit:update", self.patch_json,
            '/audits/%s' % audit.uuid,
            [{'path': '/state', 'value': 'SUBMITTED', 'op': 'replace'}],
            expect_errors=True)

    def test_policy_disallow_create(self):
        audit_dict = post_get_test_audit(state=objects.audit.State.PENDING)
        del audit_dict['uuid']
        del audit_dict['state']
        self._common_policy_check(
            "audit:create", self.post_json, '/audits', audit_dict,
            expect_errors=True)

    def test_policy_disallow_delete(self):
        audit = obj_utils.create_test_audit(self.context)
        self._common_policy_check(
            "audit:delete", self.delete,
            '/audits/%s' % audit.uuid, expect_errors=True)


class TestAuditEnforcementWithAdminContext(TestListAudit,
                                           api_base.AdminRoleTest):

    def setUp(self):
        super(TestAuditEnforcementWithAdminContext, self).setUp()
        self.policy.set_rules({
            "admin_api": "(role:admin or role:administrator)",
            "default": "rule:admin_api",
            "audit:create": "rule:default",
            "audit:delete": "rule:default",
            "audit:detail": "rule:default",
            "audit:get": "rule:default",
            "audit:get_all": "rule:default",
            "audit:update": "rule:default"})
