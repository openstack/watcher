# -*- encoding: utf-8 -*-
# Copyright (c) 2016 b<>com
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

import json
import uuid

from watcher_tempest_plugin.services.infra_optim import base


class InfraOptimClientJSON(base.BaseInfraOptimClient):
    """Base Tempest REST client for Watcher API v1."""

    URI_PREFIX = 'v1'

    def serialize(self, object_dict):
        """Serialize an Watcher object."""
        return json.dumps(object_dict)

    def deserialize(self, object_str):
        """Deserialize an Watcher object."""
        return json.loads(object_str.decode('utf-8'))

    # ### AUDIT TEMPLATES ### #

    @base.handle_errors
    def list_audit_templates(self, **kwargs):
        """List all existing audit templates."""
        return self._list_request('audit_templates', **kwargs)

    @base.handle_errors
    def list_audit_templates_detail(self, **kwargs):
        """Lists details of all existing audit templates."""
        return self._list_request('/audit_templates/detail', **kwargs)

    @base.handle_errors
    def show_audit_template(self, audit_template_uuid):
        """Gets a specific audit template.

        :param audit_template_uuid: Unique identifier of the audit template
        :return: Serialized audit template as a dictionary.
        """
        return self._show_request('audit_templates', audit_template_uuid)

    @base.handle_errors
    def filter_audit_template_by_host_aggregate(self, host_aggregate):
        """Gets an audit template associated with given host agregate ID.

        :param host_aggregate: Unique identifier of the host aggregate
        :return: Serialized audit template as a dictionary.
        """
        return self._list_request('/audit_templates',
                                  host_aggregate=host_aggregate)

    @base.handle_errors
    def filter_audit_template_by_goal(self, goal):
        """Gets an audit template associated with given goal.

        :param goal: goal identifier
        :return: Serialized audit template as a dictionary.
        """
        return self._list_request('/audit_templates', goal=goal)

    @base.handle_errors
    def create_audit_template(self, **kwargs):
        """Creates an audit template with the specified parameters.

        :param name: The name of the audit template. Default: My Audit Template
        :param description: The description of the audit template.
            Default: AT Description
        :param goal: The goal associated within the audit template.
            Default: DUMMY
        :param host_aggregate: ID of the host aggregate targeted by
            this audit template. Default: 1
        :param extra: IMetadata associated to this audit template.
            Default: {}
        :return: A tuple with the server response and the created audit
            template.
        """

        parameters = {k: v for k, v in kwargs.items() if v is not None}
        # This name is unique to avoid the DB unique constraint on names
        unique_name = 'Tempest Audit Template %s' % uuid.uuid4()

        audit_template = {
            'name': parameters.get('name', unique_name),
            'description': parameters.get('description', ''),
            'goal': parameters.get('goal', 'DUMMY'),
            'host_aggregate': parameters.get('host_aggregate', 1),
            'extra': parameters.get('extra', {}),
        }

        return self._create_request('audit_templates', audit_template)

    @base.handle_errors
    def delete_audit_template(self, audit_template_uuid):
        """Deletes an audit template having the specified UUID.

        :param audit_template_uuid: The unique identifier of the audit template
        :return: A tuple with the server response and the response body.
        """

        return self._delete_request('audit_templates', audit_template_uuid)

    @base.handle_errors
    def update_audit_template(self, audit_template_uuid, patch):
        """Update the specified audit template.

        :param audit_template_uuid: The unique identifier of the audit template
        :param patch: List of dicts representing json patches.
        :return: A tuple with the server response and the updated audit
            template.
        """

        return self._patch_request('audit_templates',
                                   audit_template_uuid, patch)

    # ### AUDITS ### #

    @base.handle_errors
    def list_audits(self, **kwargs):
        """List all existing audit templates."""
        return self._list_request('audits', **kwargs)

    @base.handle_errors
    def list_audits_detail(self, **kwargs):
        """Lists details of all existing audit templates."""
        return self._list_request('/audits/detail', **kwargs)

    @base.handle_errors
    def list_audit_by_audit_template(self, audit_template_uuid):
        """Lists all audits associated with an audit template."""
        return self._list_request(
            '/audits', audit_template=audit_template_uuid)

    @base.handle_errors
    def show_audit(self, audit_uuid):
        """Gets a specific audit template.

        :param audit_uuid: Unique identifier of the audit template
        :return: Serialized audit template as a dictionary
        """
        return self._show_request('audits', audit_uuid)

    @base.handle_errors
    def create_audit(self, audit_template_uuid, **kwargs):
        """Create an audit with the specified parameters

        :param audit_template_uuid: Audit template ID used by the audit
        :return: A tuple with the server response and the created audit
        """
        audit = {'audit_template_uuid': audit_template_uuid}
        audit.update(kwargs)

        return self._create_request('audits', audit)

    @base.handle_errors
    def delete_audit(self, audit_uuid):
        """Deletes an audit having the specified UUID

        :param audit_uuid: The unique identifier of the audit
        :return: A tuple with the server response and the response body
        """

        return self._delete_request('audits', audit_uuid)

    @base.handle_errors
    def update_audit(self, audit_uuid, patch):
        """Update the specified audit.

        :param audit_uuid: The unique identifier of the audit
        :param patch: List of dicts representing json patches.
        :return: Tuple with the server response and the updated audit
        """

        return self._patch_request('audits', audit_uuid, patch)

    # ### ACTION PLANS ### #

    @base.handle_errors
    def list_action_plans(self, **kwargs):
        """List all existing action plan"""
        return self._list_request('action_plans', **kwargs)

    @base.handle_errors
    def list_action_plans_detail(self, **kwargs):
        """Lists details of all existing action plan"""
        return self._list_request('/action_plans/detail', **kwargs)

    @base.handle_errors
    def list_action_plan_by_audit(self, audit_uuid):
        """Lists all action plans associated with an audit"""
        return self._list_request('/action_plans', audit_uuid=audit_uuid)

    @base.handle_errors
    def show_action_plan(self, action_plan_uuid):
        """Gets a specific action plan

        :param action_plan_uuid: Unique identifier of the action plan
        :return: Serialized action plan as a dictionary
        """
        return self._show_request('/action_plans', action_plan_uuid)

    @base.handle_errors
    def delete_action_plan(self, action_plan_uuid):
        """Deletes an action_plan having the specified UUID

        :param action_plan_uuid: The unique identifier of the action_plan
        :return: A tuple with the server response and the response body
        """

        return self._delete_request('/action_plans', action_plan_uuid)

    @base.handle_errors
    def update_action_plan(self, action_plan_uuid, patch):
        """Update the specified action plan

        :param action_plan_uuid: The unique identifier of the action_plan
        :param patch: List of dicts representing json patches.
        :return: Tuple with the server response and the updated action_plan
        """

        return self._patch_request('/action_plans', action_plan_uuid, patch)

    # ### GOALS ### #

    @base.handle_errors
    def list_goals(self, **kwargs):
        """List all existing goals"""
        return self._list_request('/goals', **kwargs)

    @base.handle_errors
    def list_goals_detail(self, **kwargs):
        """Lists details of all existing goals"""
        return self._list_request('/goals/detail', **kwargs)

    @base.handle_errors
    def show_goal(self, goal):
        """Gets a specific goal

        :param goal: Name of the goal
        :return: Serialized goal as a dictionary
        """
        return self._show_request('/goals', goal)
