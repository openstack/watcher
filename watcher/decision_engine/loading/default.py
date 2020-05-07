# -*- encoding: utf-8 -*-
# Copyright (c) 2015 b<>com
#
# Authors: Jean-Emile DARTOIS <jean-emile.dartois@b-com.com>
#          Vincent FRANCOISE <vincent.francoise@b-com.com>
#          Tomasz Kaczynski <tomasz.kaczynski@intel.com>
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

from watcher.common.loader import default


class DefaultStrategyLoader(default.DefaultLoader):
    def __init__(self):
        super(DefaultStrategyLoader, self).__init__(
            namespace='watcher_strategies')


class DefaultGoalLoader(default.DefaultLoader):
    def __init__(self):
        super(DefaultGoalLoader, self).__init__(
            namespace='watcher_goals')


class DefaultPlannerLoader(default.DefaultLoader):
    def __init__(self):
        super(DefaultPlannerLoader, self).__init__(
            namespace='watcher_planners')


class ClusterDataModelCollectorLoader(default.DefaultLoader):
    def __init__(self):
        super(ClusterDataModelCollectorLoader, self).__init__(
            namespace='watcher_cluster_data_model_collectors')


class DefaultScoringLoader(default.DefaultLoader):
    def __init__(self):
        super(DefaultScoringLoader, self).__init__(
            namespace='watcher_scoring_engines')


class DefaultScoringContainerLoader(default.DefaultLoader):
    def __init__(self):
        super(DefaultScoringContainerLoader, self).__init__(
            namespace='watcher_scoring_engine_containers')
