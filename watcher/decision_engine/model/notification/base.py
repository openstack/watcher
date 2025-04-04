# -*- encoding: utf-8 -*-
# Copyright (c) 2016 b<>com
#
# Authors: Vincent FRANCOISE <Vincent.FRANCOISE@b-com.com>
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

import abc


class NotificationEndpoint(object, metaclass=abc.ABCMeta):

    def __init__(self, collector):
        super(NotificationEndpoint, self).__init__()
        self.collector = collector
        self._notifier = None

    @property
    @abc.abstractmethod
    def filter_rule(self):
        """Notification Filter"""
        raise NotImplementedError()

    @property
    def cluster_data_model(self):
        return self.collector.cluster_data_model
