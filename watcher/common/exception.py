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
from oslo_log import log
import six

from watcher._i18n import _

LOG = log.getLogger(__name__)

CONF = cfg.CONF


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
            except Exception:
                # kwargs doesn't match a variable in msg_fmt
                # log the issue and the kwargs
                LOG.exception('Exception in string format operation')
                for name, value in kwargs.items():
                    LOG.error("%(name)s: %(value)s",
                              {'name': name, 'value': value})

                if CONF.fatal_exception_format_errors:
                    raise
                else:
                    # at least get the core msg_fmt out if something happened
                    message = self.msg_fmt

        super(WatcherException, self).__init__(message)

    def __str__(self):
        """Encode to utf-8 then wsme api can consume it as well"""
        if not six.PY3:
            return six.text_type(self.args[0]).encode('utf-8')
        else:
            return self.args[0]

    def __unicode__(self):
        return six.text_type(self.args[0])

    def format_message(self):
        if self.__class__.__name__.endswith('_Remote'):
            return self.args[0]
        else:
            return six.text_type(self)


class UnsupportedError(WatcherException):
    msg_fmt = _("Not supported")


class NotAuthorized(WatcherException):
    msg_fmt = _("Not authorized")
    code = 403


class NotAcceptable(WatcherException):
    msg_fmt = _("Request not acceptable.")
    code = 406


class PolicyNotAuthorized(NotAuthorized):
    msg_fmt = _("Policy doesn't allow %(action)s to be performed.")


class OperationNotPermitted(NotAuthorized):
    msg_fmt = _("Operation not permitted")


class Invalid(WatcherException, ValueError):
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


class InvalidParameter(Invalid):
    msg_fmt = _("%(parameter)s has to be of type %(parameter_type)s")


class InvalidIdentity(Invalid):
    msg_fmt = _("Expected a uuid or int but received %(identity)s")


class InvalidOperator(Invalid):
    msg_fmt = _("Filter operator is not valid: %(operator)s not "
                "in %(valid_operators)s")


class InvalidGoal(Invalid):
    msg_fmt = _("Goal %(goal)s is invalid")


class InvalidStrategy(Invalid):
    msg_fmt = _("Strategy %(strategy)s is invalid")


class InvalidAudit(Invalid):
    msg_fmt = _("Audit %(audit)s is invalid")


class EagerlyLoadedAuditRequired(InvalidAudit):
    msg_fmt = _("Audit %(audit)s was not eagerly loaded")


class InvalidActionPlan(Invalid):
    msg_fmt = _("Action plan %(action_plan)s is invalid")


class EagerlyLoadedActionPlanRequired(InvalidActionPlan):
    msg_fmt = _("Action plan %(action_plan)s was not eagerly loaded")


class EagerlyLoadedActionRequired(InvalidActionPlan):
    msg_fmt = _("Action %(action)s was not eagerly loaded")


class InvalidUUID(Invalid):
    msg_fmt = _("Expected a uuid but received %(uuid)s")


class InvalidName(Invalid):
    msg_fmt = _("Expected a logical name but received %(name)s")


class InvalidUuidOrName(Invalid):
    msg_fmt = _("Expected a logical name or uuid but received %(name)s")


class InvalidIntervalOrCron(Invalid):
    msg_fmt = _("Expected an interval or cron syntax but received %(name)s")


class DataModelTypeNotFound(ResourceNotFound):
    msg_fmt = _("The %(data_model_type)s data model could not be found")


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


class AuditTypeNotFound(Invalid):
    msg_fmt = _("Audit type %(audit_type)s could not be found")


class AuditParameterNotAllowed(Invalid):
    msg_fmt = _("Audit parameter %(parameter)s are not allowed")


class AuditNotFound(ResourceNotFound):
    msg_fmt = _("Audit %(audit)s could not be found")


class AuditAlreadyExists(Conflict):
    msg_fmt = _("An audit with UUID or name %(audit)s already exists")


class AuditIntervalNotSpecified(Invalid):
    msg_fmt = _("Interval of audit must be specified for %(audit_type)s.")


class AuditIntervalNotAllowed(Invalid):
    msg_fmt = _("Interval of audit must not be set for %(audit_type)s.")


class AuditStartEndTimeNotAllowed(Invalid):
    msg_fmt = _("Start or End time of audit must not be set for "
                "%(audit_type)s.")


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


class ActionPlanCancelled(WatcherException):
    msg_fmt = _("Action Plan with UUID %(uuid)s is cancelled by user")


class ActionPlanIsOngoing(Conflict):
    msg_fmt = _("Action Plan %(action_plan)s is currently running.")


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


class UnsupportedActionType(UnsupportedError):
    msg_fmt = _("Provided %(action_type)s is not supported yet")


class EfficacyIndicatorNotFound(ResourceNotFound):
    msg_fmt = _("Efficacy indicator %(efficacy_indicator)s could not be found")


