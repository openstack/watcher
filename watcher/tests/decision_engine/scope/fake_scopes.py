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

from watcher.tests.decision_engine.model import faker_cluster_state

vum = faker_cluster_state.volume_uuid_mapping

fake_scope_1 = [{'compute': [{'availability_zones': [{'name': 'AZ1'},
                                                     {'name': 'AZ3'}]},
                             {'exclude': [
                                 {'instances': [
                                     {'uuid': 'INSTANCE_6'}]},
                             ]}]
                 }
                ]

compute_scope = [{'compute': [{'host_aggregates': [{'id': '*'}]},
                              {'availability_zones': [{'name': 'AZ1'},
                                                      {'name': 'AZ2'}]},
                              {'exclude': [
                                  {'instances': [
                                      {'uuid': 'INSTANCE_1'},
                                      {'uuid': 'INSTANCE_2'}]},
                                  {'compute_nodes': [
                                      {'name': 'Node_1'},
                                      {'name': 'Node_2'}]}
                              ]}]
                  }
                 ]

fake_scope_2 = [{'storage': [{'availability_zones': [{'name': 'zone_0'}]},
                             {'exclude': [
                                 {'volumes': [
                                     {'uuid': vum['volume_1']}]},

                                 {'storage_pools': [
                                     {'name': 'host_0@backend_0#pool_1'}]}
                             ]}]
                 }
                ]

fake_scope_3 = [{'compute': [{'host_aggregates': [{'id': '1'}]},
                             {'exclude': []
                              }]
                 }
                ]

baremetal_scope = [
    {'baremetal': [
        {'exclude': [
            {'ironic_nodes': [
                {'uuid': 'c5941348-5a87-4016-94d4-4f9e0ce2b87a'},
                {'uuid': 'c5941348-5a87-4016-94d4-4f9e0ce2b87c'}
                ]
             }
            ]
         }
        ]
     }
]
