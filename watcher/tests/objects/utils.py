# Copyright 2014 Rackspace Hosting
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
"""Watcher object test utilities."""

from watcher import objects
from watcher.tests.db import utils as db_utils


def _load_related_objects(context, cls, db_data):
    """Replace the DB data with its object counterpart"""
    obj_data = db_data.copy()
    for name, (obj_cls, _) in cls.object_fields.items():
        if obj_data.get(name):
            obj_data[name] = obj_cls(context, **obj_data.get(name).as_dict())
        else:
            del obj_data[name]

    return obj_data


def get_test_audit_template(context, **kw):
    """Return a AuditTemplate object with appropriate attributes.

    NOTE: The object leaves the attributes marked as changed, such
    that a create() could be used to commit it to the DB.
    """
    db_audit_template = db_utils.get_test_audit_template(**kw)
    # Let DB generate ID if it isn't specified explicitly
    if 'id' not in kw:
        del db_audit_template['id']
    audit_template = objects.AuditTemplate(context)
    for key in db_audit_template:
        setattr(audit_template, key, db_audit_template[key])

    return audit_template


def create_test_audit_template(context, **kw):
    """Create and return a test audit_template object.

    Create a audit template in the DB and return an AuditTemplate object
    with appropriate attributes.
    """
    audit_template = get_test_audit_template(context, **kw)
    audit_template.create()
    return audit_template


def get_test_audit(context, **kw):
    """Return a Audit object with appropriate attributes.

    NOTE: The object leaves the attributes marked as changed, such
    that a create() could be used to commit it to the DB.
    """
    db_audit = db_utils.get_test_audit(**kw)
    obj_data = _load_related_objects(context, objects.Audit, db_audit)

    # Let DB generate ID if it isn't specified explicitly
    if 'id' not in kw:
        del db_audit['id']
    audit = objects.Audit(context)
    for key in obj_data:
        setattr(audit, key, obj_data[key])
    return audit


def create_test_audit(context, **kw):
    """Create and return a test audit object.

    Create a audit in the DB and return an Audit object with appropriate
    attributes.
    """
    audit = get_test_audit(context, **kw)
    audit.create()
    return audit


def get_test_action_plan(context, **kw):
    """Return a ActionPlan object with appropriate attributes.

    NOTE: The object leaves the attributes marked as changed, such
    that a create() could be used to commit it to the DB.
    """
    db_action_plan = db_utils.get_test_action_plan(**kw)
    # Let DB generate ID if it isn't specified explicitly
    if 'id' not in kw:
        del db_action_plan['id']
    action_plan = objects.ActionPlan(context)
    for key in db_action_plan:
        setattr(action_plan, key, db_action_plan[key])
    return action_plan


def create_test_action_plan(context, **kw):
    """Create and return a test action_plan object.

    Create a action plan in the DB and return a ActionPlan object with
    appropriate attributes.
    """
    action_plan = get_test_action_plan(context, **kw)
    action_plan.create()
    return action_plan


def get_test_action(context, **kw):
    """Return a Action object with appropriate attributes.

    NOTE: The object leaves the attributes marked as changed, such
    that a create() could be used to commit it to the DB.
    """
    db_action = db_utils.get_test_action(**kw)
    # Let DB generate ID if it isn't specified explicitly
    if 'id' not in kw:
        del db_action['id']
    action = objects.Action(context)
    for key in db_action:
        setattr(action, key, db_action[key])
    return action


def create_test_action(context, **kw):
    """Create and return a test action object.

    Create a action in the DB and return a Action object with appropriate
    attributes.
    """
    action = get_test_action(context, **kw)
    action.create()
    return action


def get_test_goal(context, **kw):
    """Return a Goal object with appropriate attributes.

    NOTE: The object leaves the attributes marked as changed, such
    that a create() could be used to commit it to the DB.
    """
    db_goal = db_utils.get_test_goal(**kw)
    # Let DB generate ID if it isn't specified explicitly
    if 'id' not in kw:
        del db_goal['id']
    goal = objects.Goal(context)
    for key in db_goal:
        setattr(goal, key, db_goal[key])
    return goal


