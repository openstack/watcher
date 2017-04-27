# -*- encoding: utf-8 -*-
# Copyright (c) 2016 Servionica
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
#

import abc
import six

from watcher.common import context


@six.add_metaclass(abc.ABCMeta)
class BaseScope(object):
    """A base class for Scope mechanism

    Child of this class is called when audit launches strategy. This strategy
    requires Cluster Data Model which can be segregated to achieve audit scope.
    """

    def __init__(self, scope, config):
        self.ctx = context.make_context()
        self.scope = scope
        self.config = config

    @abc.abstractmethod
    def get_scoped_model(self, cluster_model):
        """Leave only nodes and instances proposed in the audit scope"""
