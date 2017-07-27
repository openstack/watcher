#    Copyright 2013 IBM Corp.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

# NOTE(comstud): You may scratch your head as you see code that imports
# this module and then accesses attributes for objects such as Node,
# etc, yet you do not see these attributes in here. Never fear, there is
# a little bit of magic. When objects are registered, an attribute is set
# on this module automatically, pointing to the newest/latest version of
# the object.


def register_all():
    # NOTE(danms): You must make sure your object gets imported in this
    # function in order for it to be registered by services that may
    # need to receive it via RPC.
    __import__('watcher.objects.goal')
    __import__('watcher.objects.strategy')
    __import__('watcher.objects.audit_template')
    __import__('watcher.objects.audit')
    __import__('watcher.objects.action_plan')
    __import__('watcher.objects.action')
    __import__('watcher.objects.efficacy_indicator')
    __import__('watcher.objects.scoring_engine')
    __import__('watcher.objects.service')
    __import__('watcher.objects.action_description')
