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


def _load_test_obj(context, cls, obj_data, **kw):
    # Let DB generate ID if it isn't specified explicitly
    if 'id' not in kw:
        del obj_data['id']
    obj = cls(context)
    for key in obj_data:
        setattr(obj, key, obj_data[key])
    return obj


def get_test_audit_template(context, **kw):
    """Return a AuditTemplate object with appropriate attributes.

    NOTE: The object leaves the attributes marked as changed, such
    that a create() could be used to commit it to the DB.
    """
    obj_cls = objects.AuditTemplate
    db_data = db_utils.get_test_audit_template(**kw)
    obj_data = _load_related_objects(context, obj_cls, db_data)

    return _load_test_obj(context, obj_cls, obj_data, **kw)


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
    obj_cls = objects.Audit
    db_data = db_utils.get_test_audit(**kw)
    obj_data = _load_related_objects(context, obj_cls, db_data)

    return _load_test_obj(context, obj_cls, obj_data, **kw)


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
    obj_cls = objects.ActionPlan
    db_data = db_utils.get_test_action_plan(**kw)
    obj_data = _load_related_objects(context, obj_cls, db_data)

    return _load_test_obj(context, obj_cls, obj_data, **kw)


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
    obj_cls = objects.Action
    db_data = db_utils.get_test_action(**kw)
    obj_data = _load_related_objects(context, obj_cls, db_data)

    return _load_test_obj(context, obj_cls, obj_data, **kw)


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
    obj_cls = objects.Goal
    db_data = db_utils.get_test_goal(**kw)
    obj_data = _load_related_objects(context, obj_cls, db_data)

    return _load_test_obj(context, obj_cls, obj_data, **kw)


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
    obj_cls = objects.ScoringEngine
    db_data = db_utils.get_test_scoring_engine(**kw)
    obj_data = _load_related_objects(context, obj_cls, db_data)

    return _load_test_obj(context, obj_cls, obj_data, **kw)


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
    obj_cls = objects.Service
    db_data = db_utils.get_test_service(**kw)
    obj_data = _load_related_objects(context, obj_cls, db_data)

    return _load_test_obj(context, obj_cls, obj_data, **kw)


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
    obj_cls = objects.Strategy
    db_data = db_utils.get_test_strategy(**kw)
    obj_data = _load_related_objects(context, obj_cls, db_data)

    return _load_test_obj(context, obj_cls, obj_data, **kw)


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
    obj_cls = objects.EfficacyIndicator
    db_data = db_utils.get_test_efficacy_indicator(**kw)
    obj_data = _load_related_objects(context, obj_cls, db_data)

    return _load_test_obj(context, obj_cls, obj_data, **kw)


def create_test_efficacy_indicator(context, **kw):
    """Create and return a test efficacy indicator object.

    Create a efficacy indicator in the DB and return a EfficacyIndicator object
    with appropriate attributes.
    """
    efficacy_indicator = get_test_efficacy_indicator(context, **kw)
    efficacy_indicator.create()
    return efficacy_indicator
