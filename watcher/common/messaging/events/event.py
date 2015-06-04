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


class Event(object):
    """Generic event to use with EventDispatcher"""

    def __init__(self, event_type=None, data=None, request_id=None):
        """Default constructor

        :param event_type: the type of the event
        :param data: a dictionary which contains data
        :param request_id: a string which represent the uuid of the request
        """
        self._type = event_type
        self._data = data
        self._request_id = request_id

    def get_type(self):
        return self._type

    def set_type(self, type):
        self._type = type

    def get_data(self):
        return self._data

    def set_data(self, data):
        self._data = data

    def set_request_id(self, id):
        self._request_id = id

    def get_request_id(self):
        return self._request_id
