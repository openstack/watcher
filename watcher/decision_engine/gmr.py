# -*- encoding: utf-8 -*-
# Copyright (c) 2016 b<>com
#
# Authors: Vincent FRANCOISE <vincent.francoise@b-com.com>
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

from oslo_reports import guru_meditation_report as gmr

from watcher._i18n import _
from watcher.decision_engine.model.collector import manager


def register_gmr_plugins():
    """Register GMR plugins that are specific to watcher-decision-engine."""
    gmr.TextGuruMeditation.register_section(_('CDMCs'), show_models)


def show_models():
    """Create a formatted output of all the CDMs

    Mainly used as a Guru Meditation Report (GMR) plugin
    """
    mgr = manager.CollectorManager()

    output = []
    for name, cdmc in mgr.get_collectors().items():
        output.append("")
        output.append("~" * len(name))
        output.append(name)
        output.append("~" * len(name))
        output.append("")

        cdmc_struct = cdmc.cluster_data_model.to_string()
        output.append(cdmc_struct)

    return "\n".join(output)
