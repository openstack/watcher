# -*- encoding: utf-8 -*-
# Copyright (c) 2016 b<>com
#
# Authors: Vincent FRANCOISE <Vincent.FRANCOISE@b-com.com>
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

import re

import oslo_messaging as om
import six


class NotificationFilter(om.NotificationFilter):
    """Notification Endpoint base class

    This class is responsible for handling incoming notifications. Depending
    on the priority level of the incoming, you may need to implement one or
    more of the following methods:

    .. code: py
        def audit(self, ctxt, publisher_id, event_type, payload, metadata):
            do_something(payload)

        def info(self, ctxt, publisher_id, event_type, payload, metadata):
            do_something(payload)

        def warn(self, ctxt, publisher_id, event_type, payload, metadata):
            do_something(payload)

        def error(self, ctxt, publisher_id, event_type, payload, metadata):
            do_something(payload)

        def critical(self, ctxt, publisher_id, event_type, payload, metadata):
            do_something(payload)
    """

    def _build_regex_dict(self, regex_list):
        if regex_list is None:
            return {}

        regex_mapping = {}
        for key, value in regex_list.items():
            if isinstance(value, dict):
                regex_mapping[key] = self._build_regex_dict(value)
            else:
                if callable(value):
                    regex_mapping[key] = value
                elif value is not None:
                    regex_mapping[key] = re.compile(value)
                else:
                    regex_mapping[key] = None

        return regex_mapping

    def _check_for_mismatch(self, data, regex):
        if isinstance(regex, dict):
            mismatch_results = [
                k not in data or not self._check_for_mismatch(data[k], v)
                for k, v in regex.items()
            ]
            if not mismatch_results:
                return False

            return all(mismatch_results)
        elif callable(regex):
            # The filter is a callable that should return True
            # if there is a mismatch
            return regex(data)
        elif regex is not None and data is None:
            return True
        elif (regex is not None and
              isinstance(data, six.string_types) and
              not regex.match(data)):
            return True

        return False
