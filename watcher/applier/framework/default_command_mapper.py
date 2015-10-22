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


from watcher.applier.api.command_mapper import CommandMapper
from watcher.applier.framework.command.hypervisor_state_command import \
    HypervisorStateCommand
from watcher.applier.framework.command.migrate_command import MigrateCommand
from watcher.applier.framework.command.nop_command import NopCommand
from watcher.applier.framework.command.power_state_command import \
    PowerStateCommand
from watcher.common.exception import ActionNotFound
from watcher.decision_engine.framework.default_planner import Primitives


class DefaultCommandMapper(CommandMapper):
    def build_primitive_command(self, action):
        if action.action_type == Primitives.COLD_MIGRATE.value:
            return MigrateCommand(action.applies_to, Primitives.COLD_MIGRATE,
                                  action.src,
                                  action.dst)
        elif action.action_type == Primitives.LIVE_MIGRATE.value:
            return MigrateCommand(action.applies_to, Primitives.COLD_MIGRATE,
                                  action.src,
                                  action.dst)
        elif action.action_type == Primitives.HYPERVISOR_STATE.value:
            return HypervisorStateCommand(action.applies_to, action.parameter)
        elif action.action_type == Primitives.POWER_STATE.value:
            return PowerStateCommand()
        elif action.action_type == Primitives.NOP.value:
            return NopCommand()
        else:
            raise ActionNotFound()
