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
"""Watcher test utilities."""

from oslo_utils import timeutils

from watcher.db import api as db_api
from watcher.db.sqlalchemy import models
from watcher import objects


def id_generator():
    id_ = 1
    while True:
        yield id_
        id_ += 1


def _load_relationships(model, db_data):
    rel_data = {}
    relationships = db_api.get_instance()._get_relationships(model)
    for name, relationship in relationships.items():
        related_model = relationship.argument
        if not db_data.get(name):
            rel_data[name] = None
        else:
            rel_data[name] = related_model(**db_data.get(name))

    return rel_data


def get_test_audit_template(**kwargs):
    audit_template_data = {
        'id': kwargs.get('id', 1),
        'uuid': kwargs.get('uuid', 'e74c40e0-d825-11e2-a28f-0800200c9a66'),
        'goal_id': kwargs.get('goal_id', 1),
        'strategy_id': kwargs.get('strategy_id', None),
        'name': kwargs.get('name', 'My Audit Template'),
        'description': kwargs.get('description', 'Desc. Of My Audit Template'),
        'scope': kwargs.get('scope', []),
        'created_at': kwargs.get('created_at'),
        'updated_at': kwargs.get('updated_at'),
        'deleted_at': kwargs.get('deleted_at'),
    }

    # ObjectField doesn't allow None nor dict, so if we want to simulate a
    # non-eager object loading, the field should not be referenced at all.
    audit_template_data.update(
        _load_relationships(models.AuditTemplate, kwargs))

    return audit_template_data


def create_test_audit_template(**kwargs):
    """Create test audit template entry in DB and return AuditTemplate DB object.

    Function to be used to create test AuditTemplate objects in the database.
    :param kwargs: kwargsargs with overriding values for audit template's
                   attributes.
    :returns: Test AuditTemplate DB object.
    """  # noqa: E501
    audit_template = get_test_audit_template(**kwargs)
    # Let DB generate ID if it isn't specified explicitly
    if 'id' not in kwargs:
        del audit_template['id']
    dbapi = db_api.get_instance()
    return dbapi.create_audit_template(audit_template)


def get_test_audit(**kwargs):
    audit_data = {
        'id': kwargs.get('id', 1),
        'uuid': kwargs.get('uuid', '10a47dd1-4874-4298-91cf-eff046dbdb8d'),
        'name': kwargs.get('name', 'My Audit'),
        'audit_type': kwargs.get('audit_type', 'ONESHOT'),
        'state': kwargs.get('state', objects.audit.State.PENDING),
        'created_at': kwargs.get('created_at'),
        'updated_at': kwargs.get('updated_at'),
        'deleted_at': kwargs.get('deleted_at'),
        'parameters': kwargs.get('parameters', {}),
        'interval': kwargs.get('interval', '3600'),
        'goal_id': kwargs.get('goal_id', 1),
        'strategy_id': kwargs.get('strategy_id', None),
        'scope': kwargs.get('scope', []),
        'auto_trigger': kwargs.get('auto_trigger', False),
        'next_run_time': kwargs.get('next_run_time'),
        'hostname': kwargs.get('hostname', 'host_1'),
        'start_time': kwargs.get('start_time'),
        'end_time': kwargs.get('end_time'),
        'force': kwargs.get('force', False)

    }
    # ObjectField doesn't allow None nor dict, so if we want to simulate a
    # non-eager object loading, the field should not be referenced at all.
    audit_data.update(_load_relationships(models.Audit, kwargs))

    return audit_data


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
    action_data = {
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
        'state': kwargs.get('state', objects.action_plan.State.PENDING),
        'parents': kwargs.get('parents', []),
        'created_at': kwargs.get('created_at'),
        'updated_at': kwargs.get('updated_at'),
        'deleted_at': kwargs.get('deleted_at'),
    }

    # ObjectField doesn't allow None nor dict, so if we want to simulate a
    # non-eager object loading, the field should not be referenced at all.
    action_data.update(_load_relationships(models.Action, kwargs))

    return action_data


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
    action_plan_data = {
        'id': kwargs.get('id', 1),
        'uuid': kwargs.get('uuid', '76be87bd-3422-43f9-93a0-e85a577e3061'),
        'state': kwargs.get('state', objects.action_plan.State.ONGOING),
        'audit_id': kwargs.get('audit_id', 1),
        'strategy_id': kwargs.get('strategy_id', 1),
        'global_efficacy': kwargs.get('global_efficacy', []),
        'created_at': kwargs.get('created_at'),
        'updated_at': kwargs.get('updated_at'),
        'deleted_at': kwargs.get('deleted_at'),
        'hostname': kwargs.get('hostname', 'host_1'),
    }

    # ObjectField doesn't allow None nor dict, so if we want to simulate a
    # non-eager object loading, the field should not be referenced at all.
    action_plan_data.update(_load_relationships(models.ActionPlan, kwargs))

    return action_plan_data


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


