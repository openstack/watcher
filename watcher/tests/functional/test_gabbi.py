# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Gabbi test loader for Watcher functional tests.

Discovers YAML test files in the ``gabbits/`` directory and builds
unittest-compatible test suites that stestr can discover and run.
"""

import os

from gabbi import driver

from watcher.tests.functional import gabbi_fixture


TESTS_DIR = 'gabbits'


def load_tests(loader, tests, pattern):
    test_dir = os.path.join(os.path.dirname(__file__), TESTS_DIR)
    return driver.build_tests(
        test_dir,
        loader,
        intercept=gabbi_fixture.wsgi_app,
        fixture_module=gabbi_fixture,
        prefix='/v1',
        test_loader_name=__name__,
    )
