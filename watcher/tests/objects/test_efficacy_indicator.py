# Copyright 2015 OpenStack Foundation
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
from watcher.common import exception
# from watcher.common import utils as w_utils
from watcher import objects
from watcher.tests.db import base
from watcher.tests.db import utils


class TestEfficacyIndicatorObject(base.DbTestCase):

    def setUp(self):
        super(TestEfficacyIndicatorObject, self).setUp()
        self.fake_efficacy_indicator = utils.get_test_efficacy_indicator()

    def test_get_by_id(self):
        efficacy_indicator_id = self.fake_efficacy_indicator['id']
        with mock.patch.object(self.dbapi, 'get_efficacy_indicator_by_id',
                               autospec=True) as mock_get_efficacy_indicator:
            mock_get_efficacy_indicator.return_value = (
                self.fake_efficacy_indicator)
            efficacy_indicator = objects.EfficacyIndicator.get(
                self.context, efficacy_indicator_id)
            mock_get_efficacy_indicator.assert_called_once_with(
                self.context, efficacy_indicator_id)
            self.assertEqual(self.context, efficacy_indicator._context)

    def test_get_by_uuid(self):
        uuid = self.fake_efficacy_indicator['uuid']
        with mock.patch.object(self.dbapi, 'get_efficacy_indicator_by_uuid',
                               autospec=True) as mock_get_efficacy_indicator:
            mock_get_efficacy_indicator.return_value = (
                self.fake_efficacy_indicator)
            efficacy_indicator = objects.EfficacyIndicator.get(
                self.context, uuid)
            mock_get_efficacy_indicator.assert_called_once_with(
                self.context, uuid)
            self.assertEqual(self.context, efficacy_indicator._context)

    def test_get_bad_id_and_uuid(self):
        self.assertRaises(
            exception.InvalidIdentity,
            objects.EfficacyIndicator.get, self.context, 'not-a-uuid')

    def test_list(self):
        with mock.patch.object(self.dbapi, 'get_efficacy_indicator_list',
                               autospec=True) as mock_get_list:
            mock_get_list.return_value = [self.fake_efficacy_indicator]
            efficacy_indicators = objects.EfficacyIndicator.list(self.context)
            self.assertEqual(1, mock_get_list.call_count)
            self.assertEqual(1, len(efficacy_indicators))
            self.assertIsInstance(
                efficacy_indicators[0], objects.EfficacyIndicator)
            self.assertEqual(self.context, efficacy_indicators[0]._context)

    def test_create(self):
        with mock.patch.object(
            self.dbapi, 'create_efficacy_indicator',
            autospec=True
        ) as mock_create_efficacy_indicator:
            mock_create_efficacy_indicator.return_value = (
                self.fake_efficacy_indicator)
            efficacy_indicator = objects.EfficacyIndicator(
                self.context, **self.fake_efficacy_indicator)

            efficacy_indicator.create()
            mock_create_efficacy_indicator.assert_called_once_with(
                self.fake_efficacy_indicator)
            self.assertEqual(self.context, efficacy_indicator._context)

    def test_destroy(self):
        uuid = self.fake_efficacy_indicator['uuid']
        with mock.patch.object(
            self.dbapi, 'get_efficacy_indicator_by_uuid',
            autospec=True
        ) as mock_get_efficacy_indicator:
            mock_get_efficacy_indicator.return_value = (
                self.fake_efficacy_indicator)
            with mock.patch.object(
                self.dbapi, 'destroy_efficacy_indicator',
                autospec=True
            ) as mock_destroy_efficacy_indicator:
                efficacy_indicator = objects.EfficacyIndicator.get_by_uuid(
                    self.context, uuid)
                efficacy_indicator.destroy()
                mock_get_efficacy_indicator.assert_called_once_with(
                    self.context, uuid)
                mock_destroy_efficacy_indicator.assert_called_once_with(uuid)
                self.assertEqual(self.context, efficacy_indicator._context)

    def test_save(self):
        uuid = self.fake_efficacy_indicator['uuid']
        with mock.patch.object(
            self.dbapi, 'get_efficacy_indicator_by_uuid',
            autospec=True
        ) as mock_get_efficacy_indicator:
            mock_get_efficacy_indicator.return_value = (
                self.fake_efficacy_indicator)
            with mock.patch.object(
                self.dbapi, 'update_efficacy_indicator',
                autospec=True
            ) as mock_update_efficacy_indicator:
                efficacy_indicator = objects.EfficacyIndicator.get_by_uuid(
                    self.context, uuid)
                efficacy_indicator.description = 'Indicator Description'
                efficacy_indicator.save()

                mock_get_efficacy_indicator.assert_called_once_with(
                    self.context, uuid)
                mock_update_efficacy_indicator.assert_called_once_with(
                    uuid, {'description': 'Indicator Description'})
                self.assertEqual(self.context, efficacy_indicator._context)

    def test_refresh(self):
        uuid = self.fake_efficacy_indicator['uuid']
        returns = [dict(self.fake_efficacy_indicator,
                        description="first description"),
                   dict(self.fake_efficacy_indicator,
                        description="second description")]
        expected = [mock.call(self.context, uuid),
                    mock.call(self.context, uuid)]
        with mock.patch.object(self.dbapi, 'get_efficacy_indicator_by_uuid',
                               side_effect=returns,
                               autospec=True) as mock_get_efficacy_indicator:
            efficacy_indicator = objects.EfficacyIndicator.get(
                self.context, uuid)
            self.assertEqual(
                "first description", efficacy_indicator.description)
            efficacy_indicator.refresh()
            self.assertEqual(
                "second description", efficacy_indicator.description)
            self.assertEqual(
                expected, mock_get_efficacy_indicator.call_args_list)
            self.assertEqual(self.context, efficacy_indicator._context)
