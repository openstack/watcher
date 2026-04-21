# Copyright (c) 2017 ZTE Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import abc

from oslo_versionedobjects import fields as ovo_fields

from watcher.decision_engine.model.element import base


class BaremetalResource(base.Element, metaclass=abc.ABCMeta):
    VERSION = '1.0'

    fields = {
        "uuid": ovo_fields.StringField(),
        "human_id": ovo_fields.StringField(default=""),
    }
