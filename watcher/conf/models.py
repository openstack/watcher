# Copyright 2025 Red Hat, Inc.
#
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
#

from oslo_config import cfg

compute_model = cfg.OptGroup(name='compute_model',
                             title='Configuration Options for Compute Model',
                             help="Additional configuration options for the "
                                  "compute model.")

COMPUTE_MODEL_OPTS = [
    cfg.BoolOpt(
        'enable_extended_attributes',
        default=False,
        help="Enable the collection of compute model extended attributes. "
             "Note that some attributes require a more recent api "
             "microversion to be configured in nova_client section."
    ),
]


def register_opts(conf):
    conf.register_group(compute_model)
    conf.register_opts(COMPUTE_MODEL_OPTS, group=compute_model)


def list_opts():
    return [(compute_model, COMPUTE_MODEL_OPTS)]