class EfficacyIndicatorAlreadyExists(Conflict):
    msg_fmt = _("An action with UUID %(uuid)s already exists")


class ScoringEngineAlreadyExists(Conflict):
    msg_fmt = _("A scoring engine with UUID %(uuid)s already exists")


class ScoringEngineNotFound(ResourceNotFound):
    msg_fmt = _("ScoringEngine %(scoring_engine)s could not be found")


class HTTPNotFound(ResourceNotFound):
    pass


class PatchError(Invalid):
    msg_fmt = _("Couldn't apply patch '%(patch)s'. Reason: %(reason)s")


class DeleteError(Invalid):
    msg_fmt = _("Couldn't delete when state is '%(state)s'.")


class StartError(Invalid):
    msg_fmt = _("Couldn't start when state is '%(state)s'.")


# decision engine

class WorkflowExecutionException(WatcherException):
    msg_fmt = _('Workflow execution error: %(error)s')


class IllegalArgumentException(WatcherException):
    msg_fmt = _('Illegal argument')


class AuthorizationFailure(WatcherException):
    msg_fmt = _('%(client)s connection failed. Reason: %(reason)s')


class ClusterStateStale(WatcherException):
    msg_fmt = _("The cluster state is stale")


class ClusterDataModelCollectionError(WatcherException):
    msg_fmt = _("The cluster data model '%(cdm)s' could not be built")


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


class UnsupportedDataSource(UnsupportedError):
    msg_fmt = _("Datasource %(datasource)s is not supported "
                "by strategy %(strategy)s")


class DataSourceNotAvailable(WatcherException):
    msg_fmt = _("Datasource %(datasource)s is not available.")


class MetricNotAvailable(WatcherException):
    """Indicate that a metric is not configured or does not exists"""
    msg_fmt = _('Metric: %(metric)s not available')


class NoDatasourceAvailable(WatcherException):
    """No datasources have been configured"""
    msg_fmt = _('No datasources available')


class NoSuchMetricForHost(WatcherException):
    msg_fmt = _("No %(metric)s metric for %(host)s found.")


class ServiceAlreadyExists(Conflict):
    msg_fmt = _("A service with name %(name)s is already working on %(host)s.")


class ServiceNotFound(ResourceNotFound):
    msg_fmt = _("The service %(service)s cannot be found.")


class WildcardCharacterIsUsed(WatcherException):
    msg_fmt = _("You shouldn't use any other IDs of %(resource)s if you use "
                "wildcard character.")


class CronFormatIsInvalid(WatcherException):
    msg_fmt = _("Provided cron is invalid: %(message)s")


class ActionDescriptionAlreadyExists(Conflict):
    msg_fmt = _("An action description with type %(action_type)s is "
                "already exist.")


class ActionDescriptionNotFound(ResourceNotFound):
    msg_fmt = _("The action description %(action_id)s cannot be found.")


class ActionExecutionFailure(WatcherException):
    msg_fmt = _("The action %(action_id)s execution failed.")


# Model

class ComputeResourceNotFound(WatcherException):
    msg_fmt = _("The compute resource '%(name)s' could not be found")


class InstanceNotFound(ComputeResourceNotFound):
    msg_fmt = _("The instance '%(name)s' could not be found")


class InstanceNotMapped(ComputeResourceNotFound):
    msg_fmt = _("The mapped compute node for instance '%(uuid)s' "
                "could not be found.")


class ComputeNodeNotFound(ComputeResourceNotFound):
    msg_fmt = _("The compute node %(name)s could not be found")


class StorageResourceNotFound(WatcherException):
    msg_fmt = _("The storage resource '%(name)s' could not be found")


class StorageNodeNotFound(StorageResourceNotFound):
    msg_fmt = _("The storage node %(name)s could not be found")


class PoolNotFound(StorageResourceNotFound):
    msg_fmt = _("The pool %(name)s could not be found")


class VolumeNotFound(StorageResourceNotFound):
    msg_fmt = _("The volume '%(name)s' could not be found")


class BaremetalResourceNotFound(WatcherException):
    msg_fmt = _("The baremetal resource '%(name)s' could not be found")


class IronicNodeNotFound(BaremetalResourceNotFound):
    msg_fmt = _("The ironic node %(uuid)s could not be found")


class LoadingError(WatcherException):
    msg_fmt = _("Error loading plugin '%(name)s'")


class ReservedWord(WatcherException):
    msg_fmt = _("The identifier '%(name)s' is a reserved word")


class NotSoftDeletedStateError(WatcherException):
    msg_fmt = _("The %(name)s resource %(id)s is not soft deleted")


class NegativeLimitError(WatcherException):
    msg_fmt = _("Limit should be positive")


class NotificationPayloadError(WatcherException):
    msg_fmt = _("Payload not populated when trying to send notification "
                "\"%(class_name)s\"")


class InvalidPoolAttributeValue(Invalid):
    msg_fmt = _("The %(name)s pool %(attribute)s is not integer")
