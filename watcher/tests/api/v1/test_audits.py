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
from dateutil import tz
import itertools
import mock

from oslo_config import cfg
from oslo_serialization import jsonutils
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
    goal = db_utils.get_test_goal()
    del_keys = ['goal_id', 'strategy_id']
    del_keys.extend(kw.get('params_to_exclude', []))
    add_keys = {'audit_template_uuid': audit_template['uuid'],
                'goal': goal['uuid'],
                }
    if kw.get('use_named_goal'):
        add_keys['goal'] = 'TEST'
    for k in add_keys:
        audit[k] = kw.get(k, add_keys[k])
    for k in del_keys:
        del audit[k]
    return audit


def post_get_test_audit_with_predefined_strategy(**kw):
    spec = kw.pop('strategy_parameters_spec', {})
    strategy_id = 2
    strategy = db_utils.get_test_strategy(parameters_spec=spec, id=strategy_id)
    audit = api_utils.audit_post_data(**kw)
    audit_template = db_utils.get_test_audit_template(
        strategy_id=strategy['id'])
    del_keys = ['goal_id', 'strategy_id']
    add_keys = {'audit_template_uuid': audit_template['uuid'],
                }
    for k in del_keys:
        del audit[k]
    for k in add_keys:
        audit[k] = kw.get(k, add_keys[k])
    return audit


class TestAuditObject(base.TestCase):

    def test_audit_init(self):
        audit_dict = api_utils.audit_post_data(audit_template_id=None,
                                               goal_id=None,
                                               strategy_id=None)
        del audit_dict['state']
        audit = api_audit.Audit(**audit_dict)
        self.assertEqual(wtypes.Unset, audit.state)


class TestListAudit(api_base.FunctionalTest):

    def setUp(self):
        super(TestListAudit, self).setUp()
        obj_utils.create_test_goal(self.context)
        obj_utils.create_test_strategy(self.context)
        obj_utils.create_test_audit_template(self.context)

    def test_empty(self):
        response = self.get_json('/audits')
        self.assertEqual([], response['audits'])

    def _assert_audit_fields(self, audit):
        audit_fields = ['audit_type', 'scope', 'state', 'goal_uuid',
                        'strategy_uuid']
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
            audit = obj_utils.create_test_audit(
                self.context, id=id_,
                uuid=utils.generate_uuid(), name='My Audit {0}'.format(id_))
            audit_list.append(audit.uuid)
        response = self.get_json('/audits')
        self.assertEqual(len(audit_list), len(response['audits']))
        uuids = [s['uuid'] for s in response['audits']]
        self.assertEqual(sorted(audit_list), sorted(uuids))

    def test_many_without_soft_deleted(self):
        audit_list = []
        for id_ in [1, 2, 3]:
            audit = obj_utils.create_test_audit(
                self.context, id=id_,
                uuid=utils.generate_uuid(), name='My Audit {0}'.format(id_))
            audit_list.append(audit.uuid)
        for id_ in [4, 5]:
            audit = obj_utils.create_test_audit(
                self.context, id=id_,
                uuid=utils.generate_uuid(), name='My Audit {0}'.format(id_))
            audit.soft_delete()
        response = self.get_json('/audits')
        self.assertEqual(3, len(response['audits']))
        uuids = [s['uuid'] for s in response['audits']]
        self.assertEqual(sorted(audit_list), sorted(uuids))

    def test_many_with_soft_deleted(self):
        audit_list = []
        for id_ in [1, 2, 3]:
            audit = obj_utils.create_test_audit(
                self.context, id=id_,
                uuid=utils.generate_uuid(), name='My Audit {0}'.format(id_))
            audit_list.append(audit.uuid)
        for id_ in [4, 5]:
            audit = obj_utils.create_test_audit(
                self.context, id=id_,
                uuid=utils.generate_uuid(), name='My Audit {0}'.format(id_))
            audit.soft_delete()
            audit_list.append(audit.uuid)
        response = self.get_json('/audits',
                                 headers={'X-Show-Deleted': 'True'})
        self.assertEqual(5, len(response['audits']))
        uuids = [s['uuid'] for s in response['audits']]
        self.assertEqual(sorted(audit_list), sorted(uuids))

    def test_many_with_sort_key_goal_uuid(self):
        goal_list = []
        for id_ in range(5):
            goal = obj_utils.create_test_goal(
                self.context,
                name='gl{0}'.format(id_),
                uuid=utils.generate_uuid())
            obj_utils.create_test_audit(
                self.context, id=id_, uuid=utils.generate_uuid(),
                goal_id=goal.id, name='My Audit {0}'.format(id_))
            goal_list.append(goal.uuid)

        response = self.get_json('/audits/?sort_key=goal_uuid')

        self.assertEqual(5, len(response['audits']))
        uuids = [s['goal_uuid'] for s in response['audits']]
        self.assertEqual(sorted(goal_list), uuids)

    def test_sort_key_validation(self):
        response = self.get_json(
            '/audits?sort_key=%s' % 'bad_name',
            expect_errors=True)
        self.assertEqual(400, response.status_int)

    def test_links(self):
        uuid = utils.generate_uuid()
        obj_utils.create_test_audit(
            self.context, id=1, uuid=uuid,
            name='My Audit {0}'.format(1))
        response = self.get_json('/audits/%s' % uuid)
        self.assertIn('links', response.keys())
        self.assertEqual(2, len(response['links']))
        self.assertIn(uuid, response['links'][0]['href'])
        for l in response['links']:
            bookmark = l['rel'] == 'bookmark'
            self.assertTrue(self.validate_link(l['href'], bookmark=bookmark))

    def test_collection_links(self):
        for id_ in range(5):
            obj_utils.create_test_audit(
                self.context, id=id_,
                uuid=utils.generate_uuid(), name='My Audit {0}'.format(id_))
        response = self.get_json('/audits/?limit=3')
        self.assertEqual(3, len(response['audits']))

        next_marker = response['audits'][-1]['uuid']
        self.assertIn(next_marker, response['next'])

    def test_collection_links_default_limit(self):
        cfg.CONF.set_override('max_limit', 3, 'api')
        for id_ in range(5):
            obj_utils.create_test_audit(
                self.context, id=id_,
                uuid=utils.generate_uuid(), name='My Audit {0}'.format(id_))
        response = self.get_json('/audits')
        self.assertEqual(3, len(response['audits']))

        next_marker = response['audits'][-1]['uuid']
        self.assertIn(next_marker, response['next'])


