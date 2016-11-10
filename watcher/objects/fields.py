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

from oslo_log import log
from oslo_versionedobjects import fields


LOG = log.getLogger(__name__)


IntegerField = fields.IntegerField
UUIDField = fields.UUIDField
StringField = fields.StringField
DateTimeField = fields.DateTimeField
BooleanField = fields.BooleanField
ListOfStringsField = fields.ListOfStringsField


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