def create_test_goal(context, **kw):
    """Create and return a test goal object.

    Create a goal in the DB and return a Goal object with appropriate
    attributes.
    """
    goal = get_test_goal(context, **kw)
    goal.create()
    return goal


def get_test_scoring_engine(context, **kw):
    """Return a ScoringEngine object with appropriate attributes.

    NOTE: The object leaves the attributes marked as changed, such
    that a create() could be used to commit it to the DB.
    """
    db_scoring_engine = db_utils.get_test_scoring_engine(**kw)
    scoring_engine = objects.ScoringEngine(context)
    for key in db_scoring_engine:
        setattr(scoring_engine, key, db_scoring_engine[key])
    return scoring_engine


def create_test_scoring_engine(context, **kw):
    """Create and return a test scoring engine object.

    Create a scoring engine in the DB and return a ScoringEngine object with
    appropriate attributes.
    """
    scoring_engine = get_test_scoring_engine(context, **kw)
    scoring_engine.create()
    return scoring_engine


def get_test_service(context, **kw):
    """Return a Service object with appropriate attributes.

    NOTE: The object leaves the attributes marked as changed, such
    that a create() could be used to commit it to the DB.
    """
    db_service = db_utils.get_test_service(**kw)
    service = objects.Service(context)
    for key in db_service:
        if key == 'last_seen_up':
            db_service[key] = None
        setattr(service, key, db_service[key])
    return service


def create_test_service(context, **kw):
    """Create and return a test service object.

    Create a service in the DB and return a Service object with
    appropriate attributes.
    """
    service = get_test_service(context, **kw)
    service.create()
    return service


def get_test_strategy(context, **kw):
    """Return a Strategy object with appropriate attributes.

    NOTE: The object leaves the attributes marked as changed, such
    that a create() could be used to commit it to the DB.
    """
    db_strategy = db_utils.get_test_strategy(**kw)
    # Let DB generate ID if it isn't specified explicitly
    if 'id' not in kw:
        del db_strategy['id']
    strategy = objects.Strategy(context)
    for key in db_strategy:
        setattr(strategy, key, db_strategy[key])

    # ObjectField checks for the object type, so if we want to simulate a
    # non-eager object loading, the field should not be referenced at all.
    # Contrarily, eager loading need the data to be casted to the object type
    # that was specified by the ObjectField.
    if kw.get('goal'):
        strategy.goal = objects.Goal(context, **kw.get('goal'))

    return strategy


def create_test_strategy(context, **kw):
    """Create and return a test strategy object.

    Create a strategy in the DB and return a Strategy object with appropriate
    attributes.
    """
    strategy = get_test_strategy(context, **kw)
    strategy.create()
    return strategy


def get_test_efficacy_indicator(context, **kw):
    """Return a EfficacyIndicator object with appropriate attributes.

    NOTE: The object leaves the attributes marked as changed, such
    that a create() could be used to commit it to the DB.
    """
    db_efficacy_indicator = db_utils.get_test_efficacy_indicator(**kw)
    # Let DB generate ID if it isn't specified explicitly
    if 'id' not in kw:
        del db_efficacy_indicator['id']
    efficacy_indicator = objects.EfficacyIndicator(context)
    for key in db_efficacy_indicator:
        setattr(efficacy_indicator, key, db_efficacy_indicator[key])
    return efficacy_indicator


def create_test_efficacy_indicator(context, **kw):
    """Create and return a test efficacy indicator object.

    Create a efficacy indicator in the DB and return a EfficacyIndicator object
    with appropriate attributes.
    """
    efficacy_indicator = get_test_efficacy_indicator(context, **kw)
    efficacy_indicator.create()
    return efficacy_indicator
