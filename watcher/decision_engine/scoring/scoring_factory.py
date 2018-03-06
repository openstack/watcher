# -*- encoding: utf-8 -*-
# Copyright (c) 2016 Intel
#
# Authors: Tomasz Kaczynski <tomasz.kaczynski@intel.com>
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

"""
A module providing helper methods to work with Scoring Engines.
"""

from oslo_log import log

from watcher._i18n import _
from watcher.decision_engine.loading import default


LOG = log.getLogger(__name__)

_scoring_engine_map = None


def get_scoring_engine(scoring_engine_name):
    """Returns a Scoring Engine by its name.

    Method retrieves a Scoring Engine instance by its name. Scoring Engine
    instances are being cached in memory to avoid enumerating the Stevedore
    plugins on each call.

    When called for the first time, it reloads the cache.

    :return: A Scoring Engine instance with a given name
    :rtype: :class:
        `watcher.decision_engine.scoring.scoring_engine.ScoringEngine`
    """
    global _scoring_engine_map

    _reload_scoring_engines()
    scoring_engine = _scoring_engine_map.get(scoring_engine_name)
    if scoring_engine is None:
        raise KeyError(_('Scoring Engine with name=%s not found')
                       % scoring_engine_name)

    return scoring_engine


def get_scoring_engine_list():
    """Returns a list of Scoring Engine instances.

    The main use case for this method is discoverability, so the Scoring
    Engine list is always reloaded before returning any results.

    Frequent calling of this method might have a negative performance impact.

    :return: A list of all available Scoring Engine instances
    :rtype: List of :class:
        `watcher.decision_engine.scoring.scoring_engine.ScoringEngine`
    """
    global _scoring_engine_map

    _reload_scoring_engines(True)
    return _scoring_engine_map.values()


def _reload_scoring_engines(refresh=False):
    """Reloads Scoring Engines from Stevedore plugins to memory.

    Please note that two Stevedore entry points are used:
    - watcher_scoring_engines: for simple plugin implementations
    - watcher_scoring_engine_containers: for container plugins, which enable
      the dynamic scenarios (its get_scoring_engine_list method might return
      different values on each call)
    """
    global _scoring_engine_map

    if _scoring_engine_map is None or refresh:
        LOG.debug("Reloading Scoring Engine plugins")
        engines = default.DefaultScoringLoader().list_available()
        _scoring_engine_map = dict()

        for name in engines.keys():
            se_impl = default.DefaultScoringLoader().load(name)
            LOG.debug("Found Scoring Engine plugin: %s", se_impl.get_name())
            _scoring_engine_map[se_impl.get_name()] = se_impl

        engine_containers = \
            default.DefaultScoringContainerLoader().list_available()

        for container_id, container_cls in engine_containers.items():
            LOG.debug("Found Scoring Engine container plugin: %s",
                      container_id)
            for se in container_cls.get_scoring_engine_list():
                LOG.debug("Found Scoring Engine plugin: %s",
                          se.get_name())
                _scoring_engine_map[se.get_name()] = se
