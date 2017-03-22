# -*- encoding: utf-8 -*-
# Copyright (c) 2016 b<>com
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
#

from __future__ import print_function

import collections
import datetime
import itertools
import sys

from oslo_log import log
from oslo_utils import strutils
import prettytable as ptable
from six.moves import input

from watcher._i18n import _
from watcher._i18n import lazy_translation_enabled
from watcher.common import context
from watcher.common import exception
from watcher.common import utils
from watcher import objects

LOG = log.getLogger(__name__)


class WatcherObjectsMap(object):
    """Wrapper to deal with watcher objects per type

    This wrapper object contains a list of watcher objects per type.
    Its main use is to simplify the merge of watcher objects by avoiding
    duplicates, but also for representing the relationships between these
    objects.
    """

    # This is for generating the .pot translations
    keymap = collections.OrderedDict([
        ("goals", _("Goals")),
        ("strategies", _("Strategies")),
        ("audit_templates", _("Audit Templates")),
        ("audits", _("Audits")),
        ("action_plans", _("Action Plans")),
        ("actions", _("Actions")),
    ])

    def __init__(self):
        for attr_name in self.keys():
            setattr(self, attr_name, [])

    def values(self):
        return (getattr(self, key) for key in self.keys())

    @classmethod
    def keys(cls):
        return cls.keymap.keys()

    def __iter__(self):
        return itertools.chain(*self.values())

    def __add__(self, other):
        new_map = self.__class__()

        # Merge the 2 items dicts into a new object (and avoid dupes)
        for attr_name, initials, others in zip(self.keys(), self.values(),
                                               other.values()):
            # Creates a copy
            merged = initials[:]
            initials_ids = [item.id for item in initials]
            non_dupes = [item for item in others
                         if item.id not in initials_ids]
            merged += non_dupes

            setattr(new_map, attr_name, merged)

        return new_map

    def __str__(self):
        out = ""
        for key, vals in zip(self.keys(), self.values()):
            ids = [val.id for val in vals]
            out += "%(key)s: %(val)s" % (dict(key=key, val=ids))
            out += "\n"
        return out

    def __len__(self):
        return sum(len(getattr(self, key)) for key in self.keys())

    def get_count_table(self):
        headers = list(self.keymap.values())
        headers.append(_("Total"))  # We also add a total count
        translated_headers = [
            h.translate() if lazy_translation_enabled() else h
            for h in headers
        ]

        counters = [len(cat_vals) for cat_vals in self.values()] + [len(self)]
        table = ptable.PrettyTable(field_names=translated_headers)
        table.add_row(counters)
        return table.get_string()


