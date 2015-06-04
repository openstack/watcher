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
from six.moves.urllib import parse as urlparse
from wsme import types as wtypes

from watcher.api.controllers.v1 import audit_template as api_audit_template
from watcher.common import utils
from watcher.db import api as db_api
from watcher import objects
from watcher.tests.api import base as api_base
from watcher.tests.api import utils as api_utils
from watcher.tests import base
from watcher.tests.objects import utils as obj_utils


class TestAuditTemplateObject(base.TestCase):

    def test_audit_template_init(self):
        audit_template_dict = api_utils.audit_template_post_data()
        del audit_template_dict['name']
        audit_template = api_audit_template.AuditTemplate(
            **audit_template_dict)
        self.assertEqual(wtypes.Unset, audit_template.name)


class TestListAuditTemplate(api_base.FunctionalTest):

    def test_empty(self):
        response = self.get_json('/audit_templates')
        self.assertEqual([], response['audit_templates'])

    def _assert_audit_template_fields(self, audit_template):
        audit_template_fields = ['name', 'goal', 'host_aggregate']
        for field in audit_template_fields:
            self.assertIn(field, audit_template)

    def test_one(self):
        audit_template = obj_utils.create_test_audit_template(self.context)
        response = self.get_json('/audit_templates')
        self.assertEqual(audit_template.uuid,
                         response['audit_templates'][0]["uuid"])
        self._assert_audit_template_fields(response['audit_templates'][0])

    def test_one_soft_deleted(self):
        audit_template = obj_utils.create_test_audit_template(self.context)
        audit_template.soft_delete()
        response = self.get_json('/audit_templates',
                                 headers={'X-Show-Deleted': 'True'})
        self.assertEqual(audit_template.uuid,
                         response['audit_templates'][0]["uuid"])
        self._assert_audit_template_fields(response['audit_templates'][0])

        response = self.get_json('/audit_templates')
        self.assertEqual([], response['audit_templates'])

    def test_get_one_by_uuid(self):
        audit_template = obj_utils.create_test_audit_template(self.context)
        response = self.get_json(
            '/audit_templates/%s' % audit_template['uuid'])
        self.assertEqual(audit_template.uuid, response['uuid'])
        self._assert_audit_template_fields(response)

    def test_get_one_by_name(self):
        audit_template = obj_utils.create_test_audit_template(self.context)
        response = self.get_json(urlparse.quote(
            '/audit_templates/%s' % audit_template['name']))
        self.assertEqual(audit_template.uuid, response['uuid'])
        self._assert_audit_template_fields(response)

    def test_get_one_soft_deleted(self):
        audit_template = obj_utils.create_test_audit_template(self.context)
        audit_template.soft_delete()
        response = self.get_json(
            '/audit_templates/%s' % audit_template['uuid'],
            headers={'X-Show-Deleted': 'True'})
        self.assertEqual(audit_template.uuid, response['uuid'])
        self._assert_audit_template_fields(response)

        response = self.get_json(
            '/audit_templates/%s' % audit_template['uuid'],
            expect_errors=True)
        self.assertEqual(404, response.status_int)

    def test_detail(self):
        audit_template = obj_utils.create_test_audit_template(self.context)
        response = self.get_json('/audit_templates/detail')
        self.assertEqual(audit_template.uuid,
                         response['audit_templates'][0]["uuid"])
        self._assert_audit_template_fields(response['audit_templates'][0])

    def test_detail_soft_deleted(self):
        audit_template = obj_utils.create_test_audit_template(self.context)
        audit_template.soft_delete()
        response = self.get_json('/audit_templates/detail',
                                 headers={'X-Show-Deleted': 'True'})
        self.assertEqual(audit_template.uuid,
                         response['audit_templates'][0]["uuid"])
        self._assert_audit_template_fields(response['audit_templates'][0])

        response = self.get_json('/audit_templates/detail')
        self.assertEqual([], response['audit_templates'])

    def test_detail_against_single(self):
        audit_template = obj_utils.create_test_audit_template(self.context)
        response = self.get_json(
            '/audit_templates/%s/detail' % audit_template['uuid'],
            expect_errors=True)
        self.assertEqual(404, response.status_int)

    def test_many(self):
        audit_template_list = []
        for id_ in range(5):
            audit_template = obj_utils.create_test_audit_template(
                self.context, id=id_,
                uuid=utils.generate_uuid(),
                name='My Audit Template ' + str(id_))
            audit_template_list.append(audit_template.uuid)
        response = self.get_json('/audit_templates')
        self.assertEqual(len(audit_template_list),
                         len(response['audit_templates']))
        uuids = [s['uuid'] for s in response['audit_templates']]
        self.assertEqual(sorted(audit_template_list), sorted(uuids))

    def test_many_without_soft_deleted(self):
        audit_template_list = []
        for id_ in [1, 2, 3]:
            audit_template = obj_utils.create_test_audit_template(
                self.context, id=id_, uuid=utils.generate_uuid(),
                name='My Audit Template ' + str(id_))
            audit_template_list.append(audit_template.uuid)
        for id_ in [4, 5]:
            audit_template = obj_utils.create_test_audit_template(
                self.context, id=id_, uuid=utils.generate_uuid(),
                name='My Audit Template ' + str(id_))
            audit_template.soft_delete()
        response = self.get_json('/audit_templates')
        self.assertEqual(3, len(response['audit_templates']))
        uuids = [s['uuid'] for s in response['audit_templates']]
        self.assertEqual(sorted(audit_template_list), sorted(uuids))

    def test_many_with_soft_deleted(self):
        audit_template_list = []
        for id_ in [1, 2, 3]:
            audit_template = obj_utils.create_test_audit_template(
                self.context, id=id_, uuid=utils.generate_uuid(),
                name='My Audit Template ' + str(id_))
            audit_template_list.append(audit_template.uuid)
        for id_ in [4, 5]:
            audit_template = obj_utils.create_test_audit_template(
                self.context, id=id_, uuid=utils.generate_uuid(),
                name='My Audit Template ' + str(id_))
            audit_template.soft_delete()
            audit_template_list.append(audit_template.uuid)
        response = self.get_json('/audit_templates',
                                 headers={'X-Show-Deleted': 'True'})
        self.assertEqual(5, len(response['audit_templates']))
        uuids = [s['uuid'] for s in response['audit_templates']]
        self.assertEqual(sorted(audit_template_list), sorted(uuids))

    def test_links(self):
        uuid = utils.generate_uuid()
        obj_utils.create_test_audit_template(self.context, id=1, uuid=uuid)
        response = self.get_json('/audit_templates/%s' % uuid)
        self.assertIn('links', response.keys())
        self.assertEqual(2, len(response['links']))
        self.assertIn(uuid, response['links'][0]['href'])
        for l in response['links']:
            bookmark = l['rel'] == 'bookmark'
            self.assertTrue(self.validate_link(l['href'], bookmark=bookmark))

    def test_collection_links(self):
        for id_ in range(5):
            obj_utils.create_test_audit_template(
                self.context, id=id_, uuid=utils.generate_uuid(),
                name='My Audit Template ' + str(id_))
        response = self.get_json('/audit_templates/?limit=3')
        self.assertEqual(3, len(response['audit_templates']))

        next_marker = response['audit_templates'][-1]['uuid']
        self.assertIn(next_marker, response['next'])

    def test_collection_links_default_limit(self):
        cfg.CONF.set_override('max_limit', 3, 'api')
        for id_ in range(5):
            obj_utils.create_test_audit_template(
                self.context, id=id_, uuid=utils.generate_uuid(),
                name='My Audit Template ' + str(id_))
        response = self.get_json('/audit_templates')
        self.assertEqual(3, len(response['audit_templates']))

        next_marker = response['audit_templates'][-1]['uuid']
        self.assertIn(next_marker, response['next'])


