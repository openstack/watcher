# -*- encoding: utf-8 -*-
# Copyright (c) 2016 b<>com
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import functools

from tempest import test
from tempest_lib.common.utils import data_utils
from tempest_lib import exceptions as lib_exc

from watcher_tempest_plugin import infra_optim_clients as clients

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
    def setup_credentials(cls):
        super(BaseInfraOptimTest, cls).setup_credentials()
        cls.mgr = clients.AdminManager()

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

    def validate_self_link(self, resource, uuid, link):
        """Check whether the given self link formatted correctly."""
        expected_link = "{base}/{pref}/{res}/{uuid}".format(
            base=self.client.base_url,
            pref=self.client.URI_PREFIX,
            res=resource,
            uuid=uuid
        )
        self.assertEqual(expected_link, link)

    def assert_expected(self, expected, actual,
                        keys=('created_at', 'updated_at', 'deleted_at')):
        # Check if not expected keys/values exists in actual response body
        for key, value in expected.items():
            if key not in keys:
                self.assertIn(key, actual)
                self.assertEqual(value, actual[key])

    # ### AUDIT TEMPLATES ### #

    @classmethod
    @creates('audit_template')
    def create_audit_template(cls, name=None, description=None, goal=None,
                              host_aggregate=None, extra=None):
        """Wrapper utility for creating a test audit template

        :param name: The name of the audit template. Default: My Audit Template
        :param description: The description of the audit template.
            Default: AT Description
        :param goal: The goal associated within the audit template.
            Default: DUMMY
        :param host_aggregate: ID of the host aggregate targeted by
            this audit template. Default: 1
        :param extra: IMetadata associated to this audit template.
            Default: {}
        :return: A tuple with The HTTP response and its body
        """

        description = description or data_utils.rand_name(
            'test-audit_template')
        resp, body = cls.client.create_audit_template(
            name=name, description=description, goal=goal,
            host_aggregate=host_aggregate, extra=extra)
        return resp, body

    @classmethod
    def delete_audit_template(cls, uuid):
        """Deletes a audit_template having the specified UUID

        :param uuid: The unique identifier of the audit template
        :return: Server response
        """

        resp, body = cls.client.delete_audit_template(uuid)

        if uuid in cls.created_objects['audit_template']:
            cls.created_objects['audit_template'].remove(uuid)

        return resp
