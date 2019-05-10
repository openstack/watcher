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
import jsonschema
from jsonschema import SchemaError
from jsonschema import ValidationError
import six

from oslo_log import log
from oslo_serialization import jsonutils

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
        """JsonSchema used to validate the indicator value

        :return: A Schema
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
            jsonschema.validate(value, cls.schema)
        except (SchemaError, ValidationError) as exc:
            LOG.exception(exc)
            raise
        except Exception as exc:
            LOG.exception(exc)
            raise exception.InvalidIndicatorValue(
                name=indicator.name, value=value, spec_type=type(indicator))

    def to_dict(self):
        return {
            "name": self.name,
            "description": self.description,
            "unit": self.unit,
            "schema": jsonutils.dumps(self.schema) if self.schema else None,
        }

    def __str__(self):
        return str(self.to_dict())


class ComputeNodesCount(IndicatorSpecification):
    def __init__(self):
        super(ComputeNodesCount, self).__init__(
            name="compute_nodes_count",
            description=_("The total number of enabled compute nodes."),
            unit=None,
        )

    @property
    def schema(self):
        return {
            "type": "integer",
            "minimum": 0
        }


class ReleasedComputeNodesCount(IndicatorSpecification):
    def __init__(self):
        super(ReleasedComputeNodesCount, self).__init__(
            name="released_compute_nodes_count",
            description=_("The number of compute nodes to be released."),
            unit=None,
        )

    @property
    def schema(self):
        return {
            "type": "integer",
            "minimum": 0
        }


class InstancesCount(IndicatorSpecification):
    def __init__(self):
        super(InstancesCount, self).__init__(
            name="instances_count",
            description=_("The total number of audited instances in "
                          "strategy."),
            unit=None,
            required=False,
        )

    @property
    def schema(self):
        return {
            "type": "integer",
            "minimum": 0
        }


class InstanceMigrationsCount(IndicatorSpecification):
    def __init__(self):
        super(InstanceMigrationsCount, self).__init__(
            name="instance_migrations_count",
            description=_("The number of VM migrations to be performed."),
            unit=None,
        )

    @property
    def schema(self):
        return {
            "type": "integer",
            "minimum": 0
        }


class LiveInstanceMigrateCount(IndicatorSpecification):
    def __init__(self):
        super(LiveInstanceMigrateCount, self).__init__(
            name="live_migrate_instance_count",
            description=_("The number of instances actually live migrated."),
            unit=None,
        )

    @property
    def schema(self):
        return {
            "type": "integer",
            "minimum": 0
        }


class PlannedLiveInstanceMigrateCount(IndicatorSpecification):
    def __init__(self):
        super(PlannedLiveInstanceMigrateCount, self).__init__(
            name="planned_live_migrate_instance_count",
            description=_("The number of instances planned to live migrate."),
            unit=None,
        )

    @property
    def schema(self):
        return {
            "type": "integer",
            "minimum": 0
        }


class ColdInstanceMigrateCount(IndicatorSpecification):
    def __init__(self):
        super(ColdInstanceMigrateCount, self).__init__(
            name="cold_migrate_instance_count",
            description=_("The number of instances actually cold migrated."),
            unit=None,
        )

    @property
    def schema(self):
        return {
            "type": "integer",
            "minimum": 0
        }


class PlannedColdInstanceMigrateCount(IndicatorSpecification):
    def __init__(self):
        super(PlannedColdInstanceMigrateCount, self).__init__(
            name="planned_cold_migrate_instance_count",
            description=_("The number of instances planned to cold migrate."),
            unit=None,
        )

    @property
    def schema(self):
        return {
            "type": "integer",
            "minimum": 0
        }


class VolumeMigrateCount(IndicatorSpecification):
    def __init__(self):
        super(VolumeMigrateCount, self).__init__(
            name="volume_migrate_count",
            description=_("The number of detached volumes actually migrated."),
            unit=None,
        )

    @property
    def schema(self):
        return {
            "type": "integer",
            "minimum": 0
        }


class PlannedVolumeMigrateCount(IndicatorSpecification):
    def __init__(self):
        super(PlannedVolumeMigrateCount, self).__init__(
            name="planned_volume_migrate_count",
            description=_("The number of detached volumes planned"
                          " to migrate."),
            unit=None,
        )

    @property
    def schema(self):
        return {
            "type": "integer",
            "minimum": 0
        }


class VolumeUpdateCount(IndicatorSpecification):
    def __init__(self):
        super(VolumeUpdateCount, self).__init__(
            name="volume_update_count",
            description=_("The number of attached volumes actually"
                          " migrated."),
            unit=None,
        )

    @property
    def schema(self):
        return {
            "type": "integer",
            "minimum": 0
        }


class PlannedVolumeUpdateCount(IndicatorSpecification):
    def __init__(self):
        super(PlannedVolumeUpdateCount, self).__init__(
            name="planned_volume_update_count",
            description=_("The number of attached volumes planned to"
                          " migrate."),
            unit=None,
        )

    @property
    def schema(self):
        return {
            "type": "integer",
            "minimum": 0
        }


class StandardDeviationValue(IndicatorSpecification):
    def __init__(self):
        super(StandardDeviationValue, self).__init__(
            name="standard_deviation_after_audit",
            description=_("The value of resulted standard deviation."),
            unit=None,
            required=False,
        )

    @property
    def schema(self):
        return {
            "type": "number",
            "minimum": 0
        }


class OriginalStandardDeviationValue(IndicatorSpecification):
    def __init__(self):
        super(OriginalStandardDeviationValue, self).__init__(
            name="standard_deviation_before_audit",
            description=_("The value of original standard deviation."),
            unit=None,
            required=False,
        )

    @property
    def schema(self):
        return {
            "type": "number",
            "minimum": 0
        }
