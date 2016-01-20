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

import watcher.api.app
from watcher.applier import manager as applier_manager
from watcher.common import clients
from watcher.decision_engine import manager as decision_engine_manger
from watcher.decision_engine.planner import manager as planner_manager
from watcher.decision_engine.strategy.selection import default \
    as strategy_selector


def list_opts():
    return [
        ('api', watcher.api.app.API_SERVICE_OPTS),
        ('watcher_goals', strategy_selector.WATCHER_GOALS_OPTS),
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
