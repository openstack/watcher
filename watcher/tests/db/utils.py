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
        'goal_id': kwargs.get('goal_id', 1),
        'strategy_id': kwargs.get('strategy_id', None),
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
        'audit_type': kwargs.get('audit_type', 'ONESHOT'),
        'state': kwargs.get('state'),
        'deadline': kwargs.get('deadline'),
        'audit_template_id': kwargs.get('audit_template_id', 1),
        'created_at': kwargs.get('created_at'),
        'updated_at': kwargs.get('updated_at'),
        'deleted_at': kwargs.get('deleted_at'),
        'parameters': kwargs.get('parameters', {}),
        'interval': kwargs.get('period', 3600),
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
        'action_type': kwargs.get('action_type', 'nop'),
        'input_parameters':
            kwargs.get('input_parameters',
                       {'key1': 'val1',
                        'key2': 'val2',
                        'resource_id':
                        '10a47dd1-4874-4298-91cf-eff046dbdb8d'}),
        'state': kwargs.get('state', 'PENDING'),
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
        'global_efficacy': kwargs.get('global_efficacy', {}),
        'first_action_id': kwargs.get('first_action_id', 1),
        'created_at': kwargs.get('created_at'),
        'updated_at': kwargs.get('updated_at'),
        'deleted_at': kwargs.get('deleted_at'),
    }


def create_test_action_plan(**kwargs):
    """Create test action plan entry in DB and return Action Plan DB object.

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


def get_test_goal(**kwargs):
    return {
        'id': kwargs.get('id', 1),
        'uuid': kwargs.get('uuid', 'f7ad87ae-4298-91cf-93a0-f35a852e3652'),
        'name': kwargs.get('name', 'TEST'),
        'display_name': kwargs.get('display_name', 'test goal'),
        'created_at': kwargs.get('created_at'),
        'updated_at': kwargs.get('updated_at'),
        'deleted_at': kwargs.get('deleted_at'),
        'efficacy_specification': kwargs.get('efficacy_specification', []),
    }


def create_test_goal(**kwargs):
    """Create test goal entry in DB and return Goal DB object.

    Function to be used to create test Goal objects in the database.
    :param kwargs: kwargs which override default goal values of its attributes.
    :returns: Test Goal DB object.
    """
    goal = get_test_goal(**kwargs)
    dbapi = db_api.get_instance()
    return dbapi.create_goal(goal)


def get_test_strategy(**kwargs):
    return {
        'id': kwargs.get('id', 1),
        'uuid': kwargs.get('uuid', 'cb3d0b58-4415-4d90-b75b-1e96878730e3'),
        'name': kwargs.get('name', 'TEST'),
        'display_name': kwargs.get('display_name', 'test strategy'),
        'goal_id': kwargs.get('goal_id', 1),
        'created_at': kwargs.get('created_at'),
        'updated_at': kwargs.get('updated_at'),
        'deleted_at': kwargs.get('deleted_at'),
        'parameters_spec': kwargs.get('parameters_spec', {})
    }


def create_test_strategy(**kwargs):
    """Create test strategy entry in DB and return Strategy DB object.

    Function to be used to create test Strategy objects in the database.
    :param kwargs: kwargs with overriding values for strategy's attributes.
    :returns: Test Strategy DB object.
    """
    strategy = get_test_strategy(**kwargs)
    dbapi = db_api.get_instance()
    return dbapi.create_strategy(strategy)


def get_test_efficacy_indicator(**kwargs):
    return {
        'id': kwargs.get('id', 1),
        'uuid': kwargs.get('uuid', '202cfcf9-811c-411a-8a35-d8351f64eb24'),
        'name': kwargs.get('name', 'test_indicator'),
        'description': kwargs.get('description', 'Test indicator'),
        'unit': kwargs.get('unit', '%'),
        'value': kwargs.get('value', 0),
        'action_plan_id': kwargs.get('action_plan_id', 1),
        'created_at': kwargs.get('created_at'),
        'updated_at': kwargs.get('updated_at'),
        'deleted_at': kwargs.get('deleted_at'),
    }


def create_test_efficacy_indicator(**kwargs):
    """Create and return a test efficacy indicator entry in DB.

    Function to be used to create test EfficacyIndicator objects in the DB.
    :param kwargs: kwargs for overriding the values of the attributes
    :returns: Test EfficacyIndicator DB object.
    """
    efficacy_indicator = get_test_efficacy_indicator(**kwargs)
    # Let DB generate ID if it isn't specified explicitly
    if 'id' not in kwargs:
        del efficacy_indicator['id']
    dbapi = db_api.get_instance()
    return dbapi.create_efficacy_indicator(efficacy_indicator)
