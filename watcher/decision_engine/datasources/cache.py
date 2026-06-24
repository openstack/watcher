# Copyright 2026 OpenStack Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Metric Data Cache for Audit Pipeline execution.

The Metric Data Cache stores resource metrics retrieved during pipeline
execution, allowing multiple stages to share metrics and optionally
simulate expected metric values after optimizations.
"""

from oslo_log import log


LOG = log.getLogger(__name__)


class MetricCacheKey:
    """Generates cache keys for metric lookups."""

    @staticmethod
    def generate(resource_id, meter_name, aggregate, period, granularity):
        """Generate a unique cache key for a metric query.

        The key encodes all five dimensions that distinguish a metric
        observation: resource identity, metric name, aggregation method,
        time window (period), and datasource granularity.

        :param resource_id: ID of the resource (usually the resource UUID)
        :param meter_name: Name of the metric
        :param aggregate: Aggregation method
        :param period: Time window in seconds
        :param granularity: Datasource granularity in seconds
        :return: A unique string key
        """
        return ":".join(
            [
                str(resource_id),
                str(meter_name),
                str(aggregate),
                str(period),
                str(granularity),
            ]
        )


class MetricDataCache:
    """Cache for storing and retrieving metric data.

    This cache is used for:
    1. Avoid redundant datasource API calls
    2. Store expected metric values after simulating strategy actions
    3. Share metric data between strategies in a pipeline
    """

    def __init__(self):
        """Initialize the metric cache."""
        self._cache = {}
        self._simulated = {}

    def get(
        self,
        resource_id,
        meter_name,
        aggregate='mean',
        period=300,
        granularity=300,
    ):
        """Retrieve a cached metric value.

        :param resource_id: ID of the resource
        :param meter_name: Name of the metric
        :param aggregate: Aggregation method
        :param period: Time window in seconds
        :param granularity: Datasource granularity in seconds
        :return: Cached value or None if not found
        """
        key = MetricCacheKey.generate(
            resource_id, meter_name, aggregate, period, granularity
        )
        value = self._cache.get(key)
        # NOTE(dviroel): Useful for debugging but may be removed
        #  if generates too much logging.
        if value is not None:
            LOG.debug(
                "MetricDataCache.get: cache hit resource=%s meter=%s "
                "value=%s aggregate=%s period=%s granularity=%s",
                resource_id,
                meter_name,
                value,
                aggregate,
                period,
                granularity,
            )
        else:
            LOG.debug(
                "MetricDataCache.get: cache miss resource=%s meter=%s "
                "aggregate=%s period=%s granularity=%s",
                resource_id,
                meter_name,
                aggregate,
                period,
                granularity,
            )
        return value

    def put(
        self,
        resource_id,
        meter_name,
        value,
        aggregate='mean',
        period=300,
        granularity=300,
        simulated=False,
    ):
        """Store a metric value in the cache.

        :param resource_id: ID of the resource
        :param meter_name: Name of the metric
        :param value: The metric value to cache
        :param aggregate: Aggregation method
        :param period: Time window in seconds
        :param granularity: Datasource granularity in seconds
        :param simulated: True if value is simulated (not from datasource)
        """
        key = MetricCacheKey.generate(
            resource_id, meter_name, aggregate, period, granularity
        )
        self._cache[key] = value
        if simulated:
            self._simulated[key] = True

        # NOTE(dviroel): Useful for debugging but may be removed
        #  if generates too much logging.
        LOG.debug(
            "MetricDataCache.put: resource=%s meter=%s value=%s "
            "aggregate=%s period=%s granularity=%s simulated=%s",
            resource_id,
            meter_name,
            value,
            aggregate,
            period,
            granularity,
            simulated,
        )

    def is_simulated(
        self,
        resource_id,
        meter_name,
        aggregate='mean',
        period=300,
        granularity=300,
    ):
        """Check if a cached value is simulated.

        :return: True if the value was simulated, False otherwise
        """
        key = MetricCacheKey.generate(
            resource_id, meter_name, aggregate, period, granularity
        )
        return self._simulated.get(key, False)

    def remove(self, resource_id, meter_name=None):
        """Remove cached values for a resource.

        Can remove all metrics for a resource, or only a specific metric.

        :param resource_id: ID of the resource
        :param meter_name: Name of the metric (optional filter)
        """
        keys_to_remove = []
        for key in self._cache:
            parts = key.split(":")
            if parts[0] == str(resource_id):
                if meter_name is None or parts[1] == str(meter_name):
                    keys_to_remove.append(key)

        for key in keys_to_remove:
            del self._cache[key]
            self._simulated.pop(key, None)

    def clear(self):
        """Clear all cached values."""
        self._cache.clear()
        self._simulated.clear()

    def clear_simulated(self):
        """Remove only simulated metric values.

        Preserves real datasource-fetched values.
        """
        for key in list(self._simulated):
            self._cache.pop(key, None)
        self._simulated.clear()

    def __len__(self):
        """Return the number of cached items."""
        return len(self._cache)

    def __contains__(self, key):
        """Check if a key exists in the cache."""
        return key in self._cache
