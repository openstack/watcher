# Copyright 2026 Red Hat, Inc.
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

from watcher.decision_engine.datasources.cache import MetricCacheKey
from watcher.decision_engine.datasources.cache import MetricDataCache
from watcher.tests.unit import base


class TestMetricCacheKey(base.TestCase):
    def test_generate_produces_five_part_key(self):
        key = MetricCacheKey.generate(
            'res-uuid', 'host_cpu_usage', 'mean', 300, 300
        )
        parts = key.split(':')
        self.assertEqual(5, len(parts))
        self.assertEqual('res-uuid', parts[0])
        self.assertEqual('host_cpu_usage', parts[1])
        self.assertEqual('mean', parts[2])
        self.assertEqual('300', parts[3])
        self.assertEqual('300', parts[4])

    def test_different_aggregates_produce_different_keys(self):
        key_mean = MetricCacheKey.generate('r', 'm', 'mean', 300, 300)
        key_max = MetricCacheKey.generate('r', 'm', 'max', 300, 300)
        self.assertNotEqual(key_mean, key_max)

    def test_different_periods_produce_different_keys(self):
        key_300 = MetricCacheKey.generate('r', 'm', 'mean', 300, 300)
        key_600 = MetricCacheKey.generate('r', 'm', 'mean', 600, 300)
        self.assertNotEqual(key_300, key_600)

    def test_different_granularities_produce_different_keys(self):
        key_60 = MetricCacheKey.generate('r', 'm', 'mean', 300, 60)
        key_300 = MetricCacheKey.generate('r', 'm', 'mean', 300, 300)
        self.assertNotEqual(key_60, key_300)


class TestMetricDataCache(base.TestCase):
    def setUp(self):
        super().setUp()
        self.cache = MetricDataCache()

    # ------------------------------------------------------------------
    # get / put
    # ------------------------------------------------------------------

    def test_get_returns_none_on_miss(self):
        self.assertIsNone(self.cache.get('no-such-resource', 'host_cpu_usage'))

    def test_put_and_get_roundtrip(self):
        self.cache.put('host-1', 'host_cpu_usage', 42.0)
        self.assertEqual(42.0, self.cache.get('host-1', 'host_cpu_usage'))

    def test_get_respects_all_key_dimensions(self):
        self.cache.put(
            'host-1',
            'host_cpu_usage',
            10.0,
            aggregate='mean',
            period=300,
            granularity=300,
        )
        # Different aggregate → different key → miss
        self.assertIsNone(
            self.cache.get(
                'host-1',
                'host_cpu_usage',
                aggregate='max',
                period=300,
                granularity=300,
            )
        )
        # Different period → miss
        self.assertIsNone(
            self.cache.get(
                'host-1',
                'host_cpu_usage',
                aggregate='mean',
                period=600,
                granularity=300,
            )
        )

    def test_put_overwrites_existing_value(self):
        self.cache.put('host-1', 'host_cpu_usage', 10.0)
        self.cache.put('host-1', 'host_cpu_usage', 99.0)
        self.assertEqual(99.0, self.cache.get('host-1', 'host_cpu_usage'))

    # ------------------------------------------------------------------
    # simulated flag
    # ------------------------------------------------------------------

    def test_put_real_value_not_marked_simulated(self):
        self.cache.put('host-1', 'host_cpu_usage', 20.0, simulated=False)
        self.assertFalse(self.cache.is_simulated('host-1', 'host_cpu_usage'))

    def test_put_simulated_value_is_marked(self):
        self.cache.put('host-1', 'host_cpu_usage', 20.0, simulated=True)
        self.assertTrue(self.cache.is_simulated('host-1', 'host_cpu_usage'))

    def test_is_simulated_returns_false_on_miss(self):
        self.assertFalse(self.cache.is_simulated('no-such', 'host_cpu_usage'))

    # ------------------------------------------------------------------
    # clear / clear_simulated
    # ------------------------------------------------------------------

    def test_clear_removes_all_entries(self):
        self.cache.put('host-1', 'host_cpu_usage', 10.0)
        self.cache.put('host-2', 'host_ram_usage', 5.0, simulated=True)
        self.cache.clear()
        self.assertEqual(0, len(self.cache))
        self.assertIsNone(self.cache.get('host-1', 'host_cpu_usage'))

    def test_clear_simulated_removes_only_simulated(self):
        self.cache.put('host-1', 'host_cpu_usage', 10.0, simulated=False)
        self.cache.put('host-1', 'host_ram_usage', 5.0, simulated=True)
        self.cache.clear_simulated()
        # Real value preserved
        self.assertEqual(10.0, self.cache.get('host-1', 'host_cpu_usage'))
        # Simulated value removed
        self.assertIsNone(self.cache.get('host-1', 'host_ram_usage'))
        # Simulated flag cleared
        self.assertFalse(self.cache.is_simulated('host-1', 'host_cpu_usage'))

    # ------------------------------------------------------------------
    # remove
    # ------------------------------------------------------------------

    def test_remove_by_resource_id_removes_all_its_metrics(self):
        self.cache.put('host-1', 'host_cpu_usage', 10.0)
        self.cache.put('host-1', 'host_ram_usage', 5.0)
        self.cache.put('host-2', 'host_cpu_usage', 20.0)
        self.cache.remove('host-1')
        self.assertIsNone(self.cache.get('host-1', 'host_cpu_usage'))
        self.assertIsNone(self.cache.get('host-1', 'host_ram_usage'))
        # Other resource unaffected
        self.assertEqual(20.0, self.cache.get('host-2', 'host_cpu_usage'))

    def test_remove_with_meter_name_removes_only_that_metric(self):
        self.cache.put('host-1', 'host_cpu_usage', 10.0)
        self.cache.put('host-1', 'host_ram_usage', 5.0)
        self.cache.remove('host-1', meter_name='host_cpu_usage')
        self.assertIsNone(self.cache.get('host-1', 'host_cpu_usage'))
        self.assertEqual(5.0, self.cache.get('host-1', 'host_ram_usage'))

    def test_remove_nonexistent_resource_is_noop(self):
        self.cache.put('host-1', 'host_cpu_usage', 10.0)
        self.cache.remove('no-such-host')
        self.assertEqual(10.0, self.cache.get('host-1', 'host_cpu_usage'))

    # ------------------------------------------------------------------
    # __len__ / __contains__
    # ------------------------------------------------------------------

    def test_len_empty_cache(self):
        self.assertEqual(0, len(self.cache))

    def test_len_after_puts(self):
        self.cache.put('host-1', 'host_cpu_usage', 10.0)
        self.cache.put('host-1', 'host_ram_usage', 5.0)
        self.assertEqual(2, len(self.cache))

    def test_contains_with_raw_key(self):
        self.cache.put('host-1', 'host_cpu_usage', 10.0)
        key = MetricCacheKey.generate(
            'host-1', 'host_cpu_usage', 'mean', 300, 300
        )
        self.assertIn(key, self.cache)
        self.assertNotIn('nonexistent-key', self.cache)
