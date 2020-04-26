# -*- encoding: utf-8 -*-
# Copyright (c) 2019 European Organization for Nuclear Research (CERN)
#
# Authors: Corne Lukken <info@dantalion.nl>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from unittest import mock

from oslo_config import cfg
from oslo_log import log

from watcher.common import exception
from watcher.decision_engine.datasources.grafana_translator import \
    base as base_translator
from watcher.tests import base

CONF = cfg.CONF
LOG = log.getLogger(__name__)


class TestGrafanaTranslatorBase(base.BaseTestCase):
    """Base class for all GrafanaTranslator test classes

    Objects under test are preceded with t_ and mocked objects are preceded
    with m_ , additionally, patched objects are preceded with p_ no object
    under test should be created in setUp this can influence the results.
    """

    def setUp(self):
        super(TestGrafanaTranslatorBase, self).setUp()

        """Basic valid reference data"""
        self.reference_data = {
            'metric': 'host_cpu_usage',
            'db': 'production',
            'attribute': 'hostname',
            'query': 'SHOW all_base FROM belong_to_us',
            'resource': mock.Mock(hostname='hyperion'),
            'resource_type': 'compute_node',
            'period': '120',
            'aggregate': 'mean',
            'granularity': None
        }


class TestBaseGrafanaTranslator(TestGrafanaTranslatorBase):
    """Test the GrafanaTranslator base class

    Objects under test are preceded with t_ and mocked objects are preceded
    with m_ , additionally, patched objects are preceded with p_ no object
    under test should be created in setUp this can influence the results.
    """

    def setUp(self):
        super(TestBaseGrafanaTranslator, self).setUp()

    def test_validate_data(self):
        """Initialize InfluxDBGrafanaTranslator and check data validation"""

        t_base_translator = base_translator.BaseGrafanaTranslator(
            data=self.reference_data)

        self.assertIsInstance(t_base_translator,
                              base_translator.BaseGrafanaTranslator)

    def test_validate_data_error(self):
        """Initialize InfluxDBGrafanaTranslator and check data validation"""

        self.assertRaises(exception.InvalidParameter,
                          base_translator.BaseGrafanaTranslator,
                          data=[])

    def test_extract_attribute(self):
        """Test that an attribute can be extracted from an object"""

        m_object = mock.Mock(hostname='test')

        t_base_translator = base_translator.BaseGrafanaTranslator(
            data=self.reference_data)

        self.assertEqual('test', t_base_translator._extract_attribute(
            m_object, 'hostname'))

    def test_extract_attribute_error(self):
        """Test error on attempt to extract none existing attribute"""

        m_object = mock.Mock(hostname='test')
        m_object.test = mock.PropertyMock(side_effect=AttributeError)

        t_base_translator = base_translator.BaseGrafanaTranslator(
            data=self.reference_data)

        self.assertRaises(AttributeError, t_base_translator._extract_attribute(
            m_object, 'test'))
