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

import copy
import futurist
from futurist import waiters

from oslo_config import cfg
from oslo_log import log
from oslo_service import service

CONF = cfg.CONF
LOG = log.getLogger(__name__)


class DecisionEngineThreadPool(object, metaclass=service.Singleton):
    """Singleton threadpool to submit general tasks to"""

    def __init__(self):
        self.amount_workers = CONF.watcher_decision_engine.max_general_workers
        self._threadpool = futurist.GreenThreadPoolExecutor(
            max_workers=self.amount_workers)

    def submit(self, fn, *args, **kwargs):
        """Will submit the job to the underlying threadpool

        :param fn: function to execute in another thread
        :param args: arguments for the function
        :param kwargs: amount of arguments for the function
        :return: future to monitor progress of execution
        :rtype: :py:class"`futurist.GreenFuture`
        """

        return self._threadpool.submit(fn, *args, **kwargs)

    @staticmethod
    def do_while_futures(futures, fn, *args, **kwargs):
        """Do while to execute a function upon completion from a collection

        Will execute the specified function with its arguments when one of the
        futures from the passed collection finishes. Additionally, the future
        is passed as first argument to the function. Does not modify the passed
        collection of futures.

        :param futures: list, set or dictionary of futures
        :type  futures: list :py:class:`futurist.GreenFuture`
        :param fn:  function to execute upon the future finishing execution
        :param args: arguments for the function
        :param kwargs: amount of arguments for the function
        """

        # shallow copy the collection to not modify it outside of this method.
        # shallow copy must be used because the type of collection needs to be
        # determined at runtime (can be both list, set and dict).
        futures = copy.copy(futures)

        DecisionEngineThreadPool.do_while_futures_modify(
            futures, fn, *args, **kwargs)

    @staticmethod
    def do_while_futures_modify(futures, fn, *args, **kwargs):
        """Do while to execute a function upon completion from a collection

        Will execute the specified function with its arguments when one of the
        futures from the passed collection finishes. Additionally, the future
        is passed as first argument to the function. Modifies the collection
        by removing completed elements,

        :param futures: list, set or dictionary of futures
        :type  futures: list :py:class:`futurist.GreenFuture`
        :param fn:  function to execute upon the future finishing execution
        :param args: arguments for the function
        :param kwargs: amount of arguments for the function
        """

        waits = waiters.wait_for_any(futures)
        while len(waits[0]) > 0 or len(waits[1]) > 0:
            for future in waiters.wait_for_any(futures)[0]:
                fn(future, *args, **kwargs)
                futures.remove(future)
            waits = waiters.wait_for_any(futures)
