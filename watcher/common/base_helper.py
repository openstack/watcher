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

"""Mixin for OpenStack SDK connection setup."""

from keystoneauth1 import loading as ks_loading
from keystoneauth1 import session as ka_session
from openstack import connection
from oslo_context import context as os_context
from oslo_log import log

from watcher import conf
from watcher.common import clients
from watcher.conf import clients_auth


LOG = log.getLogger(__name__)

CONF = conf.CONF


class BaseConnectionMixin:
    """Mixin that provides OpenStackSDK connection setup."""

    connection: connection.Connection

    def _create_sdk_connection(
        self,
        service_name: str,
        session: ka_session.Session | None = None,
        context: os_context.RequestContext | None = None,
    ) -> None:
        """Create and store an OpenStackSDK Connection.

        Loads the auth plugin from the config group identified by
        *service_name*. If the auth plugin cannot be loaded from
        that section, falls back to the
        ``[watcher_clients_auth]`` section.

        :param service_name: Name of the oslo.config group for the
            target service (e.g. ``'nova'``, ``'keystone'``).
        :param session: Optional keystone session to create the
            openstack connection.
        :param context: Optional context object, used to get the
            user's token to create the openstack connection.
        """
        auth_group = service_name
        svc_auth = ks_loading.load_auth_from_conf_options(CONF, auth_group)
        if svc_auth is None:
            LOG.debug(
                "could not load auth plugin from [%s] "
                "section, using %s as fallback",
                service_name,
                clients_auth.WATCHER_CLIENTS_AUTH,
            )
            auth_group = clients_auth.WATCHER_CLIENTS_AUTH

        self.connection = clients.get_sdk_connection(
            auth_group,
            context=context,
            session=session,
            interface=CONF[service_name].valid_interfaces,
            region_name=CONF[service_name].region_name,
        )
