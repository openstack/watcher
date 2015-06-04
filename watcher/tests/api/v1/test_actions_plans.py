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

from watcher.api.controllers.v1 import action_plan as api_action_plan
from watcher.applier.framework import rpcapi as aapi
from watcher.common import utils
from watcher.db import api as db_api
from watcher import objects
from watcher.tests.api import base as api_base
from watcher.tests.api import utils as api_utils
from watcher.tests import base
from watcher.tests.objects import utils as obj_utils


class TestActionPlanObject(base.TestCase):

    def test_actionPlan_init(self):
        act_plan_dict = api_utils.action_plan_post_data()
        del act_plan_dict['state']
        del act_plan_dict['audit_id']
        act_plan = api_action_plan.ActionPlan(**act_plan_dict)
        self.assertEqual(wtypes.Unset, act_plan.state)


class TestListActionPlan(api_base.FunctionalTest):

    def test_empty(self):
        response = self.get_json('/action_plans')
        self.assertEqual([], response['action_plans'])

    def _assert_action_plans_fields(self, action_plan):
        action_plan_fields = ['state']
        for field in action_plan_fields:
            self.assertIn(field, action_plan)

    def test_one(self):
        action_plan = obj_utils.create_action_plan_without_audit(self.context)
        response = self.get_json('/action_plans')
        self.assertEqual(action_plan.uuid,
                         response['action_plans'][0]["uuid"])
        self._assert_action_plans_fields(response['action_plans'][0])

    def test_one_soft_deleted(self):
        action_plan = obj_utils.create_action_plan_without_audit(self.context)
        action_plan.soft_delete()
        response = self.get_json('/action_plans',
                                 headers={'X-Show-Deleted': 'True'})
        self.assertEqual(action_plan.uuid,
                         response['action_plans'][0]["uuid"])
        self._assert_action_plans_fields(response['action_plans'][0])

        response = self.get_json('/action_plans')
        self.assertEqual([], response['action_plans'])

    def test_get_one(self):
        action_plan = obj_utils.create_action_plan_without_audit(self.context)
        response = self.get_json('/action_plans/%s' % action_plan['uuid'])
        self.assertEqual(action_plan.uuid, response['uuid'])
        self._assert_action_plans_fields(response)

    def test_get_one_soft_deleted(self):
        action_plan = obj_utils.create_action_plan_without_audit(self.context)
        action_plan.soft_delete()
        response = self.get_json('/action_plans/%s' % action_plan['uuid'],
                                 headers={'X-Show-Deleted': 'True'})
        self.assertEqual(action_plan.uuid, response['uuid'])
        self._assert_action_plans_fields(response)

        response = self.get_json('/action_plans/%s' % action_plan['uuid'],
                                 expect_errors=True)
        self.assertEqual(404, response.status_int)

    def test_detail(self):
        action_plan = obj_utils.create_test_action_plan(self.context,
                                                        audit_id=None)
        response = self.get_json('/action_plans/detail')
        self.assertEqual(action_plan.uuid,
                         response['action_plans'][0]["uuid"])
        self._assert_action_plans_fields(response['action_plans'][0])

    def test_detail_soft_deleted(self):
        action_plan = obj_utils.create_action_plan_without_audit(self.context)
        action_plan.soft_delete()
        response = self.get_json('/action_plans/detail',
                                 headers={'X-Show-Deleted': 'True'})
        self.assertEqual(action_plan.uuid,
                         response['action_plans'][0]["uuid"])
        self._assert_action_plans_fields(response['action_plans'][0])

        response = self.get_json('/action_plans/detail')
        self.assertEqual([], response['action_plans'])

    def test_detail_against_single(self):
        action_plan = obj_utils.create_test_action_plan(self.context)
        response = self.get_json(
            '/action_plan/%s/detail' % action_plan['uuid'],
            expect_errors=True)
        self.assertEqual(404, response.status_int)

    def test_many(self):
        action_plan_list = []
        for id_ in range(5):
            action_plan = obj_utils.create_action_plan_without_audit(
                self.context, id=id_, uuid=utils.generate_uuid())
            action_plan_list.append(action_plan.uuid)
        response = self.get_json('/action_plans')
        self.assertEqual(len(action_plan_list), len(response['action_plans']))
        uuids = [s['uuid'] for s in response['action_plans']]
        self.assertEqual(sorted(action_plan_list), sorted(uuids))

    def test_many_with_soft_deleted_audit_uuid(self):
        action_plan_list = []
        audit1 = obj_utils.create_test_audit(self.context,
                                             id=1,
                                             uuid=utils.generate_uuid())
        audit2 = obj_utils.create_test_audit(self.context,
                                             id=2,
                                             uuid=utils.generate_uuid())

        for id_ in range(0, 2):
            action_plan = obj_utils.create_test_action_plan(
                self.context, id=id_, uuid=utils.generate_uuid(),
                audit_id=audit1.id)
            action_plan_list.append(action_plan.uuid)

        for id_ in range(2, 4):
            action_plan = obj_utils.create_test_action_plan(
                self.context, id=id_, uuid=utils.generate_uuid(),
                audit_id=audit2.id)
            action_plan_list.append(action_plan.uuid)

        self.delete('/audits/%s' % audit1.uuid)

        response = self.get_json('/action_plans')

        self.assertEqual(len(action_plan_list), len(response['action_plans']))

        for id_ in range(0, 2):
            action_plan = response['action_plans'][id_]
            self.assertEqual(None, action_plan['audit_uuid'])

        for id_ in range(2, 4):
            action_plan = response['action_plans'][id_]
            self.assertEqual(audit2.uuid, action_plan['audit_uuid'])

    def test_many_with_audit_uuid(self):
        action_plan_list = []
        audit = obj_utils.create_test_audit(self.context,
                                            uuid=utils.generate_uuid())
        for id_ in range(5):
            action_plan = obj_utils.create_test_action_plan(
                self.context, id=id_, uuid=utils.generate_uuid(),
                audit_id=audit.id)
            action_plan_list.append(action_plan.uuid)
        response = self.get_json('/action_plans')
        self.assertEqual(len(action_plan_list), len(response['action_plans']))
        for action in response['action_plans']:
            self.assertEqual(audit.uuid, action['audit_uuid'])

    def test_many_with_audit_uuid_filter(self):
        action_plan_list1 = []
        audit1 = obj_utils.create_test_audit(self.context,
                                             uuid=utils.generate_uuid())
        for id_ in range(5):
            action_plan = obj_utils.create_test_action_plan(
                self.context, id=id_, uuid=utils.generate_uuid(),
                audit_id=audit1.id)
            action_plan_list1.append(action_plan.uuid)

        audit2 = obj_utils.create_test_audit(self.context,
                                             uuid=utils.generate_uuid())
        action_plan_list2 = []
        for id_ in [5, 6, 7]:
            action_plan = obj_utils.create_test_action_plan(
                self.context, id=id_, uuid=utils.generate_uuid(),
                audit_id=audit2.id)
            action_plan_list2.append(action_plan.uuid)

        response = self.get_json('/action_plans?audit_uuid=%s' % audit2.uuid)
        self.assertEqual(len(action_plan_list2), len(response['action_plans']))
        for action in response['action_plans']:
            self.assertEqual(audit2.uuid, action['audit_uuid'])

    def test_many_without_soft_deleted(self):
        action_plan_list = []
        for id_ in [1, 2, 3]:
            action_plan = obj_utils.create_action_plan_without_audit(
                self.context, id=id_, uuid=utils.generate_uuid())
            action_plan_list.append(action_plan.uuid)
        for id_ in [4, 5]:
            action_plan = obj_utils.create_test_action_plan(
                self.context, id=id_, uuid=utils.generate_uuid())
            action_plan.soft_delete()
        response = self.get_json('/action_plans')
        self.assertEqual(3, len(response['action_plans']))
        uuids = [s['uuid'] for s in response['action_plans']]
        self.assertEqual(sorted(action_plan_list), sorted(uuids))

    def test_many_with_soft_deleted(self):
        action_plan_list = []
        for id_ in [1, 2, 3]:
            action_plan = obj_utils.create_action_plan_without_audit(
                self.context, id=id_, uuid=utils.generate_uuid())
            action_plan_list.append(action_plan.uuid)
        for id_ in [4, 5]:
            action_plan = obj_utils.create_action_plan_without_audit(
                self.context, id=id_, uuid=utils.generate_uuid())
            action_plan.soft_delete()
            action_plan_list.append(action_plan.uuid)
        response = self.get_json('/action_plans',
                                 headers={'X-Show-Deleted': 'True'})
        self.assertEqual(5, len(response['action_plans']))
        uuids = [s['uuid'] for s in response['action_plans']]
        self.assertEqual(sorted(action_plan_list), sorted(uuids))

    def test_many_with_sort_key_audit_uuid(self):
        audit_list = []
        for id_ in range(5):
            audit = obj_utils.create_test_audit(self.context,
                                                uuid=utils.generate_uuid())
            obj_utils.create_test_action_plan(
                self.context, id=id_, uuid=utils.generate_uuid(),
                audit_id=audit.id)
            audit_list.append(audit.uuid)

        response = self.get_json('/action_plans/?sort_key=audit_uuid')

        self.assertEqual(5, len(response['action_plans']))
        uuids = [s['audit_uuid'] for s in response['action_plans']]
        self.assertEqual(sorted(audit_list), uuids)

    def test_links(self):
        uuid = utils.generate_uuid()
        obj_utils.create_action_plan_without_audit(self.context,
                                                   id=1, uuid=uuid)
        response = self.get_json('/action_plans/%s' % uuid)
        self.assertIn('links', response.keys())
        self.assertEqual(2, len(response['links']))
        self.assertIn(uuid, response['links'][0]['href'])
        for l in response['links']:
            bookmark = l['rel'] == 'bookmark'
            self.assertTrue(self.validate_link(l['href'], bookmark=bookmark))

    def test_collection_links(self):
        for id_ in range(5):
            obj_utils.create_action_plan_without_audit(
                self.context, id=id_, uuid=utils.generate_uuid())
        response = self.get_json('/action_plans/?limit=3')
        self.assertEqual(3, len(response['action_plans']))

        next_marker = response['action_plans'][-1]['uuid']
        self.assertIn(next_marker, response['next'])

    def test_collection_links_default_limit(self):
        cfg.CONF.set_override('max_limit', 3, 'api')
        for id_ in range(5):
            obj_utils.create_action_plan_without_audit(
                self.context, id=id_, uuid=utils.generate_uuid(),
                audit_id=None)
        response = self.get_json('/action_plans')
        self.assertEqual(3, len(response['action_plans']))

        next_marker = response['action_plans'][-1]['uuid']
        self.assertIn(next_marker, response['next'])


