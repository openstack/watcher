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

from oslo_config import cfg

ceilometer_client = cfg.OptGroup(name='ceilometer_client',
                                 title='Configuration Options for Ceilometer')

CEILOMETER_CLIENT_OPTS = [
    cfg.StrOpt('api_version',
               default='2',
               deprecated_for_removal=True,
               deprecated_since="1.13.0",
               deprecated_reason="""
               Ceilometer API is deprecated since Ocata release.
               Any related configuration options are deprecated too.
               """,
               help='Version of Ceilometer API to use in '
                    'ceilometerclient.'),
    cfg.StrOpt('endpoint_type',
               default='internalURL',
               deprecated_for_removal=True,
               deprecated_since="1.13.0",
               deprecated_reason="""
               Ceilometer API is deprecated since Ocata release.
               Any related configuration options are deprecated too.
               """,
               help='Type of endpoint to use in ceilometerclient. '
                    'Supported values: internalURL, publicURL, adminURL. '
                    'The default is internalURL.'),
    cfg.StrOpt('region_name',
               deprecated_for_removal=True,
               deprecated_since="1.13.0",
               deprecated_reason="""
               Ceilometer API is deprecated since Ocata release.
               Any related configuration options are deprecated too.
               """,
               help='Region in Identity service catalog to use for '
                    'communication with the OpenStack service.')]


def register_opts(conf):
    conf.register_group(ceilometer_client)
    conf.register_opts(CEILOMETER_CLIENT_OPTS, group=ceilometer_client)


def list_opts():
    return [(ceilometer_client, CEILOMETER_CLIENT_OPTS)]
