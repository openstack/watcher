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

from oslo_log import log

from watcher.applier.actions import base
from watcher.common import exception

LOG = log.getLogger(__name__)


class Nop(base.BaseAction):
    """logs a message

    The action schema is::

        schema = Schema({
         'message': str,
        })

    The `message` is the actual message that will be logged.
    """

    MESSAGE = 'message'

    @property
    def schema(self):
        return {
            'type': 'object',
            'properties': {
                'message': {
                    'type': ['string', 'null']
                },
                'fail_pre_condition': {
                    'type': 'boolean',
                    'default': False
                },
                'fail_execute': {
                    'type': 'boolean',
                    'default': False
                },
                'fail_post_condition': {
                    'type': 'boolean',
                    'default': False
                }
            },
            'required': ['message'],
            'additionalProperties': False,
        }

    @property
    def message(self):
        return self.input_parameters.get(self.MESSAGE)

    def debug_message(self, message):
        return ("Executing action NOP message: %s ", message)

    def execute(self):
        LOG.debug(self.debug_message(self.message))
        if self.input_parameters.get('fail_execute'):
            return False
        return True

    def revert(self):
        LOG.debug("Revert action NOP")
        return True

    def pre_condition(self):
        if self.input_parameters.get('fail_pre_condition'):
            raise exception.WatcherException("Failed in pre_condition")

    def post_condition(self):
        if self.input_parameters.get('fail_post_condition'):
            raise exception.WatcherException("Failed in post_condition")

    def get_description(self):
        """Description of the action"""
        return "Logging a NOP message"

    def abort(self):
        LOG.debug("Abort action NOP")
        return True
