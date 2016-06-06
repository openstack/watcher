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
class BaseConnection(object):
    """Base class for storage system connections."""

    @abc.abstractmethod
    def get_goal_list(self, context, filters=None, limit=None,
                      marker=None, sort_key=None, sort_dir=None):
        """Get specific columns for matching goals.

        Return a list of the specified columns for all goals that
        match the specified filters.

        :param context: The security context
        :param filters: Filters to apply. Defaults to None.

        :param limit: Maximum number of goals to return.
        :param marker: the last item of the previous page; we return the next
                       result set.
        :param sort_key: Attribute by which results should be sorted.
        :param sort_dir: direction in which results should be sorted.
                         (asc, desc)
        :returns: A list of tuples of the specified columns.
        """

    @abc.abstractmethod
    def create_goal(self, values):
        """Create a new goal.

        :param values: A dict containing several items used to identify
                       and track the goal. For example:

                       ::

                        {
                         'uuid': utils.generate_uuid(),
                         'name': 'DUMMY',
                         'display_name': 'Dummy',
                        }
        :returns: A goal
        :raises: :py:class:`~.GoalAlreadyExists`
        """

    @abc.abstractmethod
    def get_goal_by_id(self, context, goal_id):
        """Return a goal given its ID.

        :param context: The security context
        :param goal_id: The ID of a goal
        :returns: A goal
        :raises: :py:class:`~.GoalNotFound`
        """

    @abc.abstractmethod
    def get_goal_by_uuid(self, context, goal_uuid):
        """Return a goal given its UUID.

        :param context: The security context
        :param goal_uuid: The UUID of a goal
        :returns: A goal
        :raises: :py:class:`~.GoalNotFound`
        """

    @abc.abstractmethod
    def get_goal_by_name(self, context, goal_name):
        """Return a goal given its name.

        :param context: The security context
        :param goal_name: The name of a goal
        :returns: A goal
        :raises: :py:class:`~.GoalNotFound`
        """

    @abc.abstractmethod
    def destroy_goal(self, goal_uuid):
        """Destroy a goal.

        :param goal_uuid: The UUID of a goal
        :raises: :py:class:`~.GoalNotFound`
        """

    @abc.abstractmethod
    def update_goal(self, goal_uuid, values):
        """Update properties of a goal.

        :param goal_uuid: The UUID of a goal
        :param values: A dict containing several items used to identify
                       and track the goal. For example:

                       ::

                        {
                         'uuid': utils.generate_uuid(),
                         'name': 'DUMMY',
                         'display_name': 'Dummy',
                        }
        :returns: A goal
        :raises: :py:class:`~.GoalNotFound`
        :raises: :py:class:`~.Invalid`
        """

    @abc.abstractmethod
    def get_strategy_list(self, context, filters=None, limit=None,
                          marker=None, sort_key=None, sort_dir=None):
        """Get specific columns for matching strategies.

        Return a list of the specified columns for all strategies that
        match the specified filters.

        :param context: The security context
        :param filters: Filters to apply. Defaults to None.

        :param limit: Maximum number of strategies to return.
        :param marker: The last item of the previous page; we return the next
                       result set.
        :param sort_key: Attribute by which results should be sorted.
        :param sort_dir: Direction in which results should be sorted.
                         (asc, desc)
        :returns: A list of tuples of the specified columns.
        """

    @abc.abstractmethod
    def create_strategy(self, values):
        """Create a new strategy.

        :param values: A dict containing items used to identify
                       and track the strategy. For example:

                       ::

                        {
                         'id': 1,
                         'uuid': utils.generate_uuid(),
                         'name': 'my_strategy',
                         'display_name': 'My strategy',
                         'goal_uuid': utils.generate_uuid(),
                        }
        :returns: A strategy
        :raises: :py:class:`~.StrategyAlreadyExists`
        """

    @abc.abstractmethod
    def get_strategy_by_id(self, context, strategy_id):
        """Return a strategy given its ID.

        :param context: The security context
        :param strategy_id: The ID of a strategy
        :returns: A strategy
        :raises: :py:class:`~.StrategyNotFound`
        """

    @abc.abstractmethod
    def get_strategy_by_uuid(self, context, strategy_uuid):
        """Return a strategy given its UUID.

        :param context: The security context
        :param strategy_uuid: The UUID of a strategy
        :returns: A strategy
        :raises: :py:class:`~.StrategyNotFound`
        """

    @abc.abstractmethod
    def get_strategy_by_name(self, context, strategy_name):
        """Return a strategy given its name.

        :param context: The security context
        :param strategy_name: The name of a strategy
        :returns: A strategy
        :raises: :py:class:`~.StrategyNotFound`
        """

    @abc.abstractmethod
    def destroy_strategy(self, strategy_uuid):
        """Destroy a strategy.

        :param strategy_uuid: The UUID of a strategy
        :raises: :py:class:`~.StrategyNotFound`
        """

    @abc.abstractmethod
    def update_strategy(self, strategy_uuid, values):
        """Update properties of a strategy.

        :param strategy_uuid: The UUID of a strategy
        :returns: A strategy
        :raises: :py:class:`~.StrategyNotFound`
        :raises: :py:class:`~.Invalid`
        """

    @abc.abstractmethod
    def get_audit_template_list(self, context, filters=None,
                                limit=None, marker=None, sort_key=None,
                                sort_dir=None):
        """Get specific columns for matching audit templates.

        Return a list of the specified columns for all audit templates that
        match the specified filters.

        :param context: The security context
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
                         'goal': 'DUMMY'
                         'extra': {'automatic': True}
                        }
        :returns: An audit template.
        :raises: :py:class:`~.AuditTemplateAlreadyExists`
        """

    @abc.abstractmethod
    def get_audit_template_by_id(self, context, audit_template_id):
        """Return an audit template.

        :param context: The security context
        :param audit_template_id: The id of an audit template.
        :returns: An audit template.
        :raises: :py:class:`~.AuditTemplateNotFound`
        """

    @abc.abstractmethod
    def get_audit_template_by_uuid(self, context, audit_template_uuid):
        """Return an audit template.

        :param context: The security context
        :param audit_template_uuid: The uuid of an audit template.
        :returns: An audit template.
        :raises: :py:class:`~.AuditTemplateNotFound`
        """

    def get_audit_template_by_name(self, context, audit_template_name):
        """Return an audit template.

        :param context: The security context
        :param audit_template_name: The name of an audit template.
        :returns: An audit template.
        :raises: :py:class:`~.AuditTemplateNotFound`
        """

    @abc.abstractmethod
    def destroy_audit_template(self, audit_template_id):
        """Destroy an audit_template.

        :param audit_template_id: The id or uuid of an audit template.
        :raises: :py:class:`~.AuditTemplateNotFound`
        """

    @abc.abstractmethod
    def update_audit_template(self, audit_template_id, values):
        """Update properties of an audit template.

        :param audit_template_id: The id or uuid of an audit template.
        :returns: An audit template.
        :raises: :py:class:`~.AuditTemplateNotFound`
        :raises: :py:class:`~.Invalid`
        """

    @abc.abstractmethod
    def soft_delete_audit_template(self, audit_template_id):
        """Soft delete an audit_template.

        :param audit_template_id: The id or uuid of an audit template.
        :raises: :py:class:`~.AuditTemplateNotFound`
        """

    @abc.abstractmethod
    def get_audit_list(self, context, filters=None, limit=None,
                       marker=None, sort_key=None, sort_dir=None):
        """Get specific columns for matching audits.

        Return a list of the specified columns for all audits that match the
        specified filters.

        :param context: The security context
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
        :raises: :py:class:`~.AuditAlreadyExists`
        """

    @abc.abstractmethod
    def get_audit_by_id(self, context, audit_id):
        """Return an audit.

        :param context: The security context
        :param audit_id: The id of an audit.
        :returns: An audit.
        :raises: :py:class:`~.AuditNotFound`
        """

    @abc.abstractmethod
    def get_audit_by_uuid(self, context, audit_uuid):
        """Return an audit.

        :param context: The security context
        :param audit_uuid: The uuid of an audit.
        :returns: An audit.
        :raises: :py:class:`~.AuditNotFound`
        """

    @abc.abstractmethod
    def destroy_audit(self, audit_id):
        """Destroy an audit and all associated action plans.

        :param audit_id: The id or uuid of an audit.
        :raises: :py:class:`~.AuditNotFound`
        """

    @abc.abstractmethod
    def update_audit(self, audit_id, values):
        """Update properties of an audit.

        :param audit_id: The id or uuid of an audit.
        :returns: An audit.
        :raises: :py:class:`~.AuditNotFound`
        :raises: :py:class:`~.Invalid`
        """

    def soft_delete_audit(self, audit_id):
        """Soft delete an audit and all associated action plans.

        :param audit_id: The id or uuid of an audit.
        :returns: An audit.
        :raises: :py:class:`~.AuditNotFound`
        """

    @abc.abstractmethod
    def get_action_list(self, context, filters=None, limit=None,
                        marker=None, sort_key=None, sort_dir=None):
        """Get specific columns for matching actions.

        Return a list of the specified columns for all actions that match the
        specified filters.

        :param context: The security context
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
        :raises: :py:class:`~.ActionAlreadyExists`
        """

    @abc.abstractmethod
    def get_action_by_id(self, context, action_id):
        """Return a action.

        :param context: The security context
        :param action_id: The id of a action.
        :returns: A action.
        :raises: :py:class:`~.ActionNotFound`
        """

    @abc.abstractmethod
    def get_action_by_uuid(self, context, action_uuid):
        """Return a action.

        :param context: The security context
        :param action_uuid: The uuid of a action.
        :returns: A action.
        :raises: :py:class:`~.ActionNotFound`
        """

    @abc.abstractmethod
    def destroy_action(self, action_id):
        """Destroy a action and all associated interfaces.

        :param action_id: The id or uuid of a action.
        :raises: :py:class:`~.ActionNotFound`
        :raises: :py:class:`~.ActionReferenced`
        """

    @abc.abstractmethod
    def update_action(self, action_id, values):
        """Update properties of a action.

        :param action_id: The id or uuid of a action.
        :returns: A action.
        :raises: :py:class:`~.ActionNotFound`
        :raises: :py:class:`~.ActionReferenced`
        :raises: :py:class:`~.Invalid`
        """

    @abc.abstractmethod
    def get_action_plan_list(
            self, context, filters=None, limit=None,
            marker=None, sort_key=None, sort_dir=None):
        """Get specific columns for matching action plans.

        Return a list of the specified columns for all action plans that
        match the specified filters.

        :param context: The security context
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
        :raises: :py:class:`~.ActionPlanAlreadyExists`
        """

    @abc.abstractmethod
    def get_action_plan_by_id(self, context, action_plan_id):
        """Return an action plan.

        :param context: The security context
        :param action_plan_id: The id of an action plan.
        :returns: An action plan.
        :raises: :py:class:`~.ActionPlanNotFound`
        """

    @abc.abstractmethod
    def get_action_plan_by_uuid(self, context, action_plan__uuid):
        """Return a action plan.

        :param context: The security context
        :param action_plan__uuid: The uuid of an action plan.
        :returns: An action plan.
        :raises: :py:class:`~.ActionPlanNotFound`
        """

    @abc.abstractmethod
    def destroy_action_plan(self, action_plan_id):
        """Destroy an action plan and all associated interfaces.

        :param action_plan_id: The id or uuid of a action plan.
        :raises: :py:class:`~.ActionPlanNotFound`
        :raises: :py:class:`~.ActionPlanReferenced`
        """

    @abc.abstractmethod
    def update_action_plan(self, action_plan_id, values):
        """Update properties of an action plan.

        :param action_plan_id: The id or uuid of an action plan.
        :returns: An action plan.
        :raises: :py:class:`~.ActionPlanNotFound`
        :raises: :py:class:`~.ActionPlanReferenced`
        :raises: :py:class:`~.Invalid`
        """

    @abc.abstractmethod
    def get_efficacy_indicator_list(self, context, filters=None, limit=None,
                                    marker=None, sort_key=None, sort_dir=None):
        """Get specific columns for matching efficacy indicators.

        Return a list of the specified columns for all efficacy indicators that
        match the specified filters.

        :param context: The security context
        :param columns: List of column names to return.
                        Defaults to 'id' column when columns == None.
        :param filters: Filters to apply. Defaults to None.

        :param limit: Maximum number of efficacy indicators to return.
        :param marker: The last item of the previous page; we return the next
                       result set.
        :param sort_key: Attribute by which results should be sorted.
        :param sort_dir: Direction in which results should be sorted.
                         (asc, desc)
        :returns: A list of tuples of the specified columns.
        """

    @abc.abstractmethod
    def create_efficacy_indicator(self, values):
        """Create a new efficacy indicator.

        :param values: A dict containing items used to identify
                       and track the efficacy indicator. For example:

                       ::

                        {
                         'id': 1,
                         'uuid': utils.generate_uuid(),
                         'name': 'my_efficacy_indicator',
                         'display_name': 'My efficacy indicator',
                         'goal_uuid': utils.generate_uuid(),
                        }
        :returns: An efficacy_indicator
        :raises: :py:class:`~.EfficacyIndicatorAlreadyExists`
        """

    @abc.abstractmethod
    def get_efficacy_indicator_by_id(self, context, efficacy_indicator_id):
        """Return an efficacy indicator given its ID.

        :param context: The security context
        :param efficacy_indicator_id: The ID of an efficacy indicator
        :returns: An efficacy indicator
        :raises: :py:class:`~.EfficacyIndicatorNotFound`
        """

    @abc.abstractmethod
    def get_efficacy_indicator_by_uuid(self, context, efficacy_indicator_uuid):
        """Return an efficacy indicator given its UUID.

        :param context: The security context
        :param efficacy_indicator_uuid: The UUID of an efficacy indicator
        :returns: An efficacy indicator
        :raises: :py:class:`~.EfficacyIndicatorNotFound`
        """

    @abc.abstractmethod
    def get_efficacy_indicator_by_name(self, context, efficacy_indicator_name):
        """Return an efficacy indicator given its name.

        :param context: The security context
        :param efficacy_indicator_name: The name of an efficacy indicator
        :returns: An efficacy indicator
        :raises: :py:class:`~.EfficacyIndicatorNotFound`
        """

    @abc.abstractmethod
    def destroy_efficacy_indicator(self, efficacy_indicator_uuid):
        """Destroy an efficacy indicator.

        :param efficacy_indicator_uuid: The UUID of an efficacy indicator
        :raises: :py:class:`~.EfficacyIndicatorNotFound`
        """

    @abc.abstractmethod
    def update_efficacy_indicator(self, efficacy_indicator_uuid, values):
        """Update properties of an efficacy indicator.

        :param efficacy_indicator_uuid: The UUID of an efficacy indicator
        :returns: An efficacy indicator
        :raises: :py:class:`~.EfficacyIndicatorNotFound`
        :raises: :py:class:`~.Invalid`
        """
