# -*- encoding: utf-8 -*-
# Copyright 2017 ZTE
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

import datetime
from unittest import mock

import iso8601

from watcher.db.sqlalchemy import api as db_api
from watcher import objects
from watcher.tests.db import base
from watcher.tests.db import utils


class TestActionDescriptionObject(base.DbTestCase):

    def setUp(self):
        super(TestActionDescriptionObject, self).setUp()
        self.fake_action_desc = utils.get_test_action_desc(
            created_at=datetime.datetime.utcnow())

    @mock.patch.object(db_api.Connection, 'get_action_description_by_id')
    def test_get_by_id(self, mock_get_action_desc):
        action_desc_id = self.fake_action_desc['id']
        mock_get_action_desc.return_value = self.fake_action_desc
        action_desc = objects.ActionDescription.get(
            self.context, action_desc_id)
        mock_get_action_desc.assert_called_once_with(
            self.context, action_desc_id)
        self.assertEqual(self.context, action_desc._context)

    @mock.patch.object(db_api.Connection, 'get_action_description_list')
    def test_list(self, mock_get_list):
        mock_get_list.return_value = [self.fake_action_desc]
        action_desc = objects.ActionDescription.list(self.context)
        self.assertEqual(1, mock_get_list.call_count)
        self.assertEqual(1, len(action_desc))
        self.assertIsInstance(action_desc[0], objects.ActionDescription)
        self.assertEqual(self.context, action_desc[0]._context)

    @mock.patch.object(db_api.Connection, 'create_action_description')
    def test_create(self, mock_create_action_desc):
        mock_create_action_desc.return_value = self.fake_action_desc
        action_desc = objects.ActionDescription(
            self.context, **self.fake_action_desc)

        action_desc.create()
        expected_action_desc = self.fake_action_desc.copy()
        expected_action_desc['created_at'] = expected_action_desc[
            'created_at'].replace(tzinfo=iso8601.UTC)

        mock_create_action_desc.assert_called_once_with(expected_action_desc)
        self.assertEqual(self.context, action_desc._context)

    @mock.patch.object(db_api.Connection, 'update_action_description')
    @mock.patch.object(db_api.Connection, 'get_action_description_by_id')
    def test_save(self, mock_get_action_desc, mock_update_action_desc):
        mock_get_action_desc.return_value = self.fake_action_desc
        fake_saved_action_desc = self.fake_action_desc.copy()
        fake_saved_action_desc['updated_at'] = datetime.datetime.utcnow()
        mock_update_action_desc.return_value = fake_saved_action_desc
        _id = self.fake_action_desc['id']
        action_desc = objects.ActionDescription.get(self.context, _id)
        action_desc.description = 'This is a test'
        action_desc.save()

        mock_get_action_desc.assert_called_once_with(self.context, _id)
        mock_update_action_desc.assert_called_once_with(
            _id, {'description': 'This is a test'})
        self.assertEqual(self.context, action_desc._context)

    @mock.patch.object(db_api.Connection, 'get_action_description_by_id')
    def test_refresh(self, mock_get_action_desc):
        returns = [dict(self.fake_action_desc, description="Test message1"),
                   dict(self.fake_action_desc, description="Test message2")]
        mock_get_action_desc.side_effect = returns
        _id = self.fake_action_desc['id']
        expected = [mock.call(self.context, _id),
                    mock.call(self.context, _id)]
        action_desc = objects.ActionDescription.get(self.context, _id)
        self.assertEqual("Test message1", action_desc.description)
        action_desc.refresh()
        self.assertEqual("Test message2", action_desc.description)
        self.assertEqual(expected, mock_get_action_desc.call_args_list)
        self.assertEqual(self.context, action_desc._context)

    @mock.patch.object(db_api.Connection, 'soft_delete_action_description')
    @mock.patch.object(db_api.Connection, 'get_action_description_by_id')
    def test_soft_delete(self, mock_get_action_desc, mock_soft_delete):
        mock_get_action_desc.return_value = self.fake_action_desc
        fake_deleted_action_desc = self.fake_action_desc.copy()
        fake_deleted_action_desc['deleted_at'] = datetime.datetime.utcnow()
        mock_soft_delete.return_value = fake_deleted_action_desc

        expected_action_desc = fake_deleted_action_desc.copy()
        expected_action_desc['created_at'] = expected_action_desc[
            'created_at'].replace(tzinfo=iso8601.UTC)
        expected_action_desc['deleted_at'] = expected_action_desc[
            'deleted_at'].replace(tzinfo=iso8601.UTC)

        _id = self.fake_action_desc['id']
        action_desc = objects.ActionDescription.get(self.context, _id)
        action_desc.soft_delete()
        mock_get_action_desc.assert_called_once_with(self.context, _id)
        mock_soft_delete.assert_called_once_with(_id)
        self.assertEqual(self.context, action_desc._context)
        self.assertEqual(expected_action_desc, action_desc.as_dict())
