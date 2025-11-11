# Copyright 2024 Red Hat, Inc.
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

prometheus_client = cfg.OptGroup(
    name='prometheus_client',
    title='Configuration Options for Prometheus (DEPRECATED)',
    help="DEPRECATED: The Prometheus datasource is deprecated in favor "
         "of the Aetos datasource. See https://docs.openstack.org/"
         "watcher/latest/datasources/migrate-prometheus-to-aetos.html "
         "for migration instructions.")

PROMETHEUS_CLIENT_OPTS = [
    cfg.HostAddressOpt(
        'host',
        deprecated_for_removal=True,
        deprecated_reason='Prometheus datasource is deprecated in favor '
                          'of Aetos datasource',
        deprecated_since='2026.1',
        help="The hostname or IP address for the prometheus server. "
             "DEPRECATED: Use Aetos datasource instead."),
    cfg.PortOpt(
        'port',
        default=9090,
        deprecated_for_removal=True,
        deprecated_reason='Prometheus datasource is deprecated in favor '
                          'of Aetos datasource',
        deprecated_since='2026.1',
        help="The port number used by the prometheus server. "
             "DEPRECATED: Use Aetos datasource instead."),
    cfg.StrOpt(
        'fqdn_label',
        default="fqdn",
        deprecated_for_removal=True,
        deprecated_reason='Prometheus datasource is deprecated in favor '
                          'of Aetos datasource',
        deprecated_since='2026.1',
        help="The label that Prometheus uses to store the fqdn of "
             "exporters. Defaults to 'fqdn'. "
             "DEPRECATED: Use Aetos datasource instead."),
    cfg.StrOpt(
        'instance_uuid_label',
        default="resource",
        deprecated_for_removal=True,
        deprecated_reason='Prometheus datasource is deprecated in favor '
                          'of Aetos datasource',
        deprecated_since='2026.1',
        help="The label that Prometheus uses to store the uuid of "
             "OpenStack instances. Defaults to 'resource'. "
             "DEPRECATED: Use Aetos datasource instead."),
    cfg.StrOpt(
        'username',
        deprecated_for_removal=True,
        deprecated_reason='Prometheus datasource is deprecated in favor '
                          'of Aetos datasource',
        deprecated_since='2026.1',
        help="The basic_auth username to use to authenticate with the "
             "Prometheus server. DEPRECATED: Use Aetos datasource "
             "instead."),
    cfg.StrOpt(
        'password',
        secret=True,
        deprecated_for_removal=True,
        deprecated_reason='Prometheus datasource is deprecated in favor '
                          'of Aetos datasource',
        deprecated_since='2026.1',
        help="The basic_auth password to use to authenticate with the "
             "Prometheus server. DEPRECATED: Use Aetos datasource "
             "instead."),
    cfg.StrOpt(
        'cafile',
        deprecated_for_removal=True,
        deprecated_reason='Prometheus datasource is deprecated in favor '
                          'of Aetos datasource',
        deprecated_since='2026.1',
        help="Path to the CA certificate for establishing a TLS "
             "connection with the Prometheus server. "
             "DEPRECATED: Use Aetos datasource instead."),
    cfg.StrOpt(
        'certfile',
        deprecated_for_removal=True,
        deprecated_reason='Prometheus datasource is deprecated in favor '
                          'of Aetos datasource',
        deprecated_since='2026.1',
        help="Path to the client certificate for establishing a TLS "
             "connection with the Prometheus server. "
             "DEPRECATED: Use Aetos datasource instead."),
    cfg.StrOpt(
        'keyfile',
        deprecated_for_removal=True,
        deprecated_reason='Prometheus datasource is deprecated in favor '
                          'of Aetos datasource',
        deprecated_since='2026.1',
        help="Path to the client key for establishing a TLS "
             "connection with the Prometheus server. "
             "DEPRECATED: Use Aetos datasource instead."),
]


def register_opts(conf):
    conf.register_group(prometheus_client)
    conf.register_opts(PROMETHEUS_CLIENT_OPTS, group=prometheus_client)


def list_opts():
    return [(prometheus_client, PROMETHEUS_CLIENT_OPTS)]
