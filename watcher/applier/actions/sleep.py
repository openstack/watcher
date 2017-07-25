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

import time

from oslo_log import log
from watcher.applier.actions import base

LOG = log.getLogger(__name__)


class Sleep(base.BaseAction):
    """Makes the executor of the action plan wait for a given duration

    The action schema is::

        schema = Schema({
         'duration': float,
        })

    The `duration` is expressed in seconds.
    """

    DURATION = 'duration'

    @property
    def schema(self):
        return {
            'type': 'object',
            'properties': {
                'duration': {
                    'type': 'number',
                    'minimum': 0
                },
            },
            'required': ['duration'],
            'additionalProperties': False,
        }

    @property
    def duration(self):
        return int(self.input_parameters.get(self.DURATION))

    def execute(self):
        LOG.debug("Starting action sleep with duration: %s ", self.duration)
        time.sleep(self.duration)
        return True

    def revert(self):
        LOG.debug("Revert action sleep")
        return True

    def pre_condition(self):
        pass

    def post_condition(self):
        pass

    def get_description(self):
        """Description of the action"""
        return "Wait for a given interval in seconds."

    def abort(self):
        LOG.debug("Abort action sleep")
        return True
