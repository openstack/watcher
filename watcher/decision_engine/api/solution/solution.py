# -*- encoding: utf-8 -*-
# Copyright (c) 2015 b<>com
#
# Authors: Jean-Emile DARTOIS <jean-emile.dartois@b-com.com>
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


class Solution(object):
    def __init__(self):
        self.modelOrigin = None
        self.currentModel = None
        self.efficiency = 0

    def get_efficiency(self):
        return self.efficiency

    def set_efficiency(self, efficiency):
        self.efficiency = efficiency

    def set_model(self, current_model):
        self.currentModel = current_model

    def get_model(self):
        return self.currentModel
