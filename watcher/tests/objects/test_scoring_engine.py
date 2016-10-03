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

import mock
from watcher import objects
from watcher.tests.db import base
from watcher.tests.db import utils


class TestScoringEngineObject(base.DbTestCase):

    def setUp(self):
        super(TestScoringEngineObject, self).setUp()
        self.fake_scoring_engine = utils.get_test_scoring_engine()

    def test_get_by_id(self):
        scoring_engine_id = self.fake_scoring_engine['id']
        with mock.patch.object(self.dbapi, 'get_scoring_engine_by_id',
                               autospec=True) as mock_get_scoring_engine:
            mock_get_scoring_engine.return_value = self.fake_scoring_engine
            scoring_engine = objects.ScoringEngine.get_by_id(
                self.context, scoring_engine_id)
            mock_get_scoring_engine.assert_called_once_with(self.context,
                                                            scoring_engine_id)
            self.assertEqual(self.context, scoring_engine._context)

    def test_get_by_uuid(self):
        se_uuid = self.fake_scoring_engine['uuid']
        with mock.patch.object(self.dbapi, 'get_scoring_engine_by_uuid',
                               autospec=True) as mock_get_scoring_engine:
            mock_get_scoring_engine.return_value = self.fake_scoring_engine
            scoring_engine = objects.ScoringEngine.get_by_uuid(
                self.context, se_uuid)
            mock_get_scoring_engine.assert_called_once_with(self.context,
                                                            se_uuid)
            self.assertEqual(self.context, scoring_engine._context)

    def test_get_by_name(self):
        scoring_engine_uuid = self.fake_scoring_engine['uuid']
        with mock.patch.object(self.dbapi, 'get_scoring_engine_by_uuid',
                               autospec=True) as mock_get_scoring_engine:
            mock_get_scoring_engine.return_value = self.fake_scoring_engine
            scoring_engine = objects.ScoringEngine.get(
                self.context, scoring_engine_uuid)
            mock_get_scoring_engine.assert_called_once_with(
                self.context, scoring_engine_uuid)
            self.assertEqual(self.context, scoring_engine._context)

    def test_list(self):
        with mock.patch.object(self.dbapi, 'get_scoring_engine_list',
                               autospec=True) as mock_get_list:
            mock_get_list.return_value = [self.fake_scoring_engine]
            scoring_engines = objects.ScoringEngine.list(self.context)
            self.assertEqual(1, mock_get_list.call_count, 1)
            self.assertEqual(1, len(scoring_engines))
            self.assertIsInstance(scoring_engines[0], objects.ScoringEngine)
            self.assertEqual(self.context, scoring_engines[0]._context)

    def test_create(self):
        with mock.patch.object(self.dbapi, 'create_scoring_engine',
                               autospec=True) as mock_create_scoring_engine:
            mock_create_scoring_engine.return_value = self.fake_scoring_engine
            scoring_engine = objects.ScoringEngine(
                self.context, **self.fake_scoring_engine)

            scoring_engine.create()
            mock_create_scoring_engine.assert_called_once_with(
                self.fake_scoring_engine)
            self.assertEqual(self.context, scoring_engine._context)

    def test_destroy(self):
        _id = self.fake_scoring_engine['id']
        with mock.patch.object(self.dbapi, 'get_scoring_engine_by_id',
                               autospec=True) as mock_get_scoring_engine:
            mock_get_scoring_engine.return_value = self.fake_scoring_engine
            with mock.patch.object(
                    self.dbapi, 'destroy_scoring_engine',
                    autospec=True) as mock_destroy_scoring_engine:
                scoring_engine = objects.ScoringEngine.get_by_id(
                    self.context, _id)
                scoring_engine.destroy()
                mock_get_scoring_engine.assert_called_once_with(
                    self.context, _id)
                mock_destroy_scoring_engine.assert_called_once_with(_id)
                self.assertEqual(self.context, scoring_engine._context)

    def test_save(self):
        _id = self.fake_scoring_engine['id']
        with mock.patch.object(self.dbapi, 'get_scoring_engine_by_id',
                               autospec=True) as mock_get_scoring_engine:
            mock_get_scoring_engine.return_value = self.fake_scoring_engine
            with mock.patch.object(
                    self.dbapi, 'update_scoring_engine',
                    autospec=True) as mock_update_scoring_engine:
                scoring_engine = objects.ScoringEngine.get_by_id(
                    self.context, _id)
                scoring_engine.description = 'UPDATED DESCRIPTION'
                scoring_engine.save()

                mock_get_scoring_engine.assert_called_once_with(
                    self.context, _id)
                mock_update_scoring_engine.assert_called_once_with(
                    _id, {'description': 'UPDATED DESCRIPTION'})
                self.assertEqual(self.context, scoring_engine._context)

    def test_refresh(self):
        _id = self.fake_scoring_engine['id']
        returns = [
            dict(self.fake_scoring_engine, description="first description"),
            dict(self.fake_scoring_engine, description="second description")]
        expected = [mock.call(self.context, _id),
                    mock.call(self.context, _id)]
        with mock.patch.object(self.dbapi, 'get_scoring_engine_by_id',
                               side_effect=returns,
                               autospec=True) as mock_get_scoring_engine:
            scoring_engine = objects.ScoringEngine.get_by_id(self.context, _id)
            self.assertEqual("first description", scoring_engine.description)
            scoring_engine.refresh()
            self.assertEqual("second description", scoring_engine.description)
            self.assertEqual(expected, mock_get_scoring_engine.call_args_list)
            self.assertEqual(self.context, scoring_engine._context)

    def test_soft_delete(self):
        _id = self.fake_scoring_engine['id']
        with mock.patch.object(self.dbapi, 'get_scoring_engine_by_id',
                               autospec=True) as mock_get_scoring_engine:
            mock_get_scoring_engine.return_value = self.fake_scoring_engine
            with mock.patch.object(self.dbapi, 'soft_delete_scoring_engine',
                                   autospec=True) as mock_soft_delete:
                scoring_engine = objects.ScoringEngine.get_by_id(
                    self.context, _id)
                scoring_engine.soft_delete()
                mock_get_scoring_engine.assert_called_once_with(
                    self.context, _id)
                mock_soft_delete.assert_called_once_with(_id)
                self.assertEqual(self.context, scoring_engine._context)
