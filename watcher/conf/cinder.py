# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from keystoneauth1 import loading as ks_loading
from oslo_config import cfg


cinder = cfg.OptGroup(name='cinder', title='Options for Cinder integration')

CINDER_OPTS = []


def _deprecations():
    return {'region_name': [cfg.DeprecatedOpt('region_name', 'cinder_client')]}


def register_opts(conf):
    conf.register_group(cinder)
    conf.register_opts(CINDER_OPTS, group=cinder)
    ks_loading.register_adapter_conf_options(
        conf, cinder.name, deprecated_opts=_deprecations()
    )
    ks_loading.register_session_conf_options(conf, cinder.name)
    ks_loading.register_auth_conf_options(conf, cinder.name)


def list_opts():
    deprecated_opts = _deprecations()
    return [
        (
            cinder,
            CINDER_OPTS
            + ks_loading.get_adapter_conf_options(
                include_deprecated=False, deprecated_opts=deprecated_opts
            )
            + ks_loading.get_session_conf_options()
            + ks_loading.get_auth_common_conf_options(),
        )
    ]
