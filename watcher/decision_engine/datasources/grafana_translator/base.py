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

import abc

from watcher._i18n import _
from watcher.common import exception
from watcher.decision_engine.datasources import base


class BaseGrafanaTranslator(object):
    """Grafana translator baseclass to use with grafana for different databases

    Specific databasses that are proxied through grafana require some
    alterations depending on the database.
    """

    """
    data {
        metric: name of the metric as found in DataSourceBase.METRIC_MAP,
        db: database specified for this metric in grafana_client config
            options,
        attribute: the piece of information that will be selected from the
                   resource object to build the query.
        query: the unformatted query from the configuration for this metric,
        resource: the object from the OpenStackClient
        resource_type: the type of the resource
                       ['compute_node','instance', 'bare_metal', 'storage'],
        period: the period of time to collect metrics for in seconds,
        aggregate: the aggregation can be any from ['mean', 'max', 'min',
                   'count'],
        granularity: interval between datapoints in seconds (optional),
    }
    """

    """Every grafana translator should have a uniquely identifying name"""
    NAME = ''

    RESOURCE_TYPES = base.DataSourceBase.RESOURCE_TYPES

    AGGREGATES = base.DataSourceBase.AGGREGATES

    def __init__(self, data):
        self._data = data
        self._validate_data()

    def _validate_data(self):
        """iterate through the supplied data and verify attributes"""

        optionals = ['granularity']

        reference_data = {
            'metric': None,
            'db': None,
            'attribute': None,
            'query': None,
            'resource': None,
            'resource_type': None,
            'period': None,
            'aggregate': None,
            'granularity': None
        }
        reference_data.update(self._data)

        for key, value in reference_data.items():
            if value is None and key not in optionals:
                raise exception.InvalidParameter(
                    message=(_("The value %(value)s for parameter "
                               "%(parameter)s is invalid") % {'value': None,
                                                              'parameter': key}
                             )
                )

        if reference_data['resource_type'] not in self.RESOURCE_TYPES:
            raise exception.InvalidParameter(parameter='resource_type',
                                             parameter_type='RESOURCE_TYPES')

        if reference_data['aggregate'] not in self.AGGREGATES:
            raise exception.InvalidParameter(parameter='aggregate',
                                             parameter_type='AGGREGATES')

    @staticmethod
    def _extract_attribute(resource, attribute):
        """Retrieve the desired attribute from the resource

        :param resource: The resource object to extract the attribute from.
        :param attribute: The name of the attribute to subtract as string.
        :return: The extracted attribute or None
        """

        try:
            return getattr(resource, attribute)
        except AttributeError:
            raise

    @staticmethod
    def _query_format(query, aggregate, resource, period,
                      granularity, translator_specific):
        return query.format(aggregate, resource, period, granularity,
                            translator_specific)

    @abc.abstractmethod
    def build_params(self):
        """Build the set of parameters to send with the request"""
        raise NotImplementedError()

    @abc.abstractmethod
    def extract_result(self, raw_results):
        """Extrapolate the metric from the raw results of the request"""
        raise NotImplementedError()
