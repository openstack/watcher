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

from oslo_config import cfg
import six

from watcher.common.i18n import _
from watcher.common.i18n import _LE
from watcher.openstack.common import log as logging

LOG = logging.getLogger(__name__)

exc_log_opts = [
    cfg.BoolOpt('fatal_exception_format_errors',
                default=False,
                help='Make exception message format errors fatal.'),
]

CONF = cfg.CONF
CONF.register_opts(exc_log_opts)


def _cleanse_dict(original):
    """Strip all admin_password, new_pass, rescue_pass keys from a dict."""
    return dict((k, v) for k, v in original.iteritems() if "_pass" not in k)


class WatcherException(Exception):
    """Base Watcher Exception

    To correctly use this class, inherit from it and define
    a 'message' property. That message will get printf'd
    with the keyword arguments provided to the constructor.

    """
    message = _("An unknown exception occurred.")
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
                message = self.message % kwargs

            except Exception as e:
                # kwargs doesn't match a variable in the message
                # log the issue and the kwargs
                LOG.exception(_LE('Exception in string format operation'))
                for name, value in kwargs.iteritems():
                    LOG.error("%s: %s" % (name, value))

                if CONF.fatal_exception_format_errors:
                    raise e
                else:
                    # at least get the core message out if something happened
                    message = self.message

        super(WatcherException, self).__init__(message)

    def __str__(self):
        """Encode to utf-8 then wsme api can consume it as well."""
        if not six.PY3:
            return unicode(self.args[0]).encode('utf-8')
        else:
            return self.args[0]

    def __unicode__(self):
        return self.message

    def format_message(self):
        if self.__class__.__name__.endswith('_Remote'):
            return self.args[0]
        else:
            return six.text_type(self)


class NotAuthorized(WatcherException):
    message = _("Not authorized.")
    code = 403


class OperationNotPermitted(NotAuthorized):
    message = _("Operation not permitted.")


class Invalid(WatcherException):
    message = _("Unacceptable parameters.")
    code = 400


class ObjectNotFound(WatcherException):
    message = _("The %(name)s %(id)s could not be found.")


class Conflict(WatcherException):
    message = _('Conflict.')
    code = 409


class ResourceNotFound(ObjectNotFound):
    message = _("The %(name)s resource %(id)s could not be found.")
    code = 404


class InvalidIdentity(Invalid):
    message = _("Expected an uuid or int but received %(identity)s.")


class InvalidGoal(Invalid):
    message = _("Goal %(goal)s is not defined in Watcher configuration file.")


# Cannot be templated as the error syntax varies.
# msg needs to be constructed when raised.
class InvalidParameterValue(Invalid):
    message = _("%(err)s")


class InvalidUUID(Invalid):
    message = _("Expected a uuid but received %(uuid)s.")


class InvalidName(Invalid):
    message = _("Expected a logical name but received %(name)s.")


class InvalidUuidOrName(Invalid):
    message = _("Expected a logical name or uuid but received %(name)s.")


class AuditTemplateNotFound(ResourceNotFound):
    message = _("AuditTemplate %(audit_template)s could not be found.")


class AuditTemplateAlreadyExists(Conflict):
    message = _("An audit_template with UUID %(uuid)s or name %(name)s "
                "already exists.")


class AuditTemplateReferenced(Invalid):
    message = _("AuditTemplate %(audit_template)s is referenced by one or "
                "multiple audit.")


class AuditNotFound(ResourceNotFound):
    message = _("Audit %(audit)s could not be found.")


class AuditAlreadyExists(Conflict):
    message = _("An audit with UUID %(uuid)s already exists.")


class AuditReferenced(Invalid):
    message = _("Audit %(audit)s is referenced by one or multiple action "
                "plans.")


class ActionPlanNotFound(ResourceNotFound):
    message = _("ActionPlan %(action plan)s could not be found.")


class ActionPlanAlreadyExists(Conflict):
    message = _("An action plan with UUID %(uuid)s already exists.")


class ActionPlanReferenced(Invalid):
    message = _("Action Plan %(action_plan)s is referenced by one or "
                "multiple actions.")


class ActionNotFound(ResourceNotFound):
    message = _("Action %(action)s could not be found.")


class ActionAlreadyExists(Conflict):
    message = _("An action with UUID %(uuid)s already exists.")


class ActionReferenced(Invalid):
    message = _("Action plan %(action_plan)s is referenced by one or "
                "multiple goals.")


class ActionFilterCombinationProhibited(Invalid):
    message = _("Filtering actions on both audit and action-plan is "
                "prohibited.")


class HTTPNotFound(ResourceNotFound):
    pass


class PatchError(Invalid):
    message = _("Couldn't apply patch '%(patch)s'. Reason: %(reason)s")


# decision engine


class BaseException(Exception):

    def __init__(self, desc=""):
        if (not isinstance(desc, basestring)):
            raise IllegalArgumentException(
                "Description must be an instance of str")

        desc = desc.strip()

        self._desc = desc

    def get_description(self):
        return self._desc

    def get_message(self):
        return "An exception occurred without a description."

    def __str__(self):
        return self.get_message()


class IllegalArgumentException(BaseException):
    def __init__(self, desc):
        BaseException.__init__(self, desc)

        if self._desc == "":
            raise IllegalArgumentException("Description cannot be empty")

    def get_message(self):
        return self._desc


class NoSuchMetric(BaseException):
    def __init__(self, desc):
        BaseException.__init__(self, desc)

        if self._desc == "":
            raise NoSuchMetric("No such metric")

    def get_message(self):
        return self._desc


class NoDataFound(BaseException):
    def __init__(self, desc):
        BaseException.__init__(self, desc)

        if self._desc == "":
            raise NoSuchMetric("no rows were returned")

    def get_message(self):
        return self._desc


class ClusterEmpty(WatcherException):
    message = _("The list of hypervisor(s) in the cluster is empty.'")


class MetricCollectorNotDefined(WatcherException):
    message = _("The metrics resource collector is not defined.'")


class ClusteStateNotDefined(WatcherException):
    message = _("the cluster state is not defined")


# Model

class VMNotFound(WatcherException):
    message = _("The VM could not be found.")


class HypervisorNotFound(WatcherException):
    message = _("The hypervisor could not be found.")


class MetaActionNotFound(WatcherException):
    message = _("The Meta-Action could not be found.")
