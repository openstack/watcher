# -*- encoding: utf-8 -*-
# Copyright (c) 2015 b<>com
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

# FIXME(jed): remove this class due jenkins build failed
# The following librairies are removed from requirement.txt :
# - numpy
# - matplotlib
# These dependencies required a server x, jenkin's server has no
# server x

# import matplotlib.pyplot as plt
# import numpy as np


from watcher.decision_engine.strategies.basic_consolidation import \
    BasicConsolidation
from watcher.tests.decision_engine.faker_cluster_state import \
    FakerStateCollector
from watcher.tests.decision_engine.faker_metrics_collector import \
    FakerMetricsCollector


class PlotConsolidationBasic(object):
    def plot(self, sercon, orign_model, solution):
        pass

# cluster_size = len(orign_model._hypervisors)
#        labels = []
#        before_score = []
#        after_score = []
#        for hypevisor_id in orign_model.get_all_hypervisors():
#            labels.append(hypevisor_id)
#            hypevisor = orign_model.get_hypervisor_from_id(hypevisor_id)
#            result_before = sercon.calculate_score_node(hypevisor,
#                                                        orign_model)
#            result_after = sercon.calculate_score_node(hypevisor,
#                                                 solution.get_model())
#            before_score.append(float(result_before * 100))
#            if result_after == 0:
#                result_after = 0
#            after_score.append(float(result_after * 100))
#
#        ind = np.arange(cluster_size)  # the x locations for the groups
#        width = 0.35  # the width of the bars
#
#        fig, ax = plt.subplots()
#
#        rects1 = ax.bar(ind, before_score, width, color='b')
#
#        rects2 = ax.bar(ind + width, after_score, width, color='r')
#
#       # add some text for labels, title and axes ticks
#       ax.set_ylabel(
#            'Score of each hypervisor that represent their \
#               utilization level')
#        ax.set_title('Watcher Basic Server consolidation (efficiency ' + str(
#            sercon.get_solution().get_efficiency()) + " %)")
#
#        ax.set_xticks(ind + width)
#        ax.set_xticklabels(labels)
#        ax.set_ylim([0, 140])

#      ax.legend((rects1[0], rects2[0]),
#                  ('Before Consolidation', 'After Consolidation'))

#        def autolabel(rects):
#            # attach some text labels
#            for rect in rects:
#                height = rect.get_height()
#                ax.text(rect.get_x() + rect.get_width() / 2., 1.05 * height,
#                        '%d' % int(height),
#                       ha='center', va='bottom')
#
#        autolabel(rects1)
#        autolabel(rects2)

#        plt.show()


cluster = FakerStateCollector()
metrics = FakerMetricsCollector()
sercon = BasicConsolidation()
sercon.set_metrics_resource_collector(metrics)
# try overbooking ? :) 150 % cpu
sercon.set_threshold_cores(1)
model_cluster = cluster.generate_scenario_1()
solution = sercon.execute(model_cluster)
plot = PlotConsolidationBasic()
plot.plot(sercon, cluster.generate_scenario_1(), solution)
