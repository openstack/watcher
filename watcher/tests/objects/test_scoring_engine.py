# Copyright 2016 Intel
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


class TestScoringEngineObject(base.DbTestCase):

    def setUp(self):
        super(TestScoringEngineObject, self).setUp()
        self.fake_scoring_engine = utils.get_test_scoring_engine(
            created_at=datetime.datetime.utcnow())

    @mock.patch.object(db_api.Connection, 'get_scoring_engine_by_id')
    def test_get_by_id(self, mock_get_scoring_engine):
        scoring_engine_id = self.fake_scoring_engine['id']
        mock_get_scoring_engine.return_value = self.fake_scoring_engine
        scoring_engine = objects.ScoringEngine.get_by_id(
            self.context, scoring_engine_id)
        mock_get_scoring_engine.assert_called_once_with(
            self.context, scoring_engine_id)
        self.assertEqual(self.context, scoring_engine._context)

    @mock.patch.object(db_api.Connection, 'get_scoring_engine_by_uuid')
    def test_get_by_uuid(self, mock_get_scoring_engine):
        se_uuid = self.fake_scoring_engine['uuid']
        mock_get_scoring_engine.return_value = self.fake_scoring_engine
        scoring_engine = objects.ScoringEngine.get_by_uuid(
            self.context, se_uuid)
        mock_get_scoring_engine.assert_called_once_with(
            self.context, se_uuid)
        self.assertEqual(self.context, scoring_engine._context)

    @mock.patch.object(db_api.Connection, 'get_scoring_engine_by_uuid')
    def test_get_by_name(self, mock_get_scoring_engine):
        scoring_engine_uuid = self.fake_scoring_engine['uuid']
        mock_get_scoring_engine.return_value = self.fake_scoring_engine
        scoring_engine = objects.ScoringEngine.get(
            self.context, scoring_engine_uuid)
        mock_get_scoring_engine.assert_called_once_with(
            self.context, scoring_engine_uuid)
        self.assertEqual(self.context, scoring_engine._context)

    @mock.patch.object(db_api.Connection, 'get_scoring_engine_list')
    def test_list(self, mock_get_list):
        mock_get_list.return_value = [self.fake_scoring_engine]
        scoring_engines = objects.ScoringEngine.list(self.context)
        self.assertEqual(1, mock_get_list.call_count, 1)
        self.assertEqual(1, len(scoring_engines))
        self.assertIsInstance(scoring_engines[0], objects.ScoringEngine)
        self.assertEqual(self.context, scoring_engines[0]._context)

    @mock.patch.object(db_api.Connection, 'create_scoring_engine')
    def test_create(self, mock_create_scoring_engine):
        mock_create_scoring_engine.return_value = self.fake_scoring_engine
        scoring_engine = objects.ScoringEngine(
            self.context, **self.fake_scoring_engine)
        scoring_engine.create()
        expected_scoring_engine = self.fake_scoring_engine.copy()
        expected_scoring_engine['created_at'] = expected_scoring_engine[
            'created_at'].replace(tzinfo=iso8601.UTC)
        mock_create_scoring_engine.assert_called_once_with(
            expected_scoring_engine)
        self.assertEqual(self.context, scoring_engine._context)

    @mock.patch.object(db_api.Connection, 'destroy_scoring_engine')
    @mock.patch.object(db_api.Connection, 'get_scoring_engine_by_id')
    def test_destroy(self, mock_get_scoring_engine,
                     mock_destroy_scoring_engine):
        mock_get_scoring_engine.return_value = self.fake_scoring_engine
        _id = self.fake_scoring_engine['id']
        scoring_engine = objects.ScoringEngine.get_by_id(self.context, _id)
        scoring_engine.destroy()
        mock_get_scoring_engine.assert_called_once_with(self.context, _id)
        mock_destroy_scoring_engine.assert_called_once_with(_id)
        self.assertEqual(self.context, scoring_engine._context)

    @mock.patch.object(db_api.Connection, 'update_scoring_engine')
    @mock.patch.object(db_api.Connection, 'get_scoring_engine_by_uuid')
    def test_save(self, mock_get_scoring_engine, mock_update_scoring_engine):
        mock_get_scoring_engine.return_value = self.fake_scoring_engine
        fake_saved_scoring_engine = self.fake_scoring_engine.copy()
        fake_saved_scoring_engine['updated_at'] = datetime.datetime.utcnow()
        mock_update_scoring_engine.return_value = fake_saved_scoring_engine

        uuid = self.fake_scoring_engine['uuid']
        scoring_engine = objects.ScoringEngine.get_by_uuid(self.context, uuid)
        scoring_engine.description = 'UPDATED DESCRIPTION'
        scoring_engine.save()

        mock_get_scoring_engine.assert_called_once_with(self.context, uuid)
        mock_update_scoring_engine.assert_called_once_with(
            uuid, {'description': 'UPDATED DESCRIPTION'})
        self.assertEqual(self.context, scoring_engine._context)

    @mock.patch.object(db_api.Connection, 'get_scoring_engine_by_id')
    def test_refresh(self, mock_get_scoring_engine):
        returns = [
            dict(self.fake_scoring_engine, description="first description"),
            dict(self.fake_scoring_engine, description="second description")]
        mock_get_scoring_engine.side_effect = returns
        _id = self.fake_scoring_engine['id']
        expected = [mock.call(self.context, _id),
                    mock.call(self.context, _id)]
        scoring_engine = objects.ScoringEngine.get_by_id(self.context, _id)
        self.assertEqual("first description", scoring_engine.description)
        scoring_engine.refresh()
        self.assertEqual("second description", scoring_engine.description)
        self.assertEqual(expected, mock_get_scoring_engine.call_args_list)
        self.assertEqual(self.context, scoring_engine._context)

    @mock.patch.object(db_api.Connection, 'soft_delete_scoring_engine')
    @mock.patch.object(db_api.Connection, 'get_scoring_engine_by_id')
    def test_soft_delete(self, mock_get_scoring_engine, mock_soft_delete):
        mock_get_scoring_engine.return_value = self.fake_scoring_engine
        fake_deleted_scoring_engine = self.fake_scoring_engine.copy()
        fake_deleted_scoring_engine['deleted_at'] = datetime.datetime.utcnow()
        mock_soft_delete.return_value = fake_deleted_scoring_engine

        expected_scoring_engine = fake_deleted_scoring_engine.copy()
        expected_scoring_engine['created_at'] = expected_scoring_engine[
            'created_at'].replace(tzinfo=iso8601.UTC)
        expected_scoring_engine['deleted_at'] = expected_scoring_engine[
            'deleted_at'].replace(tzinfo=iso8601.UTC)

        _id = self.fake_scoring_engine['id']
        scoring_engine = objects.ScoringEngine.get_by_id(self.context, _id)
        scoring_engine.soft_delete()
        mock_get_scoring_engine.assert_called_once_with(self.context, _id)
        mock_soft_delete.assert_called_once_with(_id)
        self.assertEqual(self.context, scoring_engine._context)
        self.assertEqual(expected_scoring_engine, scoring_engine.as_dict())
