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

"""Watcher base exception handling.

Includes decorator for re-raising Watcher-type exceptions.

SHOULD include dedicated exception logging.

"""

import functools
import sys

from keystoneclient import exceptions as keystone_exceptions
from oslo_config import cfg
from oslo_log import log as logging
import six

from watcher._i18n import _, _LE

LOG = logging.getLogger(__name__)

exc_log_opts = [
    cfg.BoolOpt('fatal_exception_format_errors',
                default=False,
                help='Make exception message format errors fatal.'),
]

CONF = cfg.CONF
CONF.register_opts(exc_log_opts)


def wrap_keystone_exception(func):
    """Wrap keystone exceptions and throw Watcher specific exceptions."""
    @functools.wraps(func)
    def wrapped(*args, **kw):
        try:
            return func(*args, **kw)
        except keystone_exceptions.AuthorizationFailure:
            raise AuthorizationFailure(
                client=func.__name__, reason=sys.exc_info()[1])
        except keystone_exceptions.ClientException:
            raise AuthorizationFailure(
                client=func.__name__,
                reason=(_('Unexpected keystone client error occurred: %s')
                        % sys.exc_info()[1]))
    return wrapped


class WatcherException(Exception):
    """Base Watcher Exception

    To correctly use this class, inherit from it and define
    a 'msg_fmt' property. That msg_fmt will get printf'd
    with the keyword arguments provided to the constructor.

    """
    msg_fmt = _("An unknown exception occurred")
    code = 500
    headers = {}
    safe = False

    def __init__(self, message=None, **kwargs):
        self.kwargs = kwargs

        if 'code' not in self.kwargs:
            try:
                self.kwargs['code'] = self.code
            except AttributeError:
                pass

        if not message:
            try:
                message = self.msg_fmt % kwargs
            except Exception as e:
                # kwargs doesn't match a variable in msg_fmt
                # log the issue and the kwargs
                LOG.exception(_LE('Exception in string format operation'))
                for name, value in kwargs.items():
                    LOG.error("%s: %s", name, value)

                if CONF.fatal_exception_format_errors:
                    raise e
                else:
                    # at least get the core msg_fmt out if something happened
                    message = self.msg_fmt

        super(WatcherException, self).__init__(message)

    def __str__(self):
        """Encode to utf-8 then wsme api can consume it as well"""
        if not six.PY3:
            return unicode(self.args[0]).encode('utf-8')
        else:
            return self.args[0]

    def __unicode__(self):
        return unicode(self.args[0])

    def format_message(self):
        if self.__class__.__name__.endswith('_Remote'):
            return self.args[0]
        else:
            return six.text_type(self)


class NotAuthorized(WatcherException):
    msg_fmt = _("Not authorized")
    code = 403


class PolicyNotAuthorized(NotAuthorized):
    msg_fmt = _("Policy doesn't allow %(action)s to be performed.")


class OperationNotPermitted(NotAuthorized):
    msg_fmt = _("Operation not permitted")


class Invalid(WatcherException):
    msg_fmt = _("Unacceptable parameters")
    code = 400


class ObjectNotFound(WatcherException):
    msg_fmt = _("The %(name)s %(id)s could not be found")


class Conflict(WatcherException):
    msg_fmt = _('Conflict')
    code = 409


class ResourceNotFound(ObjectNotFound):
    msg_fmt = _("The %(name)s resource %(id)s could not be found")
    code = 404


class InvalidIdentity(Invalid):
    msg_fmt = _("Expected a uuid or int but received %(identity)s")


class InvalidOperator(Invalid):
    msg_fmt = _("Filter operator is not valid: %(operator)s not "
                "in %(valid_operators)s")


class InvalidGoal(Invalid):
    msg_fmt = _("Goal %(goal)s is invalid")


class InvalidStrategy(Invalid):
    msg_fmt = _("Strategy %(strategy)s is invalid")


class InvalidUUID(Invalid):
    msg_fmt = _("Expected a uuid but received %(uuid)s")


class InvalidName(Invalid):
    msg_fmt = _("Expected a logical name but received %(name)s")


class InvalidUuidOrName(Invalid):
    msg_fmt = _("Expected a logical name or uuid but received %(name)s")


class GoalNotFound(ResourceNotFound):
    msg_fmt = _("Goal %(goal)s could not be found")


class GoalAlreadyExists(Conflict):
    msg_fmt = _("A goal with UUID %(uuid)s already exists")


class StrategyNotFound(ResourceNotFound):
    msg_fmt = _("Strategy %(strategy)s could not be found")


class StrategyAlreadyExists(Conflict):
    msg_fmt = _("A strategy with UUID %(uuid)s already exists")


class AuditTemplateNotFound(ResourceNotFound):
    msg_fmt = _("AuditTemplate %(audit_template)s could not be found")


