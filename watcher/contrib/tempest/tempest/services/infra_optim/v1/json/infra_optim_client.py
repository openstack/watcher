#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from tempest.services.infra_optim import base


class InfraOptimClientJSON(base.InfraOptimClient):
    """
    Base Tempest REST client for Watcher API v1.
    """
    version = '1'
    uri_prefix = 'v1'

    # Audit Template

    @base.handle_errors
    def list_audit_templates(self, **kwargs):
        """List all existing audit templates."""
        return self._list_request('audit_templates', **kwargs)

    @base.handle_errors
    def list_audit_template_audits(self, audit_template_uuid):
        """Lists all audits associated with a audit template."""
        return self._list_request(
            '/audit_templates/%s/audits' % audit_template_uuid)

    @base.handle_errors
    def list_audit_templates_detail(self, **kwargs):
        """Lists details of all existing audit templates."""
        return self._list_request('/audit_templates/detail', **kwargs)

    @base.handle_errors
    def show_audit_template(self, uuid):
        """
        Gets a specific audit template.

        :param uuid: Unique identifier of the audit template in UUID format.
        :return: Serialized audit template as a dictionary.

        """
        return self._show_request('audit_templates', uuid)

    @base.handle_errors
    def show_audit_template_by_host_agregate(self, host_agregate_id):
        """
        Gets an audit template associated with given host agregate ID.

        :param uuid: Unique identifier of the audit_template in UUID format.
        :return: Serialized audit_template as a dictionary.

        """
        uri = '/audit_templates/detail?host_agregate=%s' % host_agregate_id

        return self._show_request('audit_templates', uuid=None, uri=uri)

    @base.handle_errors
    def show_audit_template_by_goal(self, goal):
        """
        Gets an audit template associated with given goal.

        :param uuid: Unique identifier of the audit_template in UUID format.
        :return: Serialized audit_template as a dictionary.

        """
        uri = '/audit_templates/detail?goal=%s' % goal

        return self._show_request('audit_templates', uuid=None, uri=uri)

    @base.handle_errors
    def create_audit_template(self, **kwargs):
        """
        Creates an audit template with the specified parameters.

        :param name: The name of the audit template. Default: My Audit Template
        :param description: The description of the audit template.
            Default: AT Description
        :param goal: The goal associated within the audit template.
            Default: SERVERS_CONSOLIDATION
        :param host_aggregate: ID of the host aggregate targeted by
            this audit template. Default: 1
        :param extra: IMetadata associated to this audit template.
            Default: {}
        :return: A tuple with the server response and the created audit
            template.

        """
        audit_template = {
            'name': kwargs.get('name', 'My Audit Template'),
            'description': kwargs.get('description', 'AT Description'),
            'goal': kwargs.get('goal', 'SERVERS_CONSOLIDATION'),
            'host_aggregate': kwargs.get('host_aggregate', 1),
            'extra': kwargs.get('extra', {}),
            }

        return self._create_request('audit_templates', audit_template)

    # @base.handle_errors
    # def create_audit(self, audit_template_id=None, **kwargs):
    #     """
    #     Create a infra_optim audit with the specified parameters.

    #     :param cpu_arch: CPU architecture of the audit. Default: x86_64.
    #     :param cpus: Number of CPUs. Default: 8.
    #     :param local_gb: Disk size. Default: 1024.
    #     :param memory_mb: Available RAM. Default: 4096.
    #     :param driver: Driver name. Default: "fake"
    #     :return: A tuple with the server response and the created audit.

    #     """
    #     audit = {'audit_template_uuid': audit_template_id,
    #             'properties': {'cpu_arch': kwargs.get('cpu_arch', 'x86_64'),
    #                            'cpus': kwargs.get('cpus', 8),
    #                            'local_gb': kwargs.get('local_gb', 1024),
    #                            'memory_mb': kwargs.get('memory_mb', 4096)},
    #             'driver': kwargs.get('driver', 'fake')}

    #     return self._create_request('audits', audit)

    @base.handle_errors
    def delete_audit_template(self, uuid):
        """
        Deletes an audit template having the specified UUID.

        :param uuid: The unique identifier of the audit template.
        :return: A tuple with the server response and the response body.

        """
        return self._delete_request('audit_templates', uuid)

    @base.handle_errors
    def update_audit_template(self, uuid, patch):
        """
        Update the specified audit template.

        :param uuid: The unique identifier of the audit template.
        :param patch: List of dicts representing json patches.
        :return: A tuple with the server response and the updated audit
            template.

        """

        return self._patch_request('audit_templates', uuid, patch)
