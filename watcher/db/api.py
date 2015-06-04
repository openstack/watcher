# Copyright 2013 Hewlett-Packard Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
"""
Base classes for storage engines
"""

import abc

from oslo_config import cfg
from oslo_db import api as db_api
import six


_BACKEND_MAPPING = {'sqlalchemy': 'watcher.db.sqlalchemy.api'}
IMPL = db_api.DBAPI.from_config(cfg.CONF, backend_mapping=_BACKEND_MAPPING,
                                lazy=True)


def get_instance():
    """Return a DB API instance."""
    return IMPL


@six.add_metaclass(abc.ABCMeta)
class Connection(object):
    """Base class for storage system connections."""

    @abc.abstractmethod
    def __init__(self):
        """Constructor."""

    @abc.abstractmethod
    def get_audit_template_list(self, context, columns=None, filters=None,
                                limit=None, marker=None, sort_key=None,
                                sort_dir=None):
        """Get specific columns for matching audit templates.

        Return a list of the specified columns for all audit templates that
        match the specified filters.

        :param context: The security context
        :param columns: List of column names to return.
                        Defaults to 'id' column when columns == None.
        :param filters: Filters to apply. Defaults to None.

        :param limit: Maximum number of audit templates to return.
        :param marker: the last item of the previous page; we return the next
                       result set.
        :param sort_key: Attribute by which results should be sorted.
        :param sort_dir: direction in which results should be sorted.
                         (asc, desc)
        :returns: A list of tuples of the specified columns.
        """

    @abc.abstractmethod
    def create_audit_template(self, values):
        """Create a new audit template.

        :param values: A dict containing several items used to identify
                       and track the audit template. For example:

                       ::

                        {
                         'uuid': utils.generate_uuid(),
                         'name': 'example',
                         'description': 'free text description'
                         'host_aggregate': 'nova aggregate name or id'
                         'goal': 'SERVER_CONSOLiDATION'
                         'extra': {'automatic': True}
                        }
        :returns: An audit template.
        :raises: AuditTemplateAlreadyExists
        """

    @abc.abstractmethod
    def get_audit_template_by_id(self, context, audit_template_id):
        """Return an audit template.

        :param context: The security context
        :param audit_template_id: The id of an audit template.
        :returns: An audit template.
        :raises: AuditTemplateNotFound
        """

    @abc.abstractmethod
    def get_audit_template_by_uuid(self, context, audit_template_uuid):
        """Return an audit template.

        :param context: The security context
        :param audit_template_uuid: The uuid of an audit template.
        :returns: An audit template.
        :raises: AuditTemplateNotFound
        """

    def get_audit_template_by__name(self, context, audit_template_name):
        """Return an audit template.

        :param context: The security context
        :param audit_template_name: The name of an audit template.
        :returns: An audit template.
        :raises: AuditTemplateNotFound
        """

    @abc.abstractmethod
    def destroy_audit_template(self, audit_template_id):
        """Destroy an audit_template.

        :param audit_template_id: The id or uuid of an audit template.
        :raises: AuditTemplateNotFound
        """

    @abc.abstractmethod
    def update_audit_template(self, audit_template_id, values):
        """Update properties of an audit template.

        :param audit_template_id: The id or uuid of an audit template.
        :returns: An audit template.
        :raises: AuditTemplateNotFound
        :raises: InvalidParameterValue
        """
    @abc.abstractmethod
    def soft_delete_audit_template(self, audit_template_id):
        """Soft delete an audit_template.

        :param audit_template_id: The id or uuid of an audit template.
        :raises: AuditTemplateNotFound
        """

    @abc.abstractmethod
    def get_audit_list(self, context, columns=None, filters=None, limit=None,
                       marker=None, sort_key=None, sort_dir=None):
        """Get specific columns for matching audits.

        Return a list of the specified columns for all audits that match the
        specified filters.

        :param context: The security context
        :param columns: List of column names to return.
                        Defaults to 'id' column when columns == None.
        :param filters: Filters to apply. Defaults to None.

        :param limit: Maximum number of audits to return.
        :param marker: the last item of the previous page; we return the next
                       result set.
        :param sort_key: Attribute by which results should be sorted.
        :param sort_dir: direction in which results should be sorted.
                         (asc, desc)
        :returns: A list of tuples of the specified columns.
        """

    @abc.abstractmethod
    def create_audit(self, values):
        """Create a new audit.

        :param values: A dict containing several items used to identify
                       and track the audit, and several dicts which are passed
                       into the Drivers when managing this audit. For example:

                       ::

                        {
                         'uuid': utils.generate_uuid(),
                         'type': 'ONESHOT',
                         'deadline': None
                        }
        :returns: An audit.
        :raises: AuditAlreadyExists
        """

    @abc.abstractmethod
    def get_audit_by_id(self, context, audit_id):
        """Return an audit.

        :param context: The security context
        :param audit_id: The id of an audit.
        :returns: An audit.
        :raises: AuditNotFound
        """

    @abc.abstractmethod
    def get_audit_by_uuid(self, context, audit_uuid):
        """Return an audit.

        :param context: The security context
        :param audit_uuid: The uuid of an audit.
        :returns: An audit.
        :raises: AuditNotFound
        """

    @abc.abstractmethod
    def destroy_audit(self, audit_id):
        """Destroy an audit and all associated action plans.

        :param audit_id: The id or uuid of an audit.
        :raises: AuditNotFound
        """

    @abc.abstractmethod
    def update_audit(self, audit_id, values):
        """Update properties of an audit.

        :param audit_id: The id or uuid of an audit.
        :returns: An audit.
        :raises: AuditNotFound
        :raises: InvalidParameterValue
        """

    def soft_delete_audit(self, audit_id):
        """Soft delete an audit and all associated action plans.

        :param audit_id: The id or uuid of an audit.
        :returns: An audit.
        :raises: AuditNotFound
        """

    @abc.abstractmethod
    def get_action_list(self, context, columns=None, filters=None, limit=None,
                        marker=None, sort_key=None, sort_dir=None):
        """Get specific columns for matching actions.

        Return a list of the specified columns for all actions that match the
        specified filters.

        :param context: The security context
        :param columns: List of column names to return.
                        Defaults to 'id' column when columns == None.
        :param filters: Filters to apply. Defaults to None.

        :param limit: Maximum number of actions to return.
        :param marker: the last item of the previous page; we return the next
                       result set.
        :param sort_key: Attribute by which results should be sorted.
        :param sort_dir: direction in which results should be sorted.
                         (asc, desc)
        :returns: A list of tuples of the specified columns.
        """

    @abc.abstractmethod
    def create_action(self, values):
        """Create a new action.

        :param values: A dict containing several items used to identify
                       and track the action, and several dicts which are passed
                       into the Drivers when managing this action. For example:

                       ::

                        {
                         'uuid': utils.generate_uuid(),
                         'name': 'example',
                         'description': 'free text description'
                         'aggregate': 'nova aggregate name or uuid'
                        }
        :returns: A action.
        :raises: ActionAlreadyExists
        """

    @abc.abstractmethod
    def get_action_by_id(self, context, action_id):
        """Return a action.

        :param context: The security context
        :param action_id: The id of a action.
        :returns: A action.
        :raises: ActionNotFound
        """

    @abc.abstractmethod
    def get_action_by_uuid(self, context, action_uuid):
        """Return a action.

        :param context: The security context
        :param action_uuid: The uuid of a action.
        :returns: A action.
        :raises: ActionNotFound
        """

    @abc.abstractmethod
    def destroy_action(self, action_id):
        """Destroy a action and all associated interfaces.

        :param action_id: The id or uuid of a action.
        :raises: ActionNotFound
        :raises: ActionReferenced
        """

    @abc.abstractmethod
    def update_action(self, action_id, values):
        """Update properties of a action.

        :param action_id: The id or uuid of a action.
        :returns: A action.
        :raises: ActionNotFound
        :raises: ActionReferenced
        """

    @abc.abstractmethod
    def get_action_plan_list(
        self, context, columns=None, filters=None, limit=None,
            marker=None, sort_key=None, sort_dir=None):
        """Get specific columns for matching action plans.

        Return a list of the specified columns for all action plans that
        match the specified filters.

        :param context: The security context
        :param columns: List of column names to return.
                        Defaults to 'id' column when columns == None.
        :param filters: Filters to apply. Defaults to None.

        :param limit: Maximum number of audits to return.
        :param marker: the last item of the previous page; we return the next
                       result set.
        :param sort_key: Attribute by which results should be sorted.
        :param sort_dir: direction in which results should be sorted.
                         (asc, desc)
        :returns: A list of tuples of the specified columns.
        """

    @abc.abstractmethod
    def create_action_plan(self, values):
        """Create a new action plan.

        :param values: A dict containing several items used to identify
                       and track the action plan.
        :returns: An action plan.
        :raises: ActionPlanAlreadyExists
        """

    @abc.abstractmethod
    def get_action_plan_by_id(self, context, action_plan_id):
        """Return an action plan.

        :param context: The security context
        :param action_plan_id: The id of an action plan.
        :returns: An action plan.
        :raises: ActionPlanNotFound
        """

    @abc.abstractmethod
    def get_action_plan_by_uuid(self, context, action_plan__uuid):
        """Return a action plan.

        :param context: The security context
        :param action_plan__uuid: The uuid of an action plan.
        :returns: An action plan.
        :raises: ActionPlanNotFound
        """

    @abc.abstractmethod
    def destroy_action_plan(self, action_plan_id):
        """Destroy an action plan and all associated interfaces.

        :param action_plan_id: The id or uuid of a action plan.
        :raises: ActionPlanNotFound
        :raises: ActionPlanReferenced
        """

    @abc.abstractmethod
    def update_action_plan(self, action_plan_id, values):
        """Update properties of an action plan.

        :param action_plan_id: The id or uuid of an action plan.
        :returns: An action plan.
        :raises: ActionPlanNotFound
        :raises: ActionPlanReferenced
        """