class TestPatch(api_base.FunctionalTest):

    def setUp(self):
        super(TestPatch, self).setUp()
        obj_utils.create_test_goal(self.context)
        obj_utils.create_test_strategy(self.context)
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

        new_state = objects.audit.State.CANCELLED
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
        response = self.patch_json(
            '/audits/%s' % utils.generate_uuid(),
            [{'path': '/state', 'value': objects.audit.State.SUCCEEDED,
              'op': 'replace'}], expect_errors=True)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    def test_add_ok(self):
        new_state = objects.audit.State.SUCCEEDED
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
        self.assertIsNotNone(response['interval'])

        response = self.patch_json('/audits/%s' % self.audit.uuid,
                                   [{'path': '/interval', 'op': 'remove'}])
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(200, response.status_code)

        response = self.get_json('/audits/%s' % self.audit.uuid)
        self.assertIsNone(response['interval'])

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


ALLOWED_TRANSITIONS = [
    {"original_state": key, "new_state": value}
    for key, values in (
        objects.audit.AuditStateTransitionManager.TRANSITIONS.items())
    for value in values]


class TestPatchStateTransitionDenied(api_base.FunctionalTest):

    STATES = [
        ap_state for ap_state in objects.audit.State.__dict__
        if not ap_state.startswith("_")
    ]

    scenarios = [
        (
            "%s -> %s" % (original_state, new_state),
            {"original_state": original_state,
             "new_state": new_state},
        )
        for original_state, new_state
        in list(itertools.product(STATES, STATES))
        if original_state != new_state and
        {"original_state": original_state,
         "new_state": new_state} not in ALLOWED_TRANSITIONS
    ]

    def setUp(self):
        super(TestPatchStateTransitionDenied, self).setUp()
        obj_utils.create_test_goal(self.context)
        obj_utils.create_test_strategy(self.context)
        obj_utils.create_test_audit_template(self.context)
        self.audit = obj_utils.create_test_audit(self.context,
                                                 state=self.original_state)
        p = mock.patch.object(db_api.BaseConnection, 'update_audit')
        self.mock_audit_update = p.start()
        self.mock_audit_update.side_effect = self._simulate_rpc_audit_update
        self.addCleanup(p.stop)

    def _simulate_rpc_audit_update(self, audit):
        audit.save()
        return audit

    def test_replace_denied(self):
        response = self.get_json('/audits/%s' % self.audit.uuid)
        self.assertNotEqual(self.new_state, response['state'])

        response = self.patch_json(
            '/audits/%s' % self.audit.uuid,
            [{'path': '/state', 'value': self.new_state,
              'op': 'replace'}],
            expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_code)
        self.assertTrue(response.json['error_message'])

        response = self.get_json('/audits/%s' % self.audit.uuid)
        self.assertEqual(self.original_state, response['state'])


