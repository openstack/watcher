# -*- encoding: utf-8 -*-
# Copyright 2014
# The Cloudscaling Group, Inc.
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

from keystoneauth1 import loading as ka_loading
import prettytable as ptable

import watcher.api.app
from watcher.applier.loading import default as applier_loader
from watcher.applier import manager as applier_manager
from watcher.common import clients
from watcher.common import utils
from watcher.decision_engine.loading import default as decision_engine_loader
from watcher.decision_engine import manager as decision_engine_manger
from watcher.decision_engine.planner import manager as planner_manager


PLUGIN_LOADERS = (
    applier_loader.DefaultActionLoader,
    decision_engine_loader.DefaultPlannerLoader,
    decision_engine_loader.DefaultStrategyLoader,
    applier_loader.DefaultWorkFlowEngineLoader,
)


def list_opts():
    watcher_opts = [
        ('api', watcher.api.app.API_SERVICE_OPTS),
        ('watcher_decision_engine',
         decision_engine_manger.WATCHER_DECISION_ENGINE_OPTS),
        ('watcher_applier', applier_manager.APPLIER_MANAGER_OPTS),
        ('watcher_planner', planner_manager.WATCHER_PLANNER_OPTS),
        ('nova_client', clients.NOVA_CLIENT_OPTS),
        ('glance_client', clients.GLANCE_CLIENT_OPTS),
        ('cinder_client', clients.CINDER_CLIENT_OPTS),
        ('ceilometer_client', clients.CEILOMETER_CLIENT_OPTS),
        ('neutron_client', clients.NEUTRON_CLIENT_OPTS),
        ('watcher_clients_auth',
         (ka_loading.get_auth_common_conf_options() +
          ka_loading.get_auth_plugin_conf_options('password') +
          ka_loading.get_session_conf_options()))
    ]

    watcher_opts += list_plugin_opts()

    return watcher_opts


def list_plugin_opts():
    plugins_opts = []
    for plugin_loader_cls in PLUGIN_LOADERS:
        plugin_loader = plugin_loader_cls()
        plugins_map = plugin_loader.list_available()

        for plugin_name, plugin_cls in plugins_map.items():
            plugin_opts = plugin_cls.get_config_opts()
            if plugin_opts:
                plugins_opts.append(
                    (plugin_loader.get_entry_name(plugin_name), plugin_opts))

    return plugins_opts


def _show_plugins_ascii_table(rows):
    headers = ["Namespace", "Plugin name", "Import path"]
    table = ptable.PrettyTable(field_names=headers)
    for row in rows:
        table.add_row(row)
    return table.get_string()


def show_plugins():
    rows = []
    for plugin_loader_cls in PLUGIN_LOADERS:
        plugin_loader = plugin_loader_cls()
        plugins_map = plugin_loader.list_available()

        rows += [
            (plugin_loader.get_entry_name(plugin_name),
             plugin_name,
             utils.get_cls_import_path(plugin_cls))
            for plugin_name, plugin_cls in plugins_map.items()]

    return _show_plugins_ascii_table(rows)
