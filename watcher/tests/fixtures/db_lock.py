# Copyright 2026 Red Hat, Inc.
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

"""Threading lock fixture for database write operations in Watcher tests."""

import contextlib
import threading

import fixtures

from watcher.db.sqlalchemy import api as db_api


class DatabaseWriteLock(fixtures.Fixture):
    """Fixture that adds a threading lock to database write operations.

    This fixture ensures that multiple threads cannot write to the database
    simultaneously by adding a global lock around the _session_for_write
    function. This is useful for tests that use threading or concurrent
    operations to avoid race conditions and database conflicts.

    The lock is applied by wrapping Watcher's db_api._session_for_write
    function, ensuring that all database writes are serialized.
    """

    def __init__(self, lock_timeout=None):
        """Initialize the DatabaseWriteLock fixture.

        :param lock_timeout: Optional timeout for acquiring the lock (seconds).
                            If None, the lock will block indefinitely.
        :raises ValueError: If lock_timeout is not None and not a positive
                           number.
        """
        super().__init__()
        if lock_timeout is not None and lock_timeout <= 0:
            raise ValueError(
                "lock_timeout must be None or a positive number, "
                f"got {lock_timeout}")
        self.lock_timeout = lock_timeout
        self._db_write_lock = threading.RLock()  # Reentrant lock

    def _setUp(self):
        """Set up the database write lock."""
        # Store the original _session_for_write function
        original_session_for_write = db_api._session_for_write

        @contextlib.contextmanager
        def locked_session_for_write():
            """Wrapper that adds locking around _session_for_write."""
            # Acquire the lock before entering the database session
            acquired = self._db_write_lock.acquire(
                blocking=True,
                timeout=self.lock_timeout if self.lock_timeout else -1)

            if not acquired:
                raise RuntimeError(
                    f"Failed to acquire database write lock within "
                    f"{self.lock_timeout} seconds")

            try:
                # Enter the original writer session context
                with original_session_for_write() as session:
                    yield session
            finally:
                # Release the lock after exiting the database session
                self._db_write_lock.release()

        # Patch _session_for_write in watcher's db api
        self.useFixture(fixtures.MockPatchObject(
            db_api, '_session_for_write', locked_session_for_write))