class TestPatchStateTransitionOk(api_base.FunctionalTest):

    scenarios = [
        (
            "%s -> %s" % (transition["original_state"],
                          transition["new_state"]),
            transition
        )
        for transition in ALLOWED_TRANSITIONS
    ]

    def setUp(self):
        super(TestPatchStateTransitionOk, self).setUp()
        obj_utils.create_test_goal(self.context)
        obj_utils.create_test_strategy(self.context)
        obj_utils.create_test_audit_template(self.context)
        self.audit = obj_utils.create_test_audit(self.context,
                                                 state=self.original_state)
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

        response = self.get_json('/audits/%s' % self.audit.uuid)
        self.assertNotEqual(self.new_state, response['state'])

        response = self.patch_json(
            '/audits/%s' % self.audit.uuid,
            [{'path': '/state', 'value': self.new_state,
             'op': 'replace'}])
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(200, response.status_code)

        response = self.get_json('/audits/%s' % self.audit.uuid)
        self.assertEqual(self.new_state, response['state'])
        return_updated_at = timeutils.parse_isotime(
            response['updated_at']).replace(tzinfo=None)
        self.assertEqual(test_time, return_updated_at)


class TestPost(api_base.FunctionalTest):

    def setUp(self):
        super(TestPost, self).setUp()
        obj_utils.create_test_goal(self.context)
        obj_utils.create_test_strategy(self.context)
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

        audit_dict = post_get_test_audit(
            state=objects.audit.State.PENDING,
            params_to_exclude=['uuid', 'state', 'interval', 'scope',
                               'next_run_time', 'hostname', 'goal'])

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
    def test_create_audit_with_at_uuid_and_goal_specified(self, mock_utcnow):
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time

        audit_dict = post_get_test_audit(
            state=objects.audit.State.PENDING,
            params_to_exclude=['uuid', 'state', 'interval', 'scope',
                               'next_run_time', 'hostname'])

        response = self.post_json('/audits', audit_dict, expect_errors=True)
        self.assertEqual(400, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    @mock.patch.object(deapi.DecisionEngineAPI, 'trigger_audit')
    def test_create_audit_with_goal(self, mock_trigger_audit):
        mock_trigger_audit.return_value = mock.ANY

        audit_dict = post_get_test_audit(
            params_to_exclude=['uuid', 'state', 'interval', 'scope',
                               'next_run_time', 'hostname',
                               'audit_template_uuid'])

        response = self.post_json('/audits', audit_dict)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(201, response.status_int)
        self.assertEqual(objects.audit.State.PENDING,
                         response.json['state'])
        self.assertTrue(utils.is_uuid_like(response.json['uuid']))

    @mock.patch.object(deapi.DecisionEngineAPI, 'trigger_audit')
    def test_create_audit_with_goal_without_strategy(self, mock_trigger_audit):
        mock_trigger_audit.return_value = mock.ANY

        audit_dict = post_get_test_audit(
            params_to_exclude=['uuid', 'state', 'interval', 'scope',
                               'next_run_time', 'hostname',
                               'audit_template_uuid', 'strategy'])

        response = self.post_json('/audits', audit_dict)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(201, response.status_int)
        self.assertEqual(objects.audit.State.PENDING,
                         response.json['state'])
        self.assertTrue(utils.is_uuid_like(response.json['uuid']))

    @mock.patch.object(deapi.DecisionEngineAPI, 'trigger_audit')
    def test_create_audit_with_named_goal(self, mock_trigger_audit):
        mock_trigger_audit.return_value = mock.ANY

        audit_dict = post_get_test_audit(
            params_to_exclude=['uuid', 'state', 'interval', 'scope',
                               'next_run_time', 'hostname',
                               'audit_template_uuid'],
            use_named_goal=True)

        response = self.post_json('/audits', audit_dict)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(201, response.status_int)
        self.assertEqual(objects.audit.State.PENDING,
                         response.json['state'])
        self.assertTrue(utils.is_uuid_like(response.json['uuid']))

    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_create_audit_invalid_audit_template_uuid(self, mock_utcnow):
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time

        audit_dict = post_get_test_audit(
            params_to_exclude=['uuid', 'state', 'interval', 'scope',
                               'next_run_time', 'hostname', 'goal'])
        # Make the audit template UUID some garbage value
        audit_dict['audit_template_uuid'] = (
            '01234567-8910-1112-1314-151617181920')

        response = self.post_json('/audits', audit_dict, expect_errors=True)
        self.assertEqual(400, response.status_int)
        self.assertEqual("application/json", response.content_type)
        expected_error_msg = ('The audit template UUID or name specified is '
                              'invalid')
        self.assertTrue(response.json['error_message'])
        self.assertIn(expected_error_msg, response.json['error_message'])

    @mock.patch.object(deapi.DecisionEngineAPI, 'trigger_audit')
    def test_create_audit_doesnt_contain_id(self, mock_trigger_audit):
        mock_trigger_audit.return_value = mock.ANY

        audit_dict = post_get_test_audit(
            state=objects.audit.State.PENDING,
            params_to_exclude=['uuid', 'interval', 'scope',
                               'next_run_time', 'hostname', 'goal'])
        state = audit_dict['state']
        del audit_dict['state']
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

        audit_dict = post_get_test_audit(
            params_to_exclude=['uuid', 'state', 'interval', 'scope',
                               'next_run_time', 'hostname', 'goal'])

        response = self.post_json('/audits', audit_dict)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(201, response.status_int)
        self.assertEqual(objects.audit.State.PENDING,
                         response.json['state'])
        self.assertTrue(utils.is_uuid_like(response.json['uuid']))

    @mock.patch.object(deapi.DecisionEngineAPI, 'trigger_audit')
    def test_create_continuous_audit_with_interval(self, mock_trigger_audit):
        mock_trigger_audit.return_value = mock.ANY

        audit_dict = post_get_test_audit(
            params_to_exclude=['uuid', 'state', 'scope',
                               'next_run_time', 'hostname', 'goal'])
        audit_dict['audit_type'] = objects.audit.AuditType.CONTINUOUS.value
        audit_dict['interval'] = '1200'

        response = self.post_json('/audits', audit_dict)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(201, response.status_int)
        self.assertEqual(objects.audit.State.PENDING,
                         response.json['state'])
        self.assertEqual(audit_dict['interval'], response.json['interval'])
        self.assertTrue(utils.is_uuid_like(response.json['uuid']))

    @mock.patch.object(deapi.DecisionEngineAPI, 'trigger_audit')
    def test_create_continuous_audit_with_cron_interval(self,
                                                        mock_trigger_audit):
        mock_trigger_audit.return_value = mock.ANY

        audit_dict = post_get_test_audit(
            params_to_exclude=['uuid', 'state', 'scope',
                               'next_run_time', 'hostname', 'goal'])
        audit_dict['audit_type'] = objects.audit.AuditType.CONTINUOUS.value
        audit_dict['interval'] = '* * * * *'

        response = self.post_json('/audits', audit_dict)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(201, response.status_int)
        self.assertEqual(objects.audit.State.PENDING,
                         response.json['state'])
        self.assertEqual(audit_dict['interval'], response.json['interval'])
        self.assertTrue(utils.is_uuid_like(response.json['uuid']))

    @mock.patch.object(deapi.DecisionEngineAPI, 'trigger_audit')
    def test_create_continuous_audit_with_wrong_interval(self,
                                                         mock_trigger_audit):
        mock_trigger_audit.return_value = mock.ANY

        audit_dict = post_get_test_audit(
            params_to_exclude=['uuid', 'state', 'scope',
                               'next_run_time', 'hostname', 'goal'])
        audit_dict['audit_type'] = objects.audit.AuditType.CONTINUOUS.value
        audit_dict['interval'] = 'zxc'

        response = self.post_json('/audits', audit_dict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(500, response.status_int)
        expected_error_msg = ('Exactly 5 or 6 columns has to be '
                              'specified for iteratorexpression.')
        self.assertTrue(response.json['error_message'])
        self.assertIn(expected_error_msg, response.json['error_message'])

    @mock.patch.object(deapi.DecisionEngineAPI, 'trigger_audit')
    def test_create_continuous_audit_without_period(self, mock_trigger_audit):
        mock_trigger_audit.return_value = mock.ANY

        audit_dict = post_get_test_audit(
            params_to_exclude=['uuid', 'state', 'interval', 'scope',
                               'next_run_time', 'hostname', 'goal'])
        audit_dict['audit_type'] = objects.audit.AuditType.CONTINUOUS.value

        response = self.post_json('/audits', audit_dict, expect_errors=True)
        self.assertEqual(400, response.status_int)
        self.assertEqual('application/json', response.content_type)
        expected_error_msg = ('Interval of audit must be specified '
                              'for CONTINUOUS.')
        self.assertTrue(response.json['error_message'])
        self.assertIn(expected_error_msg, response.json['error_message'])

    @mock.patch.object(deapi.DecisionEngineAPI, 'trigger_audit')
    def test_create_oneshot_audit_with_period(self, mock_trigger_audit):
        mock_trigger_audit.return_value = mock.ANY

        audit_dict = post_get_test_audit(
            params_to_exclude=['uuid', 'state', 'scope',
                               'next_run_time', 'hostname', 'goal'])
        audit_dict['audit_type'] = objects.audit.AuditType.ONESHOT.value

        response = self.post_json('/audits', audit_dict, expect_errors=True)
        self.assertEqual(400, response.status_int)
        self.assertEqual('application/json', response.content_type)
        expected_error_msg = 'Interval of audit must not be set for ONESHOT.'
        self.assertTrue(response.json['error_message'])
        self.assertIn(expected_error_msg, response.json['error_message'])

    def test_create_audit_trigger_decision_engine(self):
        with mock.patch.object(deapi.DecisionEngineAPI,
                               'trigger_audit') as de_mock:
            audit_dict = post_get_test_audit(
                state=objects.audit.State.PENDING,
                params_to_exclude=['uuid', 'state', 'interval', 'scope',
                                   'next_run_time', 'hostname', 'goal'])
            response = self.post_json('/audits', audit_dict)
            de_mock.assert_called_once_with(mock.ANY, response.json['uuid'])

    @mock.patch.object(deapi.DecisionEngineAPI, 'trigger_audit')
    def test_create_audit_with_uuid(self, mock_trigger_audit):
        mock_trigger_audit.return_value = mock.ANY

        audit_dict = post_get_test_audit(state=objects.audit.State.PENDING)
        del audit_dict['scope']
        response = self.post_json('/audits', audit_dict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)
        assert not mock_trigger_audit.called

    @mock.patch.object(deapi.DecisionEngineAPI, 'trigger_audit')
    def test_create_audit_parameters_no_predefined_strategy(
            self, mock_trigger_audit):
        mock_trigger_audit.return_value = mock.ANY
        audit_dict = post_get_test_audit(
            parameters={'name': 'Tom'},
            params_to_exclude=['uuid', 'state', 'interval', 'scope',
                               'next_run_time', 'hostname', 'goal'])

        response = self.post_json('/audits', audit_dict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)
        expected_error_msg = ('Specify parameters but no predefined '
                              'strategy for audit, or no '
                              'parameter spec in predefined strategy')
        self.assertTrue(response.json['error_message'])
        self.assertIn(expected_error_msg, response.json['error_message'])
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
        del audit_dict['scope']
        del audit_dict['next_run_time']
        del audit_dict['hostname']

        response = self.post_json('/audits', audit_dict, expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)
        expected_error_msg = ('Specify parameters but no predefined '
                              'strategy for audit, or no '
                              'parameter spec in predefined strategy')
        self.assertTrue(response.json['error_message'])
        self.assertIn(expected_error_msg, response.json['error_message'])
        assert not mock_trigger_audit.called

    @mock.patch.object(deapi.DecisionEngineAPI, 'trigger_audit')
    def test_create_audit_with_parameter_not_allowed(
            self, mock_trigger_audit):
        mock_trigger_audit.return_value = mock.ANY
        audit_template = self.prepare_audit_template_strategy_with_parameter()

        audit_dict = api_utils.audit_post_data(
            parameters={'fake1': 1, 'fake2': "hello"})

        audit_dict['audit_template_uuid'] = audit_template['uuid']
        del_keys = ['uuid', 'goal_id', 'strategy_id', 'state', 'interval',
                    'scope', 'next_run_time', 'hostname']
        for k in del_keys:
            del audit_dict[k]

        response = self.post_json('/audits', audit_dict, expect_errors=True)
        self.assertEqual(400, response.status_int)
        self.assertEqual("application/json", response.content_type)
        expected_error_msg = 'Audit parameter fake2 are not allowed'
        self.assertTrue(response.json['error_message'])
        self.assertIn(expected_error_msg, response.json['error_message'])
        assert not mock_trigger_audit.called

    def prepare_audit_template_strategy_with_parameter(self):
        fake_spec = {
            "properties": {
                "fake1": {
                    "description": "number parameter example",
                    "type": "number",
                    "default": 3.2,
                    "minimum": 1.0,
                    "maximum": 10.2,
                }
            }
        }
        template_uuid = 'e74c40e0-d825-11e2-a28f-0800200c9a67'
        strategy_uuid = 'e74c40e0-d825-11e2-a28f-0800200c9a68'
        template_name = 'my template'
        strategy_name = 'my strategy'
        strategy_id = 3
        strategy = db_utils.get_test_strategy(parameters_spec=fake_spec,
                                              id=strategy_id,
                                              uuid=strategy_uuid,
                                              name=strategy_name)
        obj_utils.create_test_strategy(self.context,
                                       parameters_spec=fake_spec,
                                       id=strategy_id,
                                       uuid=strategy_uuid,
                                       name=strategy_name)
        obj_utils.create_test_audit_template(self.context,
                                             strategy_id=strategy_id,
                                             uuid=template_uuid,
                                             name='name')
        audit_template = db_utils.get_test_audit_template(
            strategy_id=strategy['id'], uuid=template_uuid, name=template_name)
        return audit_template

    @mock.patch.object(deapi.DecisionEngineAPI, 'trigger_audit')
    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_create_audit_with_name(self, mock_utcnow, mock_trigger_audit):
        mock_trigger_audit.return_value = mock.ANY
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time

        audit_dict = post_get_test_audit(
            params_to_exclude=['state', 'interval', 'scope',
                               'next_run_time', 'hostname', 'goal'])
        normal_name = 'this audit name is just for test'
        # long_name length exceeds 63 characters
        long_name = normal_name + audit_dict['uuid']
        del audit_dict['uuid']

        audit_dict['name'] = normal_name
        response = self.post_json('/audits', audit_dict)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(201, response.status_int)
        self.assertEqual(normal_name, response.json['name'])

        audit_dict['name'] = long_name
        response = self.post_json('/audits', audit_dict)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(201, response.status_int)
        self.assertNotEqual(long_name, response.json['name'])

    @mock.patch.object(deapi.DecisionEngineAPI, 'trigger_audit')
    def test_create_continuous_audit_with_start_end_time(
            self, mock_trigger_audit):
        mock_trigger_audit.return_value = mock.ANY
        start_time = datetime.datetime(2018, 3, 1, 0, 0)
        end_time = datetime.datetime(2018, 4, 1, 0, 0)

        audit_dict = post_get_test_audit(
            params_to_exclude=['uuid', 'state', 'scope',
                               'next_run_time', 'hostname', 'goal']
        )
        audit_dict['audit_type'] = objects.audit.AuditType.CONTINUOUS.value
        audit_dict['interval'] = '1200'
        audit_dict['start_time'] = str(start_time)
        audit_dict['end_time'] = str(end_time)

        response = self.post_json(
            '/audits',
            audit_dict,
            headers={'OpenStack-API-Version': 'infra-optim 1.1'})
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(201, response.status_int)
        self.assertEqual(objects.audit.State.PENDING,
                         response.json['state'])
        self.assertEqual(audit_dict['interval'], response.json['interval'])
        self.assertTrue(utils.is_uuid_like(response.json['uuid']))
        return_start_time = timeutils.parse_isotime(
            response.json['start_time'])
        return_end_time = timeutils.parse_isotime(
            response.json['end_time'])
        iso_start_time = start_time.replace(
            tzinfo=tz.tzlocal()).astimezone(tz.tzutc())
        iso_end_time = end_time.replace(
            tzinfo=tz.tzlocal()).astimezone(tz.tzutc())

        self.assertEqual(iso_start_time, return_start_time)
        self.assertEqual(iso_end_time, return_end_time)

    @mock.patch.object(deapi.DecisionEngineAPI, 'trigger_audit')
    def test_create_continuous_audit_with_start_end_time_incompatible_version(
            self, mock_trigger_audit):
        mock_trigger_audit.return_value = mock.ANY
        start_time = datetime.datetime(2018, 3, 1, 0, 0)
        end_time = datetime.datetime(2018, 4, 1, 0, 0)

        audit_dict = post_get_test_audit(
            params_to_exclude=['uuid', 'state', 'scope',
                               'next_run_time', 'hostname', 'goal']
        )
        audit_dict['audit_type'] = objects.audit.AuditType.CONTINUOUS.value
        audit_dict['interval'] = '1200'
        audit_dict['start_time'] = str(start_time)
        audit_dict['end_time'] = str(end_time)

        response = self.post_json(
            '/audits',
            audit_dict,
            headers={'OpenStack-API-Version': 'infra-optim 1.0'},
            expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(406, response.status_int)
        expected_error_msg = 'Request not acceptable.'
        self.assertTrue(response.json['error_message'])
        self.assertIn(expected_error_msg, response.json['error_message'])
        assert not mock_trigger_audit.called

    @mock.patch.object(deapi.DecisionEngineAPI, 'trigger_audit')
    def test_create_audit_with_force_false(self, mock_trigger_audit):
        mock_trigger_audit.return_value = mock.ANY

        audit_dict = post_get_test_audit(
            params_to_exclude=['uuid', 'state', 'interval', 'scope',
                               'next_run_time', 'hostname', 'goal'])

        response = self.post_json(
            '/audits',
            audit_dict,
            headers={'OpenStack-API-Version': 'infra-optim 1.2'})
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(201, response.status_int)
        self.assertFalse(response.json['force'])

    @mock.patch.object(deapi.DecisionEngineAPI, 'trigger_audit')
    def test_create_audit_with_force_true(self, mock_trigger_audit):
        mock_trigger_audit.return_value = mock.ANY

        audit_dict = post_get_test_audit(
            params_to_exclude=['uuid', 'state', 'interval', 'scope',
                               'next_run_time', 'hostname', 'goal'])

        audit_dict['force'] = True
        response = self.post_json(
            '/audits',
            audit_dict,
            headers={'OpenStack-API-Version': 'infra-optim 1.2'})
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(201, response.status_int)
        self.assertTrue(response.json['force'])


class TestDelete(api_base.FunctionalTest):

    def setUp(self):
        super(TestDelete, self).setUp()
        obj_utils.create_test_goal(self.context)
        obj_utils.create_test_strategy(self.context)
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

        new_state = objects.audit.State.ONGOING
        self.patch_json(
            '/audits/%s' % self.audit.uuid,
            [{'path': '/state', 'value': new_state,
             'op': 'replace'}])
        response = self.delete('/audits/%s' % self.audit.uuid,
                               expect_errors=True)
        self.assertEqual(400, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

        new_state = objects.audit.State.CANCELLED
        self.patch_json(
            '/audits/%s' % self.audit.uuid,
            [{'path': '/state', 'value': new_state,
             'op': 'replace'}])
        self.delete('/audits/%s' % self.audit.uuid)
        response = self.get_json('/audits/%s' % self.audit.uuid,
                                 expect_errors=True)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

        self.context.show_deleted = True
        audit = objects.Audit.get_by_uuid(self.context, self.audit.uuid)

        return_deleted_at = \
            audit['deleted_at'].strftime('%Y-%m-%dT%H:%M:%S.%f')
        self.assertEqual(test_time.strftime('%Y-%m-%dT%H:%M:%S.%f'),
                         return_deleted_at)
        self.assertEqual(objects.audit.State.DELETED, audit['state'])

    def test_delete_audit_not_found(self):
        uuid = utils.generate_uuid()
        response = self.delete('/audits/%s' % uuid, expect_errors=True)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])


class TestAuditPolicyEnforcement(api_base.FunctionalTest):

    def setUp(self):
        super(TestAuditPolicyEnforcement, self).setUp()
        obj_utils.create_test_goal(self.context)

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
            jsonutils.loads(response.json['error_message'])['faultstring'])

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
            [{'path': '/state', 'value': objects.audit.State.SUCCEEDED,
             'op': 'replace'}], expect_errors=True)

    def test_policy_disallow_create(self):
        audit_dict = post_get_test_audit(
            state=objects.audit.State.PENDING,
            params_to_exclude=['uuid', 'state', 'scope',
                               'next_run_time', 'hostname', 'goal'])
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