class TestPatch(api_base.FunctionalTest):

    def setUp(self):
        super(TestPatch, self).setUp()
        self.audit_template = obj_utils.create_test_audit_template(
            self.context)
        p = mock.patch.object(db_api.Connection, 'update_audit_template')
        self.mock_audit_template_update = p.start()
        self.mock_audit_template_update.side_effect = \
            self._simulate_rpc_audit_template_update
        self.addCleanup(p.stop)

    def _simulate_rpc_audit_template_update(self, audit_template):
        audit_template.save()
        return audit_template

    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_replace_ok(self, mock_utcnow):
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time

        new_goal = 'BALANCE_LOAD'
        response = self.get_json(
            '/audit_templates/%s' % self.audit_template.uuid)
        self.assertNotEqual(new_goal, response['goal'])

        response = self.patch_json(
            '/audit_templates/%s' % self.audit_template.uuid,
            [{'path': '/goal', 'value': new_goal,
             'op': 'replace'}])
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(200, response.status_code)

        response = self.get_json(
            '/audit_templates/%s' % self.audit_template.uuid)
        self.assertEqual(new_goal, response['goal'])
        return_updated_at = timeutils.parse_isotime(
            response['updated_at']).replace(tzinfo=None)
        self.assertEqual(test_time, return_updated_at)

    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_replace_ok_by_name(self, mock_utcnow):
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time

        new_goal = 'BALANCE_LOAD'
        response = self.get_json(urlparse.quote(
            '/audit_templates/%s' % self.audit_template.name))
        self.assertNotEqual(new_goal, response['goal'])

        response = self.patch_json(
            '/audit_templates/%s' % self.audit_template.name,
            [{'path': '/goal', 'value': new_goal,
             'op': 'replace'}])
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(200, response.status_code)

        response = self.get_json(
            '/audit_templates/%s' % self.audit_template.name)
        self.assertEqual(new_goal, response['goal'])
        return_updated_at = timeutils.parse_isotime(
            response['updated_at']).replace(tzinfo=None)
        self.assertEqual(test_time, return_updated_at)

    def test_replace_non_existent_audit_template(self):
        response = self.patch_json(
            '/audit_templates/%s' % utils.generate_uuid(),
            [{'path': '/goal', 'value': 'BALANCE_LOAD',
             'op': 'replace'}],
            expect_errors=True)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    def test_add_ok(self):
        new_goal = 'BALANCE_LOAD'
        response = self.patch_json(
            '/audit_templates/%s' % self.audit_template.uuid,
            [{'path': '/goal', 'value': new_goal, 'op': 'add'}])
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(200, response.status_int)

        response = self.get_json(
            '/audit_templates/%s' % self.audit_template.uuid)
        self.assertEqual(new_goal, response['goal'])

    def test_add_non_existent_property(self):
        response = self.patch_json(
            '/audit_templates/%s' % self.audit_template.uuid,
            [{'path': '/foo', 'value': 'bar', 'op': 'add'}],
            expect_errors=True)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(400, response.status_int)
        self.assertTrue(response.json['error_message'])

    def test_remove_ok(self):
        response = self.get_json(
            '/audit_templates/%s' % self.audit_template.uuid)
        self.assertIsNotNone(response['goal'])

        response = self.patch_json(
            '/audit_templates/%s' % self.audit_template.uuid,
            [{'path': '/goal', 'op': 'remove'}])
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(200, response.status_code)

        response = self.get_json(
            '/audit_templates/%s' % self.audit_template.uuid)
        self.assertIsNone(response['goal'])

    def test_remove_uuid(self):
        response = self.patch_json(
            '/audit_templates/%s' % self.audit_template.uuid,
            [{'path': '/uuid', 'op': 'remove'}],
            expect_errors=True)
        self.assertEqual(400, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

    def test_remove_non_existent_property(self):
        response = self.patch_json(
            '/audit_templates/%s' % self.audit_template.uuid,
            [{'path': '/non-existent', 'op': 'remove'}],
            expect_errors=True)
        self.assertEqual(400, response.status_code)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])


