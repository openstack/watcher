# -*- encoding: utf-8 -*-
# Copyright (c) 2016 b<>com
#
# Authors: Vincent FRANCOISE <vincent.francoise@b-com.com>
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

import prettytable as ptable

from watcher.applier.loading import default as applier_loader
from watcher.common import utils
from watcher.decision_engine.loading import default as decision_engine_loader

PLUGIN_LOADERS = (
    applier_loader.DefaultActionLoader,
    decision_engine_loader.DefaultPlannerLoader,
    decision_engine_loader.DefaultScoringLoader,
    decision_engine_loader.DefaultScoringContainerLoader,
    decision_engine_loader.DefaultStrategyLoader,
    decision_engine_loader.ClusterDataModelCollectorLoader,
    applier_loader.DefaultWorkFlowEngineLoader,
)


def list_opts():
    """Load config options for all Watcher plugins"""
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
