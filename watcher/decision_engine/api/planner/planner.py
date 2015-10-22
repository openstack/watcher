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


class Planner(object):
    def schedule(self, context, audit_uuid, solution):
        """The  planner receives a solution to schedule

        :param solution: the solution given by the strategy to
        :param audit_uuid: the audit uuid
        :return: ActionPlan ordered sequence of change requests
        such that all security, dependency,
        and performance requirements are met.
        """
        # example: directed acyclic graph
        raise NotImplementedError("Should have implemented this")