class TestDelete(api_base.FunctionalTest):

    def setUp(self):
        super(TestDelete, self).setUp()
        self.action_plan = obj_utils.create_action_plan_without_audit(
            self.context)
        p = mock.patch.object(db_api.Connection, 'destroy_action_plan')
        self.mock_action_plan_delete = p.start()
        self.mock_action_plan_delete.side_effect = \
            self._simulate_rpc_action_plan_delete
        self.addCleanup(p.stop)

    def _simulate_rpc_action_plan_delete(self, audit_uuid):
        action_plan = objects.ActionPlan.get_by_uuid(self.context, audit_uuid)
        action_plan.destroy()

    def test_delete_action_plan(self):
        self.delete('/action_plans/%s' % self.action_plan.uuid)
        response = self.get_json('/action_plans/%s' % self.action_plan.uuid,
                                 expect_errors=True)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    def test_delete_ction_plan_not_found(self):
        uuid = utils.generate_uuid()
        response = self.delete('/action_plans/%s' % uuid, expect_errors=True)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])


class TestPatch(api_base.FunctionalTest):

    def setUp(self):
        super(TestPatch, self).setUp()
        self.action_plan = obj_utils.create_action_plan_without_audit(
            self.context)
        p = mock.patch.object(db_api.Connection, 'update_action_plan')
        self.mock_action_plan_update = p.start()
        self.mock_action_plan_update.side_effect = \
            self._simulate_rpc_action_plan_update
        self.addCleanup(p.stop)

    def _simulate_rpc_action_plan_update(self, action_plan):
        action_plan.save()
        return action_plan

    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_replace_ok(self, mock_utcnow):
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time

        new_state = 'CANCELLED'
        response = self.get_json(
            '/action_plans/%s' % self.action_plan.uuid)
        self.assertNotEqual(new_state, response['state'])

        response = self.patch_json(
            '/action_plans/%s' % self.action_plan.uuid,
            [{'path': '/state', 'value': new_state,
             'op': 'replace'}])
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(200, response.status_code)

        response = self.get_json(
            '/action_plans/%s' % self.action_plan.uuid)
        self.assertEqual(new_state, response['state'])
        return_updated_at = timeutils.parse_isotime(
            response['updated_at']).replace(tzinfo=None)
        self.assertEqual(test_time, return_updated_at)

    def test_replace_non_existent_action_plan(self):
        response = self.patch_json(
            '/action_plans/%s' % utils.generate_uuid(),
            [{'path': '/state', 'value': 'CANCELLED',
             'op': 'replace'}],
            expect_errors=True)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    def test_add_ok(self):
        new_state = 'CANCELLED'
        response = self.patch_json(
            '/action_plans/%s' % self.action_plan.uuid,
            [{'path': '/state', 'value': new_state, 'op': 'add'}])
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(200, response.status_int)

        response = self.get_json(
            '/action_plans/%s' % self.action_plan.uuid)
        self.assertEqual(new_state, response['state'])

    def test_add_non_existent_property(self):
        response = self.patch_json(
            '/action_plans/%s' % self.action_plan.uuid,
            [{'path': '/foo', 'value': 'bar', 'op': 'add'}],
            expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)
        self.assertTrue(response.json['error_message'])

    def test_remove_ok(self):
        response = self.get_json(
            '/action_plans/%s' % self.action_plan.uuid)
        self.assertIsNotNone(response['state'])

        response = self.patch_json(
            '/action_plans/%s' % self.action_plan.uuid,
            [{'path': '/state', 'op': 'remove'}])
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(200, response.status_code)

        response = self.get_json(
            '/action_plans/%s' % self.action_plan.uuid)
        self.assertIsNone(response['state'])

    def test_remove_uuid(self):
        response = self.patch_json(
            '/action_plans/%s' % self.action_plan.uuid,
            [{'path': '/uuid', 'op': 'remove'}],
            expect_errors=True)
        self.assertEqual(400, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    def test_remove_non_existent_property(self):
        response = self.patch_json(
            '/action_plans/%s' % self.action_plan.uuid,
            [{'path': '/non-existent', 'op': 'remove'}],
            expect_errors=True)
        self.assertEqual(400, response.status_code)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    def test_replace_ok_state_starting(self):
        with mock.patch.object(aapi.ApplierAPI,
                               'launch_action_plan') as applier_mock:
            new_state = 'STARTING'
            response = self.get_json(
                '/action_plans/%s' % self.action_plan.uuid)
            self.assertNotEqual(new_state, response['state'])

            response = self.patch_json(
                '/action_plans/%s' % self.action_plan.uuid,
                [{'path': '/state', 'value': new_state,
                 'op': 'replace'}])
            self.assertEqual('application/json', response.content_type)
            self.assertEqual(200, response.status_code)
            applier_mock.assert_called_once_with(mock.ANY,
                                                 self.action_plan.uuid)