class AuditTemplateAlreadyExists(Conflict):
    msg_fmt = _("An audit_template with UUID or name %(audit_template)s "
                "already exists")


class AuditTemplateReferenced(Invalid):
    msg_fmt = _("AuditTemplate %(audit_template)s is referenced by one or "
                "multiple audit")


class AuditTypeNotFound(Invalid):
    msg_fmt = _("Audit type %(audit_type)s could not be found")


class AuditNotFound(ResourceNotFound):
    msg_fmt = _("Audit %(audit)s could not be found")


class AuditAlreadyExists(Conflict):
    msg_fmt = _("An audit with UUID %(uuid)s already exists")


class AuditIntervalNotSpecified(Invalid):
    msg_fmt = _("Interval of audit must be specified for %(audit_type)s.")


class AuditIntervalNotAllowed(Invalid):
    msg_fmt = _("Interval of audit must not be set for %(audit_type)s.")


class AuditReferenced(Invalid):
    msg_fmt = _("Audit %(audit)s is referenced by one or multiple action "
                "plans")


class ActionPlanNotFound(ResourceNotFound):
    msg_fmt = _("ActionPlan %(action_plan)s could not be found")


class ActionPlanAlreadyExists(Conflict):
    msg_fmt = _("An action plan with UUID %(uuid)s already exists")


class ActionPlanReferenced(Invalid):
    msg_fmt = _("Action Plan %(action_plan)s is referenced by one or "
                "multiple actions")


class ActionNotFound(ResourceNotFound):
    msg_fmt = _("Action %(action)s could not be found")


class ActionAlreadyExists(Conflict):
    msg_fmt = _("An action with UUID %(uuid)s already exists")


class ActionReferenced(Invalid):
    msg_fmt = _("Action plan %(action_plan)s is referenced by one or "
                "multiple goals")


class ActionFilterCombinationProhibited(Invalid):
    msg_fmt = _("Filtering actions on both audit and action-plan is "
                "prohibited")


class EfficacyIndicatorNotFound(ResourceNotFound):
    msg_fmt = _("Efficacy indicator %(efficacy_indicator)s could not be found")


class EfficacyIndicatorAlreadyExists(Conflict):
    msg_fmt = _("An action with UUID %(uuid)s already exists")


class HTTPNotFound(ResourceNotFound):
    pass


class PatchError(Invalid):
    msg_fmt = _("Couldn't apply patch '%(patch)s'. Reason: %(reason)s")


# decision engine

class WorkflowExecutionException(WatcherException):
    msg_fmt = _('Workflow execution error: %(error)s')


class IllegalArgumentException(WatcherException):
    msg_fmt = _('Illegal argument')


class NoSuchMetric(WatcherException):
    msg_fmt = _('No such metric')


class NoDataFound(WatcherException):
    msg_fmt = _('No rows were returned')


class AuthorizationFailure(WatcherException):
    msg_fmt = _('%(client)s connection failed. Reason: %(reason)s')


class KeystoneFailure(WatcherException):
    msg_fmt = _("'Keystone API endpoint is missing''")


class ClusterEmpty(WatcherException):
    msg_fmt = _("The list of hypervisor(s) in the cluster is empty")


class MetricCollectorNotDefined(WatcherException):
    msg_fmt = _("The metrics resource collector is not defined")


class ClusterStateNotDefined(WatcherException):
    msg_fmt = _("The cluster state is not defined")


class NoAvailableStrategyForGoal(WatcherException):
    msg_fmt = _("No strategy could be found to achieve the '%(goal)s' goal.")


class InvalidIndicatorValue(WatcherException):
    msg_fmt = _("The indicator '%(name)s' with value '%(value)s' "
                "and spec type '%(spec_type)s' is invalid.")


class GlobalEfficacyComputationError(WatcherException):
    msg_fmt = _("Could not compute the global efficacy for the '%(goal)s' "
                "goal using the '%(strategy)s' strategy.")


class NoMetricValuesForVM(WatcherException):
    msg_fmt = _("No values returned by %(resource_id)s for %(metric_name)s.")


class NoSuchMetricForHost(WatcherException):
    msg_fmt = _("No %(metric)s metric for %(host)s found.")


# Model

class InstanceNotFound(WatcherException):
    msg_fmt = _("The instance '%(name)s' is not found")


class HypervisorNotFound(WatcherException):
    msg_fmt = _("The hypervisor is not found")


class LoadingError(WatcherException):
    msg_fmt = _("Error loading plugin '%(name)s'")


class ReservedWord(WatcherException):
    msg_fmt = _("The identifier '%(name)s' is a reserved word")


class NotSoftDeletedStateError(WatcherException):
    msg_fmt = _("The %(name)s resource %(id)s is not soft deleted")


class NegativeLimitError(WatcherException):
    msg_fmt = _("Limit should be positive")
