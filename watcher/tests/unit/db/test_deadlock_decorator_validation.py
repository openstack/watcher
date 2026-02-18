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

"""Regression test for @retry_on_deadlock decorator requirement.

This test validates that all public database API methods using
_session_for_write() have the required @oslo_db_api.retry_on_deadlock
decorator for deadlock retry protection in MySQL/PostgreSQL deployments.

See watcher/db/sqlalchemy/api.py lines 54-56 for the requirement.
"""

import ast
import inspect

from watcher.db.sqlalchemy import api
from watcher.tests.unit import base


class ASTMethodAnalyzer:
    """Analyzes Connection class methods using AST."""

    def __init__(self, connection_class):
        self.source_file = inspect.getsourcefile(connection_class)
        with open(self.source_file) as f:
            self.tree = ast.parse(f.read())
        self.connection_node = self._find_connection_class()
        self.methods = self._analyze_methods()

    def _find_connection_class(self):
        """Find Connection class in AST."""
        for node in ast.walk(self.tree):
            if isinstance(node, ast.ClassDef) and node.name == 'Connection':
                return node
        return None

    def _has_retry_decorator(self, method_node):
        """Check if method has @oslo_db_api.retry_on_deadlock."""
        for dec in method_node.decorator_list:
            # @oslo_db_api.retry_on_deadlock
            if isinstance(dec, ast.Attribute):
                if (isinstance(dec.value, ast.Name) and
                        dec.value.id == 'oslo_db_api' and
                        dec.attr == 'retry_on_deadlock'):
                    return True
            # @retry_on_deadlock (if imported directly)
            elif isinstance(dec, ast.Name):
                if dec.id == 'retry_on_deadlock':
                    return True
        return False

    def _uses_session_for_write(self, method_node):
        """Check if method directly calls _session_for_write()."""
        for node in ast.walk(method_node):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id == '_session_for_write':
                        return True
        return False

    def _get_called_methods(self, method_node):
        """Get list of class methods called by this method."""
        called = set()
        for node in ast.walk(method_node):
            if isinstance(node, ast.Call):
                # self.method_name()
                if isinstance(node.func, ast.Attribute):
                    if (isinstance(node.func.value, ast.Name) and
                            node.func.value.id == 'self'):
                        called.add(node.func.attr)
        return called

    def _analyze_methods(self):
        """Analyze all methods in Connection class."""
        methods = {}

        if not self.connection_node:
            return methods

        for item in self.connection_node.body:
            if isinstance(item, ast.FunctionDef):
                methods[item.name] = {
                    'node': item,
                    'has_decorator': self._has_retry_decorator(item),
                    'uses_write': self._uses_session_for_write(item),
                    'calls': self._get_called_methods(item),
                    'is_public': not item.name.startswith('_')
                }

        return methods

    def compute_unprotected_write_users(self):
        """Compute which methods use _session_for_write without protection.

        This analysis accounts for the design pattern where helper methods
        like _create(), _update(), _destroy(), _soft_delete() already have
        the decorator. Public methods calling these are already protected.

        Returns dict mapping method_name -> {
            'direct': bool,  # Directly uses _session_for_write
            'indirect': bool,  # Calls undecorated method that uses it
            'call_chain': list  # Path to _session_for_write
        }
        """
        result = {}

        # First pass: mark direct users of _session_for_write
        for name, info in self.methods.items():
            if info['uses_write']:
                result[name] = {
                    'direct': True,
                    'indirect': False,
                    'call_chain': [name, '_session_for_write()'],
                    'protected': info['has_decorator']
                }

        # Iterative fixed-point: propagate to callers
        # But only propagate through UNDECORATED methods
        changed = True
        max_iterations = 100  # Prevent infinite loops
        iteration = 0

        while changed and iteration < max_iterations:
            changed = False
            iteration += 1

            for name, info in self.methods.items():
                if name in result:
                    continue  # Already marked

                # Check if this method calls any marked UNDECORATED method
                for called in info['calls']:
                    if called in result:
                        called_info = self.methods.get(called)
                        # Only propagate if the called method lacks decorator
                        # (if it has decorator, the call is already protected)
                        if called_info and not called_info['has_decorator']:
                            result[name] = {
                                'direct': False,
                                'indirect': True,
                                'call_chain': ([name] +
                                               result[called]['call_chain']),
                                'protected': info['has_decorator']
                            }
                            changed = True
                            break

        return result


