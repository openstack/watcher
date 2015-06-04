# Copyright 2015 OpenStack Foundation
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
"""Magnum test utilities."""

from watcher.db import api as db_api


def get_test_audit_template(**kwargs):
    return {
        'id': kwargs.get('id', 1),
        'uuid': kwargs.get('uuid', 'e74c40e0-d825-11e2-a28f-0800200c9a66'),
        'goal': kwargs.get('goal', 'SERVERS_CONSOLIDATION'),
        'name': kwargs.get('name', 'My Audit Template'),
        'description': kwargs.get('description', 'Desc. Of My Audit Template'),
        'extra': kwargs.get('extra', {'automatic': False}),
        'host_aggregate': kwargs.get('host_aggregate', 1),
        'version': kwargs.get('version', 'v1'),
        'created_at': kwargs.get('created_at'),
        'updated_at': kwargs.get('updated_at'),
        'deleted_at': kwargs.get('deleted_at'),
    }


def create_test_audit_template(**kwargs):
    """Create test audit template entry in DB and return AuditTemplate DB object.

    Function to be used to create test AuditTemplate objects in the database.
    :param kwargs: kwargsargs with overriding values for audit template's
                   attributes.
    :returns: Test AuditTemplate DB object.
    """
    audit_template = get_test_audit_template(**kwargs)
    # Let DB generate ID if it isn't specified explicitly
    if 'id' not in kwargs:
        del audit_template['id']
    dbapi = db_api.get_instance()
    return dbapi.create_audit_template(audit_template)


def get_test_audit(**kwargs):
    return {
        'id': kwargs.get('id', 1),
        'uuid': kwargs.get('uuid', '10a47dd1-4874-4298-91cf-eff046dbdb8d'),
        'type': kwargs.get('type', 'ONESHOT'),
        'state': kwargs.get('state'),
        'deadline': kwargs.get('deadline'),
        'audit_template_id': kwargs.get('audit_template_id', 1),
        'created_at': kwargs.get('created_at'),
        'updated_at': kwargs.get('updated_at'),
        'deleted_at': kwargs.get('deleted_at'),
    }


def create_test_audit(**kwargs):
    """Create test audit entry in DB and return Audit DB object.

    Function to be used to create test Audit objects in the database.
    :param kwargs: kwargsargs with overriding values for audit's attributes.
    :returns: Test Audit DB object.
    """
    audit = get_test_audit(**kwargs)
    # Let DB generate ID if it isn't specified explicitly
    if 'id' not in kwargs:
        del audit['id']
    dbapi = db_api.get_instance()
    return dbapi.create_audit(audit)


def get_test_action(**kwargs):
    return {
        'id': kwargs.get('id', 1),
        'uuid': kwargs.get('uuid', '10a47dd1-4874-4298-91cf-eff046dbdb8d'),
        'action_plan_id': kwargs.get('action_plan_id', 1),
        'action_type': kwargs.get('action_type', 'COLD_MIGRATION'),
        'applies_to': kwargs.get('applies_to',
                                 '10a47dd1-4874-4298-91cf-eff046dbdb8d'),
        'src': kwargs.get('src', 'rdev-indeedsrv002'),
        'dst': kwargs.get('dst', 'rdev-indeedsrv001'),
        'parameter': kwargs.get('parameter', ''),
        'description': kwargs.get('description', 'Desc. Of The Action'),
        'state': kwargs.get('state', 'PENDING'),
        'alarm': kwargs.get('alarm', None),
        'next': kwargs.get('next', 2),

        'created_at': kwargs.get('created_at'),
        'updated_at': kwargs.get('updated_at'),
        'deleted_at': kwargs.get('deleted_at'),
    }


def create_test_action(**kwargs):
    """Create test action entry in DB and return Action DB object.

    Function to be used to create test Action objects in the database.
    :param kwargs: kwargsargs with overriding values for action's attributes.
    :returns: Test Action DB object.
    """
    action = get_test_action(**kwargs)
    # Let DB generate ID if it isn't specified explicitly
    if 'id' not in kwargs:
        del action['id']
    dbapi = db_api.get_instance()
    return dbapi.create_action(action)


def get_test_action_plan(**kwargs):
    return {
        'id': kwargs.get('id', 1),
        'uuid': kwargs.get('uuid', '76be87bd-3422-43f9-93a0-e85a577e3061'),
        'state': kwargs.get('state', 'ONGOING'),
        'audit_id': kwargs.get('audit_id', 1),
        'first_action_id': kwargs.get('first_action_id', 1),
        'created_at': kwargs.get('created_at'),
        'updated_at': kwargs.get('updated_at'),
        'deleted_at': kwargs.get('deleted_at'),
    }


def create_test_action_plan(**kwargs):
    """Create test action plan entry in DB and return Action DB object.

    Function to be used to create test Action objects in the database.
    :param kwargs: kwargsargs with overriding values for action's attributes.
    :returns: Test Action DB object.
    """
    action = get_test_action_plan(**kwargs)
    # Let DB generate ID if it isn't specified explicitly
    if 'id' not in kwargs:
        del action['id']
    dbapi = db_api.get_instance()
    return dbapi.create_action_plan(action)
