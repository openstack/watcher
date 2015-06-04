# -*- encoding: utf-8 -*-
# Copyright (c) 2015 b<>com
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

from enum import Enum


class ResourceType(Enum):
    cpu_cores = 'num_cores'
    memory = 'memory'
    disk = 'disk'


class Resource(object):
    def __init__(self, name, capacity=None):
        """Resource

        :param name: ResourceType
        :param capacity: max
        :return:
        """
        self.name = name
        self.capacity = capacity
        self.mapping = {}

    def get_name(self):
        return self.name

    def set_capacity(self, element, value):
        self.mapping[element.get_uuid()] = value

    def get_capacity_from_id(self, uuid):
        if str(uuid) in self.mapping.keys():
            return self.mapping[str(uuid)]
        else:
            # TODO(jed) throw exception
            return None

    def get_capacity(self, element):
        return self.get_capacity_from_id(element.get_uuid())