class TestPost(api_base.FunctionalTest):

    def setUp(self):
        super(TestPost, self).setUp()
        p = mock.patch.object(db_api.Connection, 'create_audit_template')
        self.mock_create_audit_template = p.start()
        self.mock_create_audit_template.side_effect = (
            self._simulate_rpc_audit_template_create)
        self.addCleanup(p.stop)

    def _simulate_rpc_audit_template_create(self, audit_template):
        audit_template.create()
        return audit_template

    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_create_audit_template(self, mock_utcnow):
        audit_template_dict = api_utils.audit_template_post_data()
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time

        response = self.post_json('/audit_templates', audit_template_dict)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(201, response.status_int)
        # Check location header
        self.assertIsNotNone(response.location)
        expected_location = \
            '/v1/audit_templates/%s' % audit_template_dict['uuid']
        self.assertEqual(urlparse.urlparse(response.location).path,
                         expected_location)
        self.assertEqual(audit_template_dict['uuid'], response.json['uuid'])
        self.assertNotIn('updated_at', response.json.keys)
        self.assertNotIn('deleted_at', response.json.keys)
        return_created_at = timeutils.parse_isotime(
            response.json['created_at']).replace(tzinfo=None)
        self.assertEqual(test_time, return_created_at)

    def test_create_audit_template_doesnt_contain_id(self):
        with mock.patch.object(
            self.dbapi,
            'create_audit_template',
            wraps=self.dbapi.create_audit_template
        ) as cn_mock:
            audit_template_dict = api_utils.audit_template_post_data(
                goal='SERVERS_CONSOLIDATION')
            response = self.post_json('/audit_templates', audit_template_dict)
            self.assertEqual(audit_template_dict['goal'],
                             response.json['goal'])
            cn_mock.assert_called_once_with(mock.ANY)
            # Check that 'id' is not in first arg of positional args
            self.assertNotIn('id', cn_mock.call_args[0][0])

    def test_create_audit_template_generate_uuid(self):
        audit_template_dict = api_utils.audit_template_post_data()
        del audit_template_dict['uuid']

        response = self.post_json('/audit_templates', audit_template_dict)
        self.assertEqual('application/json', response.content_type)
        self.assertEqual(201, response.status_int)
        self.assertEqual(audit_template_dict['goal'], response.json['goal'])
        self.assertTrue(utils.is_uuid_like(response.json['uuid']))

    def test_create_audit_template_with_invalid_goal(self):
        with mock.patch.object(
            self.dbapi,
            'create_audit_template',
            wraps=self.dbapi.create_audit_template
        ) as cn_mock:
            audit_template_dict = api_utils.audit_template_post_data(
                goal='INVALID_GOAL')
            response = self.post_json('/audit_templates',
                                      audit_template_dict, expect_errors=True)
        self.assertEqual(400, response.status_int)
        assert not cn_mock.called


