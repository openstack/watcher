# Copyright 2013 Red Hat, Inc.
# All Rights Reserved.
#
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

import wsme

from oslo_config import cfg

from watcher.api.controllers.v1 import utils
from watcher.tests import base

CONF = cfg.CONF


class TestApiUtils(base.TestCase):

    def test_validate_limit(self):
        limit = utils.validate_limit(10)
        self.assertEqual(10, 10)

        # max limit
        limit = utils.validate_limit(999999999)
        self.assertEqual(CONF.api.max_limit, limit)

        # negative
        self.assertRaises(wsme.exc.ClientSideError, utils.validate_limit, -1)

        # zero
        self.assertRaises(wsme.exc.ClientSideError, utils.validate_limit, 0)

    def test_validate_sort_dir(self):
        # if sort_dir is valid, nothing should happen
        try:
            utils.validate_sort_dir('asc')
        except Exception as exc:
            self.fail(exc)

        # invalid sort_dir parameter
        self.assertRaises(wsme.exc.ClientSideError,
                          utils.validate_sort_dir,
                          'fake-sort')

    def test_validate_search_filters(self):
        allowed_fields = ["allowed", "authorized"]

        test_filters = {"allowed": 1, "authorized": 2}
        try:
            utils.validate_search_filters(test_filters, allowed_fields)
        except Exception as exc:
            self.fail(exc)

    def test_validate_search_filters_with_invalid_key(self):
        allowed_fields = ["allowed", "authorized"]

        test_filters = {"allowed": 1, "unauthorized": 2}

        self.assertRaises(
            wsme.exc.ClientSideError, utils.validate_search_filters,
            test_filters, allowed_fields)
