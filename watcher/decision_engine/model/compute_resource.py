# -*- encoding: utf-8 -*-
# Copyright (c) 2015 b<>com
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


class ComputeResource(object):

    def __init__(self):
        self._uuid = ""
        self._human_id = ""
        self._hostname = ""

    @property
    def uuid(self):
        return self._uuid

    @uuid.setter
    def uuid(self, u):
        self._uuid = u

    @property
    def hostname(self):
        return self._hostname

    @hostname.setter
    def hostname(self, h):
        self._hostname = h

    @property
    def human_id(self):
        return self._human_id

    @human_id.setter
    def human_id(self, h):
        self._human_id = h

    def __str__(self):
        return "[{0}]".format(self.uuid)
