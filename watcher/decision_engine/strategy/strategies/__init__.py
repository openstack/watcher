# -*- encoding: utf-8 -*-
# Copyright (c) 2016 b<>com
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


from watcher.decision_engine.strategy.strategies import basic_consolidation
from watcher.decision_engine.strategy.strategies import dummy_strategy
from watcher.decision_engine.strategy.strategies import outlet_temp_control
from watcher.decision_engine.strategy.strategies import uniform_airflow
from watcher.decision_engine.strategy.strategies import \
    vm_workload_consolidation
from watcher.decision_engine.strategy.strategies import workload_balance
from watcher.decision_engine.strategy.strategies import workload_stabilization

BasicConsolidation = basic_consolidation.BasicConsolidation
OutletTempControl = outlet_temp_control.OutletTempControl
DummyStrategy = dummy_strategy.DummyStrategy
VMWorkloadConsolidation = vm_workload_consolidation.VMWorkloadConsolidation
WorkloadBalance = workload_balance.WorkloadBalance
WorkloadStabilization = workload_stabilization.WorkloadStabilization
UniformAirflow = uniform_airflow.UniformAirflow

__all__ = ("BasicConsolidation", "OutletTempControl", "DummyStrategy",
           "VMWorkloadConsolidation", "WorkloadBalance",
           "WorkloadStabilization", "UniformAirflow")
