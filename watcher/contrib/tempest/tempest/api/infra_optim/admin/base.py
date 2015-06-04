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

import functools

from tempest_lib.common.utils import data_utils
from tempest_lib import exceptions as lib_exc

from tempest import clients_infra_optim as clients
from tempest.common import credentials
from tempest import config
from tempest import test

CONF = config.CONF


# Resources must be deleted in a specific order, this list
# defines the resource types to clean up, and the correct order.
RESOURCE_TYPES = ['audit_template']
# RESOURCE_TYPES = ['action', 'action_plan', 'audit', 'audit_template']


def creates(resource):
    """Decorator that adds resources to the appropriate cleanup list."""

    def decorator(f):
        @functools.wraps(f)
        def wrapper(cls, *args, **kwargs):
            resp, body = f(cls, *args, **kwargs)

            if 'uuid' in body:
                cls.created_objects[resource].add(body['uuid'])

            return resp, body
        return wrapper
    return decorator


class BaseInfraOptimTest(test.BaseTestCase):
    """Base class for Infrastructure Optimization API tests."""

    @classmethod
    # def skip_checks(cls):
    #     super(BaseInfraOptimTest, cls).skip_checks()
    #     if not CONF.service_available.watcher:
    #         skip_msg = \
    #             ('%s skipped as Watcher is not available' % cls.__name__)
    #         raise cls.skipException(skip_msg)
    @classmethod
    def setup_credentials(cls):
        super(BaseInfraOptimTest, cls).setup_credentials()
        if (not hasattr(cls, 'isolated_creds') or
                not cls.isolated_creds.name == cls.__name__):
            cls.isolated_creds = credentials.get_isolated_credentials(
                name=cls.__name__, network_resources=cls.network_resources)
        cls.mgr = clients.Manager(cls.isolated_creds.get_admin_creds())

    @classmethod
    def setup_clients(cls):
        super(BaseInfraOptimTest, cls).setup_clients()
        cls.client = cls.mgr.io_client

    @classmethod
    def resource_setup(cls):
        super(BaseInfraOptimTest, cls).resource_setup()

        cls.created_objects = {}
        for resource in RESOURCE_TYPES:
            cls.created_objects[resource] = set()

    @classmethod
    def resource_cleanup(cls):
        """Ensure that all created objects get destroyed."""

        try:
            for resource in RESOURCE_TYPES:
                uuids = cls.created_objects[resource]
                delete_method = getattr(cls.client, 'delete_%s' % resource)
                for u in uuids:
                    delete_method(u, ignore_errors=lib_exc.NotFound)
        finally:
            super(BaseInfraOptimTest, cls).resource_cleanup()

    @classmethod
    @creates('audit_template')
    def create_audit_template(cls, description=None, expect_errors=False):
        """
        Wrapper utility for creating test audit_template.

        :param description: A description of the audit template.
            if not supplied, a random value will be generated.
        :return: Created audit template.

        """
        description = description or data_utils.rand_name(
            'test-audit_template')
        resp, body = cls.client.create_audit_template(description=description)
        return resp, body

    @classmethod
    def delete_audit_template(cls, audit_template_id):
        """
        Deletes a audit_template having the specified UUID.

        :param uuid: The unique identifier of the audit_template.
        :return: Server response.

        """

        resp, body = cls.client.delete_audit_template(audit_template_id)

        if audit_template_id in cls.created_objects['audit_template']:
            cls.created_objects['audit_template'].remove(audit_template_id)

        return resp

    def validate_self_link(self, resource, uuid, link):
        """Check whether the given self link formatted correctly."""
        expected_link = "{base}/{pref}/{res}/{uuid}".format(
                        base=self.client.base_url,
                        pref=self.client.uri_prefix,
                        res=resource,
                        uuid=uuid)
        self.assertEqual(expected_link, link)
