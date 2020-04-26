# -*- encoding: utf-8 -*-
# Copyright (c) 2019 European Organization for Nuclear Research (CERN)
#
# Authors: Corne Lukken <info@dantalion.nl>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import futurist
from unittest import mock

from watcher.decision_engine import threading
from watcher.tests import base


class TestDecisionEngineThreadPool(base.TestCase):

    def setUp(self):
        super(TestDecisionEngineThreadPool, self).setUp()

        self.m_function = mock.Mock()
        self.m_function.return_value = None
        self.m_do_while_function = mock.Mock()
        self.m_do_while_function.return_value = None

        # override the underlying threadpool for testing
        # this is like a 'fixture' were the original state of the singleton
        # is restored after these tests finish but the threadpool can still
        # be used as intended with its methods
        self.p_threadool = mock.patch.object(
            threading, 'DecisionEngineThreadPool',
            new=threading.DecisionEngineThreadPool)
        self.m_threadpool = self.p_threadool.start()
        self.addCleanup(self.p_threadool.stop)

        # bind unbound patched methods for python 2.7 compatibility
        # class methods can be used unbounded in Python 3.x
        self.m_threadpool.submit = self.m_threadpool.submit.__get__(
            self.m_threadpool, threading.DecisionEngineThreadPool)

        # perform all tests synchronously
        self.m_threadpool._threadpool = futurist.SynchronousExecutor()

    def test_singleton(self):
        """Ensure only one object of DecisionEngineThreadPool can be created"""

        threadpool1 = threading.DecisionEngineThreadPool()
        threadpool2 = threading.DecisionEngineThreadPool()
        self.assertEqual(threadpool1, threadpool2)

    def test_fixture_not_singleton(self):
        """Ensure the fixture does create a new instance of the singleton"""

        threadpool1 = threading.DecisionEngineThreadPool()
        threadpool2 = self.m_threadpool
        self.assertNotEqual(threadpool1, threadpool2)

    def test_do_while(self):
        """Test the regular operation of the threadpool and do_while_futures

        With the regular operation of do_while_futures the collection of
        futures will be shallow copied and left unmodified to the caller.

        """

        # create a collection of futures from submitted m_function tasks
        futures = [self.m_threadpool.submit(self.m_function, 1, 2)]

        self.m_function.assert_called_once_with(1, 2)

        # execute m_do_while_function for every future that completes
        # and block until all futures are completed
        self.m_threadpool.do_while_futures(
            futures, self.m_do_while_function, 3, 4)

        # assert that m_do_while_function was called
        self.m_do_while_function.assert_called_once_with(futures[0], 3, 4)

        # assert that the collection of futures is unmodified
        self.assertEqual(1, len(futures))

    def test_do_while_modify(self):
        """Test the operation of the threadpool and do_while_futures_modify

        The do_while_future_modify function has slightly better performance
        because it will not create a copy of the collection and will modify it
        directly.

        """

        # create a collection of futures from submitted m_function tasks
        futures = [self.m_threadpool.submit(self.m_function, 1, 2)]

        self.m_function.assert_called_once_with(1, 2)

        # hold reference because element is going to be removed from the list
        future_ref = futures[0]

        # execute m_do_while_function for every future that completes
        # and block until all futures are completed
        self.m_threadpool.do_while_futures_modify(
            futures, self.m_do_while_function, 3, 4)

        # assert that m_do_while_function was called
        self.m_do_while_function.assert_called_once_with(future_ref, 3, 4)

        # assert that the collection of futures is modified
        self.assertEqual(0, len(futures))

    def test_multiple_tasks(self):
        """Test that 10 tasks are all executed with the correct arguments"""

        # create a collection of 10 futures from submitted m_function tasks
        futures = [self.m_threadpool.submit(
            self.m_function, i, 2) for i in range(10)]

        # assert that there are 10 submitted tasks
        self.assertEqual(10, len(futures))

        # execute m_do_while_function for every future that completes
        # and block until all futures are completed
        self.m_threadpool.do_while_futures(
            futures, self.m_do_while_function, 3, 4)

        # create list of 10 calls that should have occurred
        calls_submit = []
        for i in range(10):
            calls_submit.append(mock.call(i, 2))
        # test that the submit function has been called 10 times
        self.m_function.assert_has_calls(
            calls_submit, any_order=True)

        # create list of 10 calls that should have occurred
        calls_do_while = []
        for i in range(10):
            calls_do_while.append(mock.call(futures[i], 3, 4))
        # test that the passed do_while function has been called 10 times
        self.m_do_while_function.assert_has_calls(
            calls_do_while, any_order=True)
