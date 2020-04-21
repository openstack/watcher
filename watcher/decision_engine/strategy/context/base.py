# -*- encoding: utf-8 -*-
# Copyright (c) 2015 b<>com
#
# Authors: Jean-Emile DARTOIS <jean-emile.dartois@b-com.com>
#          Vincent FRANCOISE <vincent.francoise@b-com.com>
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

from watcher import notifications
from watcher.objects import fields


class StrategyContext(object, metaclass=abc.ABCMeta):

    def execute_strategy(self, audit, request_context):
        """Execute the strategy for the given an audit

        :param audit: Audit object
        :type audit: :py:class:`~.objects.audit.Audit` instance
        :param request_context: Current request context
        :type request_context: :py:class:`~.RequestContext` instance
        :returns: The computed solution
        :rtype: :py:class:`~.BaseSolution` instance
        """
        try:
            notifications.audit.send_action_notification(
                request_context, audit,
                action=fields.NotificationAction.STRATEGY,
                phase=fields.NotificationPhase.START)
            solution = self.do_execute_strategy(audit, request_context)
            notifications.audit.send_action_notification(
                request_context, audit,
                action=fields.NotificationAction.STRATEGY,
                phase=fields.NotificationPhase.END)
            return solution
        except Exception:
            notifications.audit.send_action_notification(
                request_context, audit,
                action=fields.NotificationAction.STRATEGY,
                priority=fields.NotificationPriority.ERROR,
                phase=fields.NotificationPhase.ERROR)
            raise

    @abc.abstractmethod
    def do_execute_strategy(self, audit, request_context):
        """Execute the strategy for the given an audit

        :param audit: Audit object
        :type audit: :py:class:`~.objects.audit.Audit` instance
        :param request_context: Current request context
        :type request_context: :py:class:`~.RequestContext` instance
        :returns: The computed solution
        :rtype: :py:class:`~.BaseSolution` instance
        """
        raise NotImplementedError()
