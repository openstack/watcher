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

import itertools

from watcher.common.policies import action
from watcher.common.policies import action_plan
from watcher.common.policies import audit
from watcher.common.policies import audit_template
from watcher.common.policies import base
from watcher.common.policies import data_model
from watcher.common.policies import goal
from watcher.common.policies import scoring_engine
from watcher.common.policies import service
from watcher.common.policies import strategy


def list_rules():
    return itertools.chain(
        base.list_rules(),
        action.list_rules(),
        action_plan.list_rules(),
        audit.list_rules(),
        audit_template.list_rules(),
        data_model.list_rules(),
        goal.list_rules(),
        scoring_engine.list_rules(),
        service.list_rules(),
        strategy.list_rules(),
    )
