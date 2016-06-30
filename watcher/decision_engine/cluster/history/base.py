# -*- encoding: utf-8 -*-
# Copyright (c) 2015 b<>com
#
# Authors: Jean-Emile DARTOIS <jean-emile.dartois@b-com.com>
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
#

"""
The :ref:`Cluster History <cluster_history_definition>` contains all the
previously collected timestamped data such as metrics and events associated
to any :ref:`managed resource <managed_resource_definition>` of the
:ref:`Cluster <cluster_definition>`.

Just like the :ref:`Cluster Data Model <cluster_data_model_definition>`, this
history may be used by any :ref:`Strategy <strategy_definition>` in order to
find the most optimal :ref:`Solution <solution_definition>` during an
:ref:`Audit <audit_definition>`.

In the Watcher project, a generic
:ref:`Cluster History <cluster_history_definition>`
API is proposed with some helper classes in order to :

-  share a common measurement (events or metrics) naming based on what is
   defined in Ceilometer.
   See `the full list of available measurements <http://docs.openstack.org/admin-guide-cloud/telemetry-measurements.html>`_
-  share common meter types (Cumulative, Delta, Gauge) based on what is
   defined in Ceilometer.
   See `the full list of meter types <http://docs.openstack.org/admin-guide-cloud/telemetry-measurements.html>`_
-  simplify the development of a new :ref:`Strategy <strategy_definition>`
-  avoid duplicating the same code in several
   :ref:`Strategies <strategy_definition>`
-  have a better consistency between the different
   :ref:`Strategies <strategy_definition>`
-  avoid any strong coupling with any external metrics/events storage system
   (the proposed API and measurement naming system acts as a pivot format)

Note however that a developer can use his/her own history management system if
the Ceilometer system does not fit his/her needs as long as the
:ref:`Strategy <strategy_definition>` is able to produce a
:ref:`Solution <solution_definition>` for the requested
:ref:`Goal <goal_definition>`.

The :ref:`Cluster History <cluster_history_definition>` data may be persisted
in any appropriate storage system (InfluxDB, OpenTSDB, MongoDB,...).
"""  # noqa

import abc
import six

""" Work in progress Helper to query metrics """


@six.add_metaclass(abc.ABCMeta)
class BaseClusterHistory(object):
    @abc.abstractmethod
    def statistic_aggregation(self, resource_id, meter_name, period,
                              aggregate='avg'):
        raise NotImplementedError()

    @abc.abstractmethod
    def get_last_sample_values(self, resource_id, meter_name, limit=1):
        raise NotImplementedError()

    def query_sample(self, meter_name, query, limit=1):
        raise NotImplementedError()

    def statistic_list(self, meter_name, query=None, period=None):
        raise NotImplementedError()
