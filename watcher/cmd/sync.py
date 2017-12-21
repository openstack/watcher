# -*- encoding: utf-8 -*-
#
# Copyright (c) 2016 Intel
#
# Authors: Tomasz Kaczynski <tomasz.kaczynski@intel.com>
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Script for the sync tool."""

import sys

from oslo_log import log

from watcher.common import service
from watcher import conf
from watcher.decision_engine import sync

LOG = log.getLogger(__name__)
CONF = conf.CONF


def main():
    LOG.info('Watcher sync started.')

    service.prepare_service(sys.argv, CONF)
    syncer = sync.Syncer()
    syncer.sync()

    LOG.info('Watcher sync finished.')
