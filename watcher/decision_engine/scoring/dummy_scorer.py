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

from oslo_log import log
from oslo_serialization import jsonutils
from oslo_utils import units

from watcher._i18n import _
from watcher.decision_engine.scoring import base

LOG = log.getLogger(__name__)


class DummyScorer(base.ScoringEngine):
    """Sample Scoring Engine implementing simplified workload classification.

    Typically a scoring engine would be implemented using machine learning
    techniques. For example, for workload classification problem the solution
    could consist of the following steps:

    1. Define a problem to solve: we want to detect the workload on the
       machine based on the collected metrics like power consumption,
       temperature, CPU load, memory usage, disk usage, network usage, etc.
    2. The workloads could be predefined, e.g. IDLE, CPU-INTENSIVE,
       MEMORY-INTENSIVE, IO-BOUND, ...
       Or we could let the ML algorithm to find the workloads based on the
       learning data provided. The decision here leads to learning algorithm
       used (supervised vs. non-supervised learning).
    3. Collect metrics from sample servers (learning data).
    4. Define the analytical model, pick ML framework and algorithm.
    5. Apply learning data to the data model. Once taught, the data model
       becomes a scoring engine and can start doing predictions or
       classifications.
    6. Wrap up the scoring engine with the class like this one, so it has a
       standard interface and can be used inside Watcher.

    This class is a greatly very simplified version of the above model. The
    goal is to provide an example how such class could be implemented and used
    in Watcher, without adding additional dependencies like machine learning
    frameworks (which can be quite heavy) or over-complicating it's internal
    implementation, which can distract from looking at the overall picture.

    That said, this class implements a workload classification "manually"
    (in plain python code) and is not intended to be used in production.
    """

    # Constants defining column indices for the input data
    PROCESSOR_TIME_PERC = 0
    MEM_TOTAL_BYTES = 1
    MEM_AVAIL_BYTES = 2
    MEM_PAGE_READS_PER_SEC = 3
    MEM_PAGE_WRITES_PER_SEC = 4
    DISK_READ_BYTES_PER_SEC = 5
    DISK_WRITE_BYTES_PER_SEC = 6
    NET_BYTES_RECEIVED_PER_SEC = 7
    NET_BYTES_SENT_PER_SEC = 8

    # Types of workload
    WORKLOAD_IDLE = 0
    WORKLOAD_CPU = 1
    WORKLOAD_MEM = 2
    WORKLOAD_DISK = 3

    def get_name(self):
        return 'dummy_scorer'

    def get_description(self):
        return 'Dummy workload classifier'

    def get_metainfo(self):
        """Metadata about input/output format of this scoring engine.

        This information is used in strategy using this scoring engine to
        prepare the input information and to understand the results.
        """

        return """{
            "feature_columns": [
                "proc-processor-time-%",
                "mem-total-bytes",
                "mem-avail-bytes",
                "mem-page-reads/sec",
                "mem-page-writes/sec",
                "disk-read-bytes/sec",
                "disk-write-bytes/sec",
                "net-bytes-received/sec",
                "net-bytes-sent/sec"],
            "result_columns": [
                "workload",
                "idle-probability",
                "cpu-probability",
                "memory-probability",
                "disk-probability"],
            "workloads": [
                "idle",
                "cpu-intensive",
                "memory-intensive",
                "disk-intensive"]
            }"""

    def calculate_score(self, features):
        """Arbitrary algorithm calculating the score.

        It demonstrates how to parse the input data (features) and serialize
        the results. It detects the workload type based on the metrics and
        also returns the probabilities of each workload detection (again,
        the arbitrary values are returned, just for demonstration how the
        "real" machine learning algorithm could work. For example, the
        Gradient Boosting Machine from H2O framework is using exactly the
        same format:
        http://www.h2o.ai/verticals/algos/gbm/
        """

        LOG.debug('Calculating score, features: %s', features)

        # By default IDLE workload will be returned
        workload = self.WORKLOAD_IDLE
        idle_prob = 0.0
        cpu_prob = 0.0
        mem_prob = 0.0
        disk_prob = 0.0

        # Basic input validation
        try:
            flist = jsonutils.loads(features)
        except Exception as e:
            raise ValueError(_('Unable to parse features: ') % e)
        if type(flist) is not list:
            raise ValueError(_('JSON list expected in feature argument'))
        if len(flist) != 9:
            raise ValueError(_('Invalid number of features, expected 9'))

        # Simple logic for workload classification
        if flist[self.PROCESSOR_TIME_PERC] >= 80:
            workload = self.WORKLOAD_CPU
            cpu_prob = 100.0
        elif flist[self.MEM_PAGE_READS_PER_SEC] >= 1000 \
                and flist[self.MEM_PAGE_WRITES_PER_SEC] >= 1000:
            workload = self.WORKLOAD_MEM
            mem_prob = 100.0
        elif flist[self.DISK_READ_BYTES_PER_SEC] >= 50*units.Mi \
                and flist[self.DISK_WRITE_BYTES_PER_SEC] >= 50*units.Mi:
            workload = self.WORKLOAD_DISK
            disk_prob = 100.0
        else:
            idle_prob = 100.0
            if flist[self.PROCESSOR_TIME_PERC] >= 40:
                cpu_prob = 50.0
            if flist[self.MEM_PAGE_READS_PER_SEC] >= 500 \
                    or flist[self.MEM_PAGE_WRITES_PER_SEC] >= 500:
                mem_prob = 50.0

        return jsonutils.dumps(
            [workload, idle_prob, cpu_prob, mem_prob, disk_prob])