class TestRetryOnDeadlockDecorator(base.TestCase):
    """Validate @retry_on_deadlock decorator on write methods."""

    def setUp(self):
        super().setUp()
        self.analyzer = ASTMethodAnalyzer(api.Connection)

    def test_public_methods_using_write_session_have_decorator(self):
        """Public methods using _session_for_write must have decorator.

        This test validates that public methods using _session_for_write()
        without protection have the required @oslo_db_api.retry_on_deadlock
        decorator. Methods are considered protected if:
        - They have the decorator themselves, OR
        - They only call decorated private methods (like _create, _update)

        Methods need the decorator if they:
        - Directly use _session_for_write(), OR
        - Call undecorated private methods that use _session_for_write()

        See watcher/db/sqlalchemy/api.py lines 54-56 for requirement.
        """
        write_users = self.analyzer.compute_unprotected_write_users()
        violations = []

        for method_name in write_users:
            method_info = self.analyzer.methods.get(method_name)

            if not method_info:
                continue

            # Only check public methods
            if not method_info['is_public']:
                continue

            # Public method uses write session but lacks decorator
            if not method_info['has_decorator']:
                usage_info = write_users[method_name]
                call_chain = ' -> '.join(usage_info['call_chain'])
                violation = {
                    'method': method_name,
                    'direct': usage_info['direct'],
                    'call_chain': call_chain
                }
                violations.append(violation)

        # Report all violations with helpful message
        if violations:
            msg_parts = [
                "\nPublic methods using _session_for_write() without "
                "protection must have @oslo_db_api.retry_on_deadlock "
                "decorator.",
                "\nMissing decorator on:",
            ]
            for v in violations:
                usage_type = "directly" if v['direct'] else "indirectly via"
                msg_parts.append(
                    "  - {}() - uses {}: {}".format(
                        v['method'], usage_type, v['call_chain'])
                )
            msg_parts.append(
                "\nNote: Methods calling decorated helpers (_create, "
                "_update, _destroy, _soft_delete) are already protected."
            )
            msg_parts.append(
                "\nSee watcher/db/sqlalchemy/api.py lines 54-56 for "
                "decorator requirement."
            )

            self.fail('\n'.join(msg_parts))

    def test_ast_analyzer_detects_known_methods(self):
        """Verify AST analyzer correctly identifies known decorated methods.

        This sanity check ensures the AST parsing works correctly by
        validating it finds methods we know have the decorator.
        """
        # These methods were added in commit b060ebb2
        known_decorated = [
            'create_audit_template',
            'create_audit',
            'destroy_audit',
            'destroy_action',
            'update_action',
            'destroy_action_plan',
            'update_action_plan',
        ]

        for method_name in known_decorated:
            method_info = self.analyzer.methods.get(method_name)
            self.assertIsNotNone(
                method_info,
                f"AST analyzer should find {method_name}()")
            self.assertTrue(
                method_info['has_decorator'],
                f"{method_name}() should have @retry_on_deadlock decorator")

    def test_ast_analyzer_detects_write_session_usage(self):
        """Verify AST analyzer detects _session_for_write() usage."""
        # Known direct users (methods that directly call _session_for_write)
        known_direct_users = [
            'create_audit_template',
            'create_audit',
            'destroy_audit',
            'destroy_action',
            'destroy_action_plan',
            '_do_update_action',  # private static method
            '_do_update_action_plan',  # private static method
        ]

        write_users = self.analyzer.compute_unprotected_write_users()

        for method_name in known_direct_users:
            self.assertIn(
                method_name,
                write_users,
                f"AST analyzer should detect {method_name}() uses "
                "_session_for_write()")
            # Verify it's marked as direct usage
            self.assertTrue(
                write_users[method_name]['direct'],
                f"{method_name}() should be marked as direct user")
