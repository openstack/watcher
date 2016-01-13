# -*- encoding: utf-8 -*-
# Copyright (c) 2015 b<>com
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

from mock import Mock
from mock import patch
from oslo_config import cfg
from watcher.cmd import dbmanage
from watcher.db import migration
from watcher.tests.base import TestCase


class TestDBManageRunApp(TestCase):

    scenarios = (
        ("upgrade", {"command": "upgrade", "expected": "upgrade"}),
        ("downgrade", {"command": "downgrade", "expected": "downgrade"}),
        ("revision", {"command": "revision", "expected": "revision"}),
        ("stamp", {"command": "stamp", "expected": "stamp"}),
        ("version", {"command": "version", "expected": "version"}),
        ("create_schema", {"command": "create_schema",
                           "expected": "create_schema"}),
        ("no_param", {"command": None, "expected": "upgrade"}),
    )

    @patch.object(dbmanage, "register_sub_command_opts", Mock())
    @patch("watcher.cmd.dbmanage.service.prepare_service")
    @patch("watcher.cmd.dbmanage.sys")
    def test_run_db_manage_app(self, m_sys, m_prepare_service):
        # Patch command function
        m_func = Mock()
        cfg.CONF.register_opt(cfg.SubCommandOpt("command"))
        cfg.CONF.command.func = m_func

        # Only append if the command is not None
        m_sys.argv = list(filter(None, ["watcher-db-manage", self.command]))

        dbmanage.main()
        self.assertEqual(m_func.call_count, 1)
        m_prepare_service.assert_called_once_with(
            ["watcher-db-manage", self.expected])


class TestDBManageRunCommand(TestCase):

    @patch.object(migration, "upgrade")
    def test_run_db_upgrade(self, m_upgrade):
        cfg.CONF.register_opt(cfg.StrOpt("revision"), group="command")
        cfg.CONF.set_default("revision", "dummy", group="command")
        dbmanage.DBCommand.upgrade()

        m_upgrade.assert_called_once_with("dummy")

    @patch.object(migration, "downgrade")
    def test_run_db_downgrade(self, m_downgrade):
        cfg.CONF.register_opt(cfg.StrOpt("revision"), group="command")
        cfg.CONF.set_default("revision", "dummy", group="command")
        dbmanage.DBCommand.downgrade()

        m_downgrade.assert_called_once_with("dummy")

    @patch.object(migration, "revision")
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

    @patch.object(migration, "stamp")
    def test_run_db_stamp(self, m_stamp):
        cfg.CONF.register_opt(cfg.StrOpt("revision"), group="command")
        cfg.CONF.set_default("revision", "dummy", group="command")
        dbmanage.DBCommand.stamp()

    @patch.object(migration, "version")
    def test_run_db_version(self, m_version):
        dbmanage.DBCommand.version()

        self.assertEqual(m_version.call_count, 1)