def get_test_scoring_engine(**kwargs):
    return {
        'id': kwargs.get('id', 1),
        'uuid': kwargs.get('uuid', 'e8370ede-4f39-11e6-9ffa-08002722cb21'),
        'name': kwargs.get('name', 'test-se-01'),
        'description': kwargs.get('description', 'test scoring engine 01'),
        'metainfo': kwargs.get('metainfo', 'test_attr=test_val'),
        'created_at': kwargs.get('created_at'),
        'updated_at': kwargs.get('updated_at'),
        'deleted_at': kwargs.get('deleted_at'),
    }


def create_test_scoring_engine(**kwargs):
    """Create test scoring engine in DB and return ScoringEngine DB object.

    Function to be used to create test ScoringEngine objects in the database.
    :param kwargs: kwargs with overriding values for SE'sattributes.
    :returns: Test ScoringEngine DB object.
    """
    scoring_engine = get_test_scoring_engine(**kwargs)
    dbapi = db_api.get_instance()
    return dbapi.create_scoring_engine(scoring_engine)


def get_test_strategy(**kwargs):
    strategy_data = {
        'id': kwargs.get('id', 1),
        'uuid': kwargs.get('uuid', 'cb3d0b58-4415-4d90-b75b-1e96878730e3'),
        'name': kwargs.get('name', 'TEST'),
        'display_name': kwargs.get('display_name', 'test strategy'),
        'goal_id': kwargs.get('goal_id', 1),
        'created_at': kwargs.get('created_at'),
        'updated_at': kwargs.get('updated_at'),
        'deleted_at': kwargs.get('deleted_at'),
        'parameters_spec': kwargs.get('parameters_spec', {}),
    }

    # ObjectField doesn't allow None nor dict, so if we want to simulate a
    # non-eager object loading, the field should not be referenced at all.
    strategy_data.update(_load_relationships(models.Strategy, kwargs))

    return strategy_data


def get_test_service(**kwargs):
    return {
        'id': kwargs.get('id', 1),
        'name': kwargs.get('name', 'watcher-service'),
        'host': kwargs.get('host', 'controller'),
        'last_seen_up': kwargs.get(
            'last_seen_up',
            timeutils.parse_isotime('2016-09-22T08:32:06').replace(tzinfo=None)
        ),
        'created_at': kwargs.get('created_at'),
        'updated_at': kwargs.get('updated_at'),
        'deleted_at': kwargs.get('deleted_at'),
    }


def create_test_service(**kwargs):
    """Create test service entry in DB and return Service DB object.

    Function to be used to create test Service objects in the database.
    :param kwargs: kwargs with overriding values for service's attributes.
    :returns: Test Service DB object.
    """
    service = get_test_service(**kwargs)
    dbapi = db_api.get_instance()
    return dbapi.create_service(service)


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


def get_test_action_desc(**kwargs):
    return {
        'id': kwargs.get('id', 1),
        'action_type': kwargs.get('action_type', 'nop'),
        'description': kwargs.get('description', 'Logging a NOP message'),
        'created_at': kwargs.get('created_at'),
        'updated_at': kwargs.get('updated_at'),
        'deleted_at': kwargs.get('deleted_at'),
    }


def create_test_action_desc(**kwargs):
    """Create test action description entry in DB and return ActionDescription.

    Function to be used to create test ActionDescription objects in the DB.
    :param kwargs: kwargs with overriding values for service's attributes.
    :returns: Test ActionDescription DB object.
    """
    action_desc = get_test_action_desc(**kwargs)
    dbapi = db_api.get_instance()
    return dbapi.create_action_description(action_desc)
