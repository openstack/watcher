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

from observabilityclient import prometheus_client
from oslo_config import cfg
from oslo_log import log
import re

from watcher._i18n import _
from watcher.common import exception
from watcher.decision_engine.datasources import prometheus_base

CONF = cfg.CONF
LOG = log.getLogger(__name__)


class PrometheusHelper(prometheus_base.PrometheusBase):
    """PrometheusHelper class for retrieving metrics from Prometheus server

    This class implements the PrometheusBase to allow Watcher to query
    Prometheus as a data source for metrics.
    """

    NAME = 'prometheus'

    def _get_fqdn_label(self):
        """Get the FQDN label from prometheus_client config"""
        return CONF.prometheus_client.fqdn_label

    def _get_instance_uuid_label(self):
        """Get the instance UUID label from prometheus_client config"""
        return CONF.prometheus_client.instance_uuid_label

    def _setup_prometheus_client(self):
        """Initialise the prometheus client with config options

        Use the prometheus_client options in watcher.conf to setup
        the PrometheusAPIClient client object and return it.
        :raises watcher.common.exception.MissingParameter if
                prometheus host or port is not set in the watcher.conf
                under the [prometheus_client] section.
        :raises watcher.common.exception.InvalidParameter if
                the prometheus host or port have invalid format.
        """
        def _validate_host_port(host, port):
            if len(host) > 255:
                return (False, "hostname is too long: '%s'" % host)
            if host[-1] == '.':
                host = host[:-1]
            legal_hostname = re.compile(
                "(?!-)[a-z0-9-]{1,63}(?<!-)$", re.IGNORECASE)
            if not all(legal_hostname.match(host_part)
                       for host_part in host.split(".")):
                return (False, "hostname '%s' failed regex match " % host)
            try:
                assert bool(1 <= int(port) <= 65535)
            except (AssertionError, ValueError):
                return (False, "missing or invalid port number '%s' "
                        % port)
            return (True, "all good")

        _host = CONF.prometheus_client.host
        _port = CONF.prometheus_client.port
        if (not _host or not _port):
            raise exception.MissingParameter(
                message=(_(
                    "prometheus host and port must be set in watcher.conf "
                    "under the [prometheus_client] section. Can't initialise "
                    "the datasource without valid host and port."))
            )
        validated, reason = _validate_host_port(_host, _port)
        if (not validated):
            raise exception.InvalidParameter(
                message=(_(
                    "A valid prometheus host and port are required. The #"
                    "values found in watcher.conf are '%(host)s' '%(port)s'. "
                    "This fails validation for the following reason: "
                    "%(reason)s.")
                    % {'host': _host, 'port': _port, 'reason': reason})
            )
        the_client = prometheus_client.PrometheusAPIClient(
            "{}:{}".format(_host, _port))

        # check if tls options or basic_auth options are set and use them
        prometheus_user = CONF.prometheus_client.username
        prometheus_pass = CONF.prometheus_client.password
        prometheus_ca_cert = CONF.prometheus_client.cafile
        prometheus_client_cert = CONF.prometheus_client.certfile
        prometheus_client_key = CONF.prometheus_client.keyfile
        if (prometheus_ca_cert):
            the_client.set_ca_cert(prometheus_ca_cert)
            if (prometheus_client_cert and prometheus_client_key):
                the_client.set_client_cert(
                    prometheus_client_cert, prometheus_client_key)
        if (prometheus_user and prometheus_pass):
            the_client.set_basic_auth(prometheus_user, prometheus_pass)

        return the_client