class PurgeCommand(object):
    """Purges the DB by removing soft deleted entries

    The workflow for this purge is the following:

    # Find soft deleted objects which are expired
    # Find orphan objects
    # Find their related objects whether they are expired or not
    # Merge them together
    # If it does not exceed the limit, destroy them all
    """

    ctx = context.make_context(show_deleted=True)

    def __init__(self, age_in_days=None, max_number=None,
                 uuid=None, exclude_orphans=False, dry_run=None):
        self.age_in_days = age_in_days
        self.max_number = max_number
        self.uuid = uuid
        self.exclude_orphans = exclude_orphans
        self.dry_run = dry_run

        self._delete_up_to_max = None
        self._objects_map = WatcherObjectsMap()

    def get_expiry_date(self):
        if not self.age_in_days:
            return None
        today = datetime.datetime.today()
        expiry_date = today - datetime.timedelta(days=self.age_in_days)
        return expiry_date

    @classmethod
    def get_goal_uuid(cls, uuid_or_name):
        if uuid_or_name is None:
            return

        query_func = None
        if not utils.is_uuid_like(uuid_or_name):
            query_func = objects.Goal.get_by_name
        else:
            query_func = objects.Goal.get_by_uuid

        try:
            goal = query_func(cls.ctx, uuid_or_name)
        except Exception as exc:
            LOG.exception(exc)
            raise exception.GoalNotFound(goal=uuid_or_name)

        if not goal.deleted_at:
            raise exception.NotSoftDeletedStateError(
                name=_('Goal'), id=uuid_or_name)

        return goal.uuid

    def _find_goals(self, filters=None):
        return objects.Goal.list(self.ctx, filters=filters)

    def _find_strategies(self, filters=None):
        return objects.Strategy.list(self.ctx, filters=filters)

    def _find_audit_templates(self, filters=None):
        return objects.AuditTemplate.list(self.ctx, filters=filters)

    def _find_audits(self, filters=None):
        return objects.Audit.list(self.ctx, filters=filters)

    def _find_action_plans(self, filters=None):
        return objects.ActionPlan.list(self.ctx, filters=filters)

    def _find_actions(self, filters=None):
        return objects.Action.list(self.ctx, filters=filters)

    def _find_orphans(self):
        orphans = WatcherObjectsMap()

        filters = dict(deleted=False)
        goals = objects.Goal.list(self.ctx, filters=filters)
        strategies = objects.Strategy.list(self.ctx, filters=filters)
        audit_templates = objects.AuditTemplate.list(self.ctx, filters=filters)
        audits = objects.Audit.list(self.ctx, filters=filters)
        action_plans = objects.ActionPlan.list(self.ctx, filters=filters)
        actions = objects.Action.list(self.ctx, filters=filters)

        goal_ids = set(g.id for g in goals)
        orphans.strategies = [
            strategy for strategy in strategies
            if strategy.goal_id not in goal_ids]

        strategy_ids = [s.id for s in (s for s in strategies
                                       if s not in orphans.strategies)]
        orphans.audit_templates = [
            audit_template for audit_template in audit_templates
            if audit_template.goal_id not in goal_ids or
            (audit_template.strategy_id and
             audit_template.strategy_id not in strategy_ids)]

        orphans.audits = [
            audit for audit in audits
            if audit.goal_id not in goal_ids or
            (audit.strategy_id and
             audit.strategy_id not in strategy_ids)]

        # Objects with orphan parents are themselves orphans
        audit_ids = [audit.id for audit in audits
                     if audit not in orphans.audits]
        orphans.action_plans = [
            ap for ap in action_plans
            if ap.audit_id not in audit_ids or
            ap.strategy_id not in strategy_ids]

        # Objects with orphan parents are themselves orphans
        action_plan_ids = [ap.id for ap in action_plans
                           if ap not in orphans.action_plans]
        orphans.actions = [
            action for action in actions
            if action.action_plan_id not in action_plan_ids]

        LOG.debug("Orphans found:\n%s", orphans)
        LOG.info("Orphans found:\n%s", orphans.get_count_table())

        return orphans

    def _find_soft_deleted_objects(self):
        to_be_deleted = WatcherObjectsMap()
        expiry_date = self.get_expiry_date()
        filters = dict(deleted=True)

        if self.uuid:
            filters["uuid"] = self.uuid
        if expiry_date:
            filters.update(dict(deleted_at__lt=expiry_date))

        to_be_deleted.goals.extend(self._find_goals(filters))
        to_be_deleted.strategies.extend(self._find_strategies(filters))
        to_be_deleted.audit_templates.extend(
            self._find_audit_templates(filters))
        to_be_deleted.audits.extend(self._find_audits(filters))
        to_be_deleted.action_plans.extend(
            self._find_action_plans(filters))
        to_be_deleted.actions.extend(self._find_actions(filters))

        soft_deleted_objs = self._find_related_objects(
            to_be_deleted, base_filters=dict(deleted=True))

        LOG.debug("Soft deleted objects:\n%s", soft_deleted_objs)

        return soft_deleted_objs

    def _find_related_objects(self, objects_map, base_filters=None):
        base_filters = base_filters or {}

        for goal in objects_map.goals:
            filters = {}
            filters.update(base_filters)
            filters.update(dict(goal_id=goal.id))
            related_objs = WatcherObjectsMap()
            related_objs.strategies = self._find_strategies(filters)
            related_objs.audit_templates = self._find_audit_templates(filters)
            related_objs.audits = self._find_audits(filters)
            objects_map += related_objs

        for strategy in objects_map.strategies:
            filters = {}
            filters.update(base_filters)
            filters.update(dict(strategy_id=strategy.id))
            related_objs = WatcherObjectsMap()
            related_objs.audit_templates = self._find_audit_templates(filters)
            related_objs.audits = self._find_audits(filters)
            objects_map += related_objs

        for audit in objects_map.audits:
            filters = {}
            filters.update(base_filters)
            filters.update(dict(audit_id=audit.id))
            related_objs = WatcherObjectsMap()
            related_objs.action_plans = self._find_action_plans(filters)
            objects_map += related_objs

        for action_plan in objects_map.action_plans:
            filters = {}
            filters.update(base_filters)
            filters.update(dict(action_plan_id=action_plan.id))
            related_objs = WatcherObjectsMap()
            related_objs.actions = self._find_actions(filters)
            objects_map += related_objs

        return objects_map

    def confirmation_prompt(self):
        print(self._objects_map.get_count_table())
        raw_val = input(
            _("There are %(count)d objects set for deletion. "
              "Continue? [y/N]") % dict(count=len(self._objects_map)))

        return strutils.bool_from_string(raw_val)

    def delete_up_to_max_prompt(self, objects_map):
        print(objects_map.get_count_table())
        print(_("The number of objects (%(num)s) to delete from the database "
                "exceeds the maximum number of objects (%(max_number)s) "
                "specified.") % dict(max_number=self.max_number,
                                     num=len(objects_map)))
        raw_val = input(
            _("Do you want to delete objects up to the specified maximum "
              "number? [y/N]"))

        self._delete_up_to_max = strutils.bool_from_string(raw_val)

        return self._delete_up_to_max

    def _aggregate_objects(self):
        """Objects aggregated on a 'per goal' basis"""
        # todo: aggregate orphans as well
        aggregate = []
        for goal in self._objects_map.goals:
            related_objs = WatcherObjectsMap()

            # goals
            related_objs.goals = [goal]

            # strategies
            goal_ids = [goal.id]
            related_objs.strategies = [
                strategy for strategy in self._objects_map.strategies
                if strategy.goal_id in goal_ids
            ]

            # audit templates
            strategy_ids = [
                strategy.id for strategy in related_objs.strategies]
            related_objs.audit_templates = [
                at for at in self._objects_map.audit_templates
                if at.goal_id in goal_ids or
                (at.strategy_id and at.strategy_id in strategy_ids)
            ]

            # audits
            related_objs.audits = [
                audit for audit in self._objects_map.audits
                if audit.goal_id in goal_ids
            ]

            # action plans
            audit_ids = [audit.id for audit in related_objs.audits]
            related_objs.action_plans = [
                action_plan for action_plan in self._objects_map.action_plans
                if action_plan.audit_id in audit_ids
            ]

            # actions
            action_plan_ids = [
                action_plan.id for action_plan in related_objs.action_plans
            ]
            related_objs.actions = [
                action for action in self._objects_map.actions
                if action.action_plan_id in action_plan_ids
            ]
            aggregate.append(related_objs)

        return aggregate

    def _get_objects_up_to_limit(self):
        aggregated_objects = self._aggregate_objects()
        to_be_deleted_subset = WatcherObjectsMap()

        for aggregate in aggregated_objects:
            if len(aggregate) + len(to_be_deleted_subset) <= self.max_number:
                to_be_deleted_subset += aggregate
            else:
                break

        LOG.debug(to_be_deleted_subset)
        return to_be_deleted_subset

    def find_objects_to_delete(self):
        """Finds all the objects to be purged

        :returns: A mapping with all the Watcher objects to purged
        :rtype: :py:class:`~.WatcherObjectsMap` instance
        """
        to_be_deleted = self._find_soft_deleted_objects()

        if not self.exclude_orphans:
            to_be_deleted += self._find_orphans()

        LOG.debug("Objects to be deleted:\n%s", to_be_deleted)

        return to_be_deleted

    def do_delete(self):
        LOG.info("Deleting...")
        # Reversed to avoid errors with foreign keys
        for entry in reversed(list(self._objects_map)):
            entry.destroy()

    def execute(self):
        LOG.info("Starting purge command")
        self._objects_map = self.find_objects_to_delete()

        if (self.max_number is not None and
                len(self._objects_map) > self.max_number):
            if self.delete_up_to_max_prompt(self._objects_map):
                self._objects_map = self._get_objects_up_to_limit()
            else:
                return

        _orphans_note = (_(" (orphans excluded)") if self.exclude_orphans
                         else _(" (may include orphans)"))
        if not self.dry_run and self.confirmation_prompt():
            self.do_delete()
            print(_("Purge results summary%s:") % _orphans_note)
            LOG.info("Purge results summary%s:", _orphans_note)
        else:
            LOG.debug(self._objects_map)
            print(_("Here below is a table containing the objects "
                    "that can be purged%s:") % _orphans_note)

        LOG.info("\n%s", self._objects_map.get_count_table())
        print(self._objects_map.get_count_table())
        LOG.info("Purge process completed")


