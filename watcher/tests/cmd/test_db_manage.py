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

import sys

import mock
from oslo_config import cfg

from watcher.cmd import dbmanage
from watcher.db import migration
from watcher.db import purge
from watcher.tests import base


class TestDBManageRunApp(base.TestCase):

    scenarios = (
        ("upgrade", {"command": "upgrade", "expected": "upgrade"}),
        ("downgrade", {"command": "downgrade", "expected": "downgrade"}),
        ("revision", {"command": "revision", "expected": "revision"}),
        ("stamp", {"command": "stamp", "expected": "stamp"}),
        ("version", {"command": "version", "expected": "version"}),
        ("create_schema", {"command": "create_schema",
                           "expected": "create_schema"}),
        ("purge", {"command": "purge", "expected": "purge"}),
        ("no_param", {"command": None, "expected": "upgrade"}),
    )

    @mock.patch.object(dbmanage, "register_sub_command_opts", mock.Mock())
    @mock.patch("watcher.cmd.dbmanage.service.prepare_service")
    @mock.patch("watcher.cmd.dbmanage.sys")
    def test_run_db_manage_app(self, m_sys, m_prepare_service):
        # Patch command function
        m_func = mock.Mock()
        cfg.CONF.register_opt(cfg.SubCommandOpt("command"))
        cfg.CONF.command.func = m_func

        # Only append if the command is not None
        m_sys.argv = list(filter(None, ["watcher-db-manage", self.command]))

        dbmanage.main()
        self.assertEqual(1, m_func.call_count)
        m_prepare_service.assert_called_once_with(
            ["watcher-db-manage", self.expected], cfg.CONF)


class TestDBManageRunCommand(base.TestCase):

    @mock.patch.object(migration, "upgrade")
    def test_run_db_upgrade(self, m_upgrade):
        cfg.CONF.register_opt(cfg.StrOpt("revision"), group="command")
        cfg.CONF.set_default("revision", "dummy", group="command")
        dbmanage.DBCommand.upgrade()

        m_upgrade.assert_called_once_with("dummy")

    @mock.patch.object(migration, "downgrade")
    def test_run_db_downgrade(self, m_downgrade):
        cfg.CONF.register_opt(cfg.StrOpt("revision"), group="command")
        cfg.CONF.set_default("revision", "dummy", group="command")
        dbmanage.DBCommand.downgrade()

        m_downgrade.assert_called_once_with("dummy")

    @mock.patch.object(migration, "revision")
    def test_run_db_revision(self, m_revision):
        cfg.CONF.register_opt(cfg.StrOpt("message"), group="command")
        cfg.CONF.register_opt(cfg.StrOpt("autogenerate"), group="command")
        cfg.CONF.set_default(
            "message", "dummy_message", group="command"
        )
        cfg.CONF.set_default(
            "autogenerate", "dummy_autogenerate", group="command"
        )
        dbmanage.DBCommand.revision()

        m_revision.assert_called_once_with(
            "dummy_message", "dummy_autogenerate"
        )

    @mock.patch.object(migration, "stamp")
    def test_run_db_stamp(self, m_stamp):
        cfg.CONF.register_opt(cfg.StrOpt("revision"), group="command")
        cfg.CONF.set_default("revision", "dummy", group="command")
        dbmanage.DBCommand.stamp()

    @mock.patch.object(migration, "version")
    def test_run_db_version(self, m_version):
        dbmanage.DBCommand.version()

        self.assertEqual(1, m_version.call_count)

    @mock.patch.object(purge, "PurgeCommand")
    def test_run_db_purge(self, m_purge_cls):
        m_purge = mock.Mock()
        m_purge_cls.return_value = m_purge
        m_purge_cls.get_goal_uuid.return_value = 'Some UUID'
        cfg.CONF.register_opt(cfg.IntOpt("age_in_days"), group="command")
        cfg.CONF.register_opt(cfg.IntOpt("max_number"), group="command")
        cfg.CONF.register_opt(cfg.StrOpt("goal"), group="command")
        cfg.CONF.register_opt(cfg.BoolOpt("exclude_orphans"), group="command")
        cfg.CONF.register_opt(cfg.BoolOpt("dry_run"), group="command")
        cfg.CONF.set_default("age_in_days", None, group="command")
        cfg.CONF.set_default("max_number", None, group="command")
        cfg.CONF.set_default("goal", None, group="command")
        cfg.CONF.set_default("exclude_orphans", True, group="command")
        cfg.CONF.set_default("dry_run", False, group="command")

        dbmanage.DBCommand.purge()

        m_purge_cls.assert_called_once_with(
            None, None, 'Some UUID', True, False)
        m_purge.execute.assert_called_once_with()

    @mock.patch.object(sys, "exit")
    @mock.patch.object(purge, "PurgeCommand")
    def test_run_db_purge_negative_max_number(self, m_purge_cls, m_exit):
        m_purge = mock.Mock()
        m_purge_cls.return_value = m_purge
        m_purge_cls.get_goal_uuid.return_value = 'Some UUID'
        cfg.CONF.register_opt(cfg.IntOpt("age_in_days"), group="command")
        cfg.CONF.register_opt(cfg.IntOpt("max_number"), group="command")
        cfg.CONF.register_opt(cfg.StrOpt("goal"), group="command")
        cfg.CONF.register_opt(cfg.BoolOpt("exclude_orphans"), group="command")
        cfg.CONF.register_opt(cfg.BoolOpt("dry_run"), group="command")
        cfg.CONF.set_default("age_in_days", None, group="command")
        cfg.CONF.set_default("max_number", -1, group="command")
        cfg.CONF.set_default("goal", None, group="command")
        cfg.CONF.set_default("exclude_orphans", True, group="command")
        cfg.CONF.set_default("dry_run", False, group="command")

        dbmanage.DBCommand.purge()

        self.assertEqual(0, m_purge_cls.call_count)
        self.assertEqual(0, m_purge.execute.call_count)
        self.assertEqual(0, m_purge.do_delete.call_count)
        self.assertEqual(1, m_exit.call_count)

    @mock.patch.object(sys, "exit")
    @mock.patch.object(purge, "PurgeCommand")
    def test_run_db_purge_dry_run(self, m_purge_cls, m_exit):
        m_purge = mock.Mock()
        m_purge_cls.return_value = m_purge
        m_purge_cls.get_goal_uuid.return_value = 'Some UUID'
        cfg.CONF.register_opt(cfg.IntOpt("age_in_days"), group="command")
        cfg.CONF.register_opt(cfg.IntOpt("max_number"), group="command")
        cfg.CONF.register_opt(cfg.StrOpt("goal"), group="command")
        cfg.CONF.register_opt(cfg.BoolOpt("exclude_orphans"), group="command")
        cfg.CONF.register_opt(cfg.BoolOpt("dry_run"), group="command")
        cfg.CONF.set_default("age_in_days", None, group="command")
        cfg.CONF.set_default("max_number", None, group="command")
        cfg.CONF.set_default("goal", None, group="command")
        cfg.CONF.set_default("exclude_orphans", True, group="command")
        cfg.CONF.set_default("dry_run", True, group="command")

        dbmanage.DBCommand.purge()

        m_purge_cls.assert_called_once_with(
            None, None, 'Some UUID', True, True)
        self.assertEqual(1, m_purge.execute.call_count)
        self.assertEqual(0, m_purge.do_delete.call_count)
        self.assertEqual(0, m_exit.call_count)
