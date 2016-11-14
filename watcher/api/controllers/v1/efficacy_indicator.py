# -*- encoding: utf-8 -*-
# Copyright (c) 2016 b<>com
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
An efficacy indicator is a single value that gives an indication on how the
:ref:`solution <solution_definition>` produced by a given :ref:`strategy
<strategy_definition>` performed. These efficacy indicators are specific to a
given :ref:`goal <goal_definition>` and are usually used to compute the
:ref:`global efficacy <efficacy_definition>` of the resulting :ref:`action plan
<action_plan_definition>`.

In Watcher, these efficacy indicators are specified alongside the goal they
relate to. When a strategy (which always relates to a goal) is executed, it
produces a solution containing the efficacy indicators specified by the goal.
This solution, which has been translated by the :ref:`Watcher Planner
<watcher_planner_definition>` into an action plan, will see its indicators and
global efficacy stored and would now be accessible through the :ref:`Watcher
API <archi_watcher_api_definition>`.
"""

import numbers

from wsme import types as wtypes

from watcher.api.controllers import base
from watcher import objects


class EfficacyIndicator(base.APIBase):
    """API representation of a efficacy indicator.

    This class enforces type checking and value constraints, and converts
    between the internal object model and the API representation of an
    efficacy indicator.
    """

    name = wtypes.wsattr(wtypes.text, mandatory=True)
    """Name of this efficacy indicator"""

    description = wtypes.wsattr(wtypes.text, mandatory=False)
    """Description of this efficacy indicator"""

    unit = wtypes.wsattr(wtypes.text, mandatory=False)
    """Unit of this efficacy indicator"""

    value = wtypes.wsattr(numbers.Number, mandatory=True)
    """Value of this efficacy indicator"""

    def __init__(self, **kwargs):
        super(EfficacyIndicator, self).__init__()

        self.fields = []
        fields = list(objects.EfficacyIndicator.fields)
        for field in fields:
            # Skip fields we do not expose.
            if not hasattr(self, field):
                continue
            self.fields.append(field)
            setattr(self, field, kwargs.get(field, wtypes.Unset))