def purge(age_in_days, max_number, goal, exclude_orphans, dry_run):
    """Removes soft deleted objects from the database

    :param age_in_days: Number of days since deletion (from today)
        to exclude from the purge. If None, everything will be purged.
    :type age_in_days: int
    :param max_number: Max number of objects expected to be deleted.
                  Prevents the deletion if exceeded. No limit if set to None.
    :type max_number: int
    :param goal: UUID or name of the goal to purge.
    :type goal: str
    :param exclude_orphans: Flag to indicate whether or not you want to
                            exclude orphans from deletion (default: False).
    :type exclude_orphans: bool
    :param dry_run: Flag to indicate whether or not you want to perform
                    a dry run (no deletion).
    :type dry_run: bool
    """
    try:
        if max_number and max_number < 0:
            raise exception.NegativeLimitError

        LOG.info("[options] age_in_days = %s", age_in_days)
        LOG.info("[options] max_number = %s", max_number)
        LOG.info("[options] goal = %s", goal)
        LOG.info("[options] exclude_orphans = %s", exclude_orphans)
        LOG.info("[options] dry_run = %s", dry_run)

        uuid = PurgeCommand.get_goal_uuid(goal)

        cmd = PurgeCommand(age_in_days, max_number, uuid,
                           exclude_orphans, dry_run)

        cmd.execute()

    except Exception as exc:
        LOG.exception(exc)
        print(exc)
        sys.exit(1)
