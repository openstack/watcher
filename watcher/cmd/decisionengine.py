# -*- encoding: utf-8 -*-
#
# Copyright 2013 Hewlett-Packard Development Company, L.P.
# All Rights Reserved.
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

"""Starter script for the Decision Engine manager service."""

import os
import sys

from oslo_config import cfg
from oslo_log import log as logging
from oslo_service import service

from watcher._i18n import _LI
from watcher.common import service as watcher_service
from watcher.decision_engine import manager
from watcher.decision_engine import sync

LOG = logging.getLogger(__name__)
CONF = cfg.CONF


def main():
    watcher_service.prepare_service(sys.argv)

    LOG.info(_LI('Starting Watcher Decision Engine service in PID %s'),
             os.getpid())

    syncer = sync.Syncer()
    syncer.sync()

    de_service = watcher_service.Service(manager.DecisionEngineManager)
    launcher = service.launch(CONF, de_service)
    launcher.wait()
