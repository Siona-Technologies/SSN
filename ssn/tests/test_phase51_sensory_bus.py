# ssn/tests/test_phase51_sensory_bus.py

import unittest
import time

from ssn.senses.contracts import SensorEnvelope
from ssn.senses.sensory_bus import SensoryBus


class TestPhase51SensoryBus(unittest.TestCase):

    def test_publish_and_recent(self):
        bus = SensoryBus(max_events_per_stream=10, max_total_events=50)

        t0 = time.time()
        for i in range(5):
            bus.publish(
                SensorEnvelope(
                    sensor_type="cctv_frame",
                    ts=t0 + i,
                    device_id="cam01",
                    stream_id="front",
                    payload={"frame": i},
                    privacy="sensitive",
                )
            )

        rec = bus.get_recent(sensor_type="cctv_frame", device_id="cam01", stream_id="front", limit=3)
        self.assertEqual(len(rec), 3)
        self.assertGreaterEqual(rec[0].ts, rec[1].ts)

    def test_window_query(self):
        bus = SensoryBus(max_events_per_stream=10, max_total_events=50)

        t0 = time.time()
        for i in range(10):
            bus.publish(
                SensorEnvelope(
                    sensor_type="imu_sample",
                    ts=t0 + i * 0.01,
                    device_id="imu01",
                    stream_id="base",
                    payload={"ax": i},
                    privacy="internal",
                )
            )

        out = bus.get_window(t_min=t0 + 0.03, t_max=t0 + 0.06, sensor_type="imu_sample", device_id="imu01", limit=100)
        self.assertTrue(all((t0 + 0.03) <= e.ts <= (t0 + 0.06) for e in out))

    def test_per_stream_capacity_drop(self):
        bus = SensoryBus(max_events_per_stream=3, max_total_events=100)

        t0 = time.time()
        for i in range(10):
            bus.publish(
                SensorEnvelope(
                    sensor_type="audio_chunk",
                    ts=t0 + i,
                    device_id="mic01",
                    stream_id="room",
                    payload=b"x",
                    privacy="sensitive",
                )
            )

        stats = bus.stats()
        # only 3 should remain in that stream
        key = "audio_chunk:mic01:room"
        self.assertEqual(stats.per_stream_counts.get(key), 3)
        self.assertGreaterEqual(stats.dropped, 7)

    def test_global_capacity_drop_oldest_across_streams(self):
        bus = SensoryBus(max_events_per_stream=100, max_total_events=5)

        t0 = time.time()
        # interleave 2 streams
        for i in range(6):
            bus.publish(
                SensorEnvelope(
                    sensor_type="vision_frame",
                    ts=t0 + i,
                    device_id="camA" if i % 2 == 0 else "camB",
                    stream_id="s",
                    payload={"i": i},
                    privacy="sensitive",
                )
            )

        stats = bus.stats()
        self.assertEqual(stats.total_events, 5)
        self.assertGreaterEqual(stats.dropped, 1)

        # window should still return in chronological order
        out = bus.get_window(t_min=t0, t_max=t0 + 100, limit=20)
        self.assertTrue(all(out[i].ts <= out[i + 1].ts for i in range(len(out) - 1)))

    def test_prune(self):
        bus = SensoryBus(max_events_per_stream=10, max_total_events=100)
        t0 = time.time()

        for i in range(5):
            bus.publish(
                SensorEnvelope(
                    sensor_type="lidar_scan",
                    ts=t0 + i,
                    device_id="lidar",
                    stream_id="top",
                    payload={"scan": i},
                    privacy="internal",
                )
            )

        removed = bus.prune_older_than(t0 + 3)
        self.assertGreaterEqual(removed, 3)
        rem = bus.get_recent(sensor_type="lidar_scan", device_id="lidar", stream_id="top", limit=20)
        self.assertTrue(all(e.ts >= (t0 + 3) for e in rem))


if __name__ == "__main__":
    unittest.main()