class TestDelete(api_base.FunctionalTest):

    def setUp(self):
        super(TestDelete, self).setUp()
        self.audit_template = obj_utils.create_test_audit_template(
            self.context)
        p = mock.patch.object(db_api.Connection, 'update_audit_template')
        self.mock_audit_template_update = p.start()
        self.mock_audit_template_update.side_effect = \
            self._simulate_rpc_audit_template_update
        self.addCleanup(p.stop)

    def _simulate_rpc_audit_template_update(self, audit_template):
        audit_template.save()
        return audit_template

    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_delete_audit_template_by_uuid(self, mock_utcnow):
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time
        self.delete('/audit_templates/%s' % self.audit_template.uuid)
        response = self.get_json(
            '/audit_templates/%s' % self.audit_template.uuid,
            expect_errors=True)
        # self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

        self.context.show_deleted = True
        audit_template = objects.AuditTemplate.get_by_uuid(
            self.context, self.audit_template.uuid)

        return_deleted_at = timeutils.strtime(audit_template['deleted_at'])
        self.assertEqual(timeutils.strtime(test_time), return_deleted_at)

    @mock.patch('oslo_utils.timeutils.utcnow')
    def test_delete_audit_template_by_name(self, mock_utcnow):
        test_time = datetime.datetime(2000, 1, 1, 0, 0)
        mock_utcnow.return_value = test_time
        self.delete(urlparse.quote('/audit_templates/%s' %
                                   self.audit_template.name))
        response = self.get_json(urlparse.quote(
            '/audit_templates/%s' % self.audit_template.name),
            expect_errors=True)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])

        self.context.show_deleted = True
        audit_template = objects.AuditTemplate.get_by_name(
            self.context, self.audit_template.name)

        return_deleted_at = timeutils.strtime(audit_template['deleted_at'])
        self.assertEqual(timeutils.strtime(test_time), return_deleted_at)

    def test_delete_audit_template_not_found(self):
        uuid = utils.generate_uuid()
        response = self.delete(
            '/audit_templates/%s' % uuid, expect_errors=True)
        self.assertEqual(404, response.status_int)
        self.assertEqual('application/json', response.content_type)
        self.assertTrue(response.json['error_message'])
