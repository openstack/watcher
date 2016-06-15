# -*- encoding: utf-8 -*-
# Copyright (c) 2016 b<>com
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
import six

from oslo_log import log
import voluptuous

from watcher._i18n import _
from watcher.common import exception

LOG = log.getLogger(__name__)


@six.add_metaclass(abc.ABCMeta)
class IndicatorSpecification(object):

    def __init__(self, name=None, description=None, unit=None, required=True):
        self.name = name
        self.description = description
        self.unit = unit
        self.required = required

    @abc.abstractproperty
    def schema(self):
        """Schema used to validate the indicator value

        :return: A Voplutuous Schema
        :rtype: :py:class:`.voluptuous.Schema` instance
        """
        raise NotImplementedError()

    @classmethod
    def validate(cls, solution):
        """Validate the given solution

        :raises: :py:class:`~.InvalidIndicatorValue` when the validation fails
        """
        indicator = cls()
        value = None
        try:
            value = getattr(solution, indicator.name)
            indicator.schema(value)
        except Exception as exc:
            LOG.exception(exc)
            raise exception.InvalidIndicatorValue(
                name=indicator.name, value=value, spec_type=type(indicator))

    def to_dict(self):
        return {
            "name": self.name,
            "description": self.description,
            "unit": self.unit,
            "schema": str(self.schema.schema) if self.schema else None,
        }

    def __str__(self):
        return str(self.to_dict())


class AverageCpuLoad(IndicatorSpecification):

    def __init__(self):
        super(AverageCpuLoad, self).__init__(
            name="avg_cpu_percent",
            description=_("Average CPU load as a percentage of the CPU time."),
            unit="%",
        )

    @property
    def schema(self):
        return voluptuous.Schema(
            voluptuous.Range(min=0, max=100), required=True)


class MigrationEfficacy(IndicatorSpecification):

    def __init__(self):
        super(MigrationEfficacy, self).__init__(
            name="migration_efficacy",
            description=_("Represents the percentage of released nodes out of "
                          "the total number of migrations."),
            unit="%",
            required=True
        )

    @property
    def schema(self):
        return voluptuous.Schema(
            voluptuous.Range(min=0, max=100), required=True)


class ReleasedComputeNodesCount(IndicatorSpecification):
    def __init__(self):
        super(ReleasedComputeNodesCount, self).__init__(
            name="released_compute_nodes_count",
            description=_("The number of compute nodes to be released."),
            unit=None,
        )

    @property
    def schema(self):
        return voluptuous.Schema(
            voluptuous.Range(min=0), required=True)


class VmMigrationsCount(IndicatorSpecification):
    def __init__(self):
        super(VmMigrationsCount, self).__init__(
            name="vm_migrations_count",
            description=_("The number of migrations to be performed."),
            unit=None,
        )

    @property
    def schema(self):
        return voluptuous.Schema(
            voluptuous.Range(min=0), required=True)
