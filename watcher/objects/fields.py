#    Copyright 2013 IBM Corp.
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

"""Utility methods for objects"""

import ast
import six

from oslo_versionedobjects import fields


BaseEnumField = fields.BaseEnumField
BooleanField = fields.BooleanField
DateTimeField = fields.DateTimeField
Enum = fields.Enum
FloatField = fields.FloatField
IntegerField = fields.IntegerField
ListOfStringsField = fields.ListOfStringsField
NonNegativeFloatField = fields.NonNegativeFloatField
NonNegativeIntegerField = fields.NonNegativeIntegerField
ObjectField = fields.ObjectField
StringField = fields.StringField
UnspecifiedDefault = fields.UnspecifiedDefault
UUIDField = fields.UUIDField


class Numeric(fields.FieldType):
    @staticmethod
    def coerce(obj, attr, value):
        if value is None:
            return value
        f_value = float(value)
        return f_value if not f_value.is_integer() else value


class NumericField(fields.AutoTypedField):
    AUTO_TYPE = Numeric()


class DictField(fields.AutoTypedField):
    AUTO_TYPE = fields.Dict(fields.FieldType())


class FlexibleDict(fields.FieldType):
    @staticmethod
    def coerce(obj, attr, value):
        if isinstance(value, six.string_types):
            value = ast.literal_eval(value)
        return dict(value)


class FlexibleDictField(fields.AutoTypedField):
    AUTO_TYPE = FlexibleDict()

    # TODO(lucasagomes): In our code we've always translated None to {},
    # this method makes this field to work like this. But probably won't
    # be accepted as-is in the oslo_versionedobjects library
    def _null(self, obj, attr):
        if self.nullable:
            return {}
        super(FlexibleDictField, self)._null(obj, attr)


class FlexibleListOfDict(fields.FieldType):
    @staticmethod
    def coerce(obj, attr, value):
        if isinstance(value, six.string_types):
            value = ast.literal_eval(value)
        return list(value)


class FlexibleListOfDictField(fields.AutoTypedField):
    AUTO_TYPE = FlexibleListOfDict()

    # TODO(lucasagomes): In our code we've always translated None to {},
    # this method makes this field to work like this. But probably won't
    # be accepted as-is in the oslo_versionedobjects library
    def _null(self, obj, attr):
        if self.nullable:
            return []
        super(FlexibleListOfDictField, self)._null(obj, attr)


# ### Notification fields ### #

class BaseWatcherEnum(Enum):

    ALL = ()

    def __init__(self, **kwargs):
        super(BaseWatcherEnum, self).__init__(valid_values=self.__class__.ALL)


class NotificationPriority(BaseWatcherEnum):
    DEBUG = 'debug'
    INFO = 'info'
    WARNING = 'warning'
    ERROR = 'error'
    CRITICAL = 'critical'

    ALL = (DEBUG, INFO, WARNING, ERROR, CRITICAL)


class NotificationPhase(BaseWatcherEnum):
    START = 'start'
    END = 'end'
    ERROR = 'error'

    ALL = (START, END, ERROR)


class NotificationAction(BaseWatcherEnum):
    CREATE = 'create'
    UPDATE = 'update'
    EXCEPTION = 'exception'
    DELETE = 'delete'

    STRATEGY = 'strategy'
    PLANNER = 'planner'
    EXECUTION = 'execution'

    ALL = (CREATE, UPDATE, EXCEPTION, DELETE, STRATEGY, PLANNER, EXECUTION)


class NotificationPriorityField(BaseEnumField):
    AUTO_TYPE = NotificationPriority()


class NotificationPhaseField(BaseEnumField):
    AUTO_TYPE = NotificationPhase()


class NotificationActionField(BaseEnumField):
    AUTO_TYPE = NotificationAction()
