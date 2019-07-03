# -*- encoding: utf-8 -*-
# Copyright (c) 2016 Intel Corp
#
# Authors: Prudhvi Rao Shedimbi <prudhvi.rao.shedimbi@intel.com>
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

WATCHER_CLIENTS_AUTH = 'watcher_clients_auth'


def register_opts(conf):
    ka_loading.register_session_conf_options(conf, WATCHER_CLIENTS_AUTH)
    ka_loading.register_auth_conf_options(conf, WATCHER_CLIENTS_AUTH)


def list_opts():
    return [(WATCHER_CLIENTS_AUTH, ka_loading.get_session_conf_options() +
            ka_loading.get_auth_common_conf_options())]
