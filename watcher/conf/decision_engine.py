# -*- encoding: utf-8 -*-
# Copyright (c) 2015 Intel Corp
#
# Authors: Prudhvi Rao Shedimbi <prudhvi.rao.shedimbi@intel.com>
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

from oslo_config import cfg


watcher_decision_engine = cfg.OptGroup(name='watcher_decision_engine',
                                       title='Defines the parameters of '
                                             'the module decision engine')

WATCHER_DECISION_ENGINE_OPTS = [
    cfg.StrOpt('conductor_topic',
               default='watcher.decision.control',
               help='The topic name used for '
                    'control events, this topic '
                    'used for RPC calls'),
    cfg.ListOpt('notification_topics',
                default=['nova.versioned_notifications',
                         'watcher.watcher_notifications'],
                help='The exchange and topic names from which '
                     'notification events will be listened to. '
                     'The exchange should be specified to get '
                     'an ability to use pools.'),
    cfg.StrOpt('publisher_id',
               default='watcher.decision.api',
               help='The identifier used by the Watcher '
                    'module on the message broker'),
    cfg.IntOpt('max_audit_workers',
               default=2,
               required=True,
               help='The maximum number of threads that can be used to '
                    'execute audits in parallel.'),
    cfg.IntOpt('max_general_workers',
               default=4,
               required=True,
               help='The maximum number of threads that can be used to '
                    'execute general tasks in parallel. The number of general '
                    'workers will not increase depending on the number of '
                    'audit workers!'),
    cfg.IntOpt('action_plan_expiry',
               default=24,
               mutable=True,
               help='An expiry timespan(hours). Watcher invalidates any '
                    'action plan for which its creation time '
                    '-whose number of hours has been offset by this value-'
                    ' is older that the current time.'),
    cfg.IntOpt('check_periodic_interval',
               default=30 * 60,
               mutable=True,
               help='Interval (in seconds) for checking action plan expiry.'),
    cfg.StrOpt('metric_map_path',
               default='/etc/watcher/metric_map.yaml',
               help='Path to metric map yaml formatted file. '
                    ' '
                    'The file contains a map per datasource whose keys '
                    'are the metric names as recognized by watcher and the '
                    'value is the real name of the metric in the datasource. '
                    'For example:: \n\n'
                    '  monasca:\n'
                    '    instance_cpu_usage: VM_CPU\n'
                    '  gnocchi:\n'
                    '    instance_cpu_usage: cpu_vm_util\n\n'
                    'This file is optional.'),
    cfg.IntOpt('continuous_audit_interval',
               default=10,
               mutable=True,
               help='Interval (in seconds) for checking newly created '
                    'continuous audits.')]


def register_opts(conf):
    conf.register_group(watcher_decision_engine)
    conf.register_opts(WATCHER_DECISION_ENGINE_OPTS,
                       group=watcher_decision_engine)


def list_opts():
    return [(watcher_decision_engine, WATCHER_DECISION_ENGINE_OPTS)]
