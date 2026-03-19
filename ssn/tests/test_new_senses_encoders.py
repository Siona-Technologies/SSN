import time

from ssn.senses.sensory_bus import SensoryBus
from ssn.senses.contracts import SensorEnvelope
from ssn.senses.encoders.registry import EncoderRegistry
from ssn.senses.encoders.touch_encoder import TouchEncoder
from ssn.senses.encoders.olfactory_encoder import OlfactoryEncoder
from ssn.senses.encoders.gustatory_encoder import GustatoryEncoder
from ssn.senses.encoders.interoception_encoder import InteroceptionEncoder
from ssn.senses.perception_hub import PerceptionHub, PerceptionHubConfig


def _mk_hub(reg: EncoderRegistry) -> PerceptionHub:
    bus = SensoryBus(max_events_per_stream=10, max_total_events=40)
    return PerceptionHub(
        bus=bus,
        registry=reg,
        config=PerceptionHubConfig(max_events_per_tick=10, trace_enabled=False, world_updates_enabled=False),
    )


def test_touch_encoder_basic_flow():
    reg = EncoderRegistry()
    reg.register("touch_map", TouchEncoder())
    hub = _mk_hub(reg)
    t0 = time.time()

    hub.bus.publish(
        SensorEnvelope(
            sensor_type="touch_map",
            ts=t0 + 0.01,
            device_id="touchpad",
            stream_id="s1",
            payload={"pressure": 0.5, "temperature": 30.0, "pain_level": 0.0},
        )
    )
    report = hub.process_once()
    assert report["status"] == "ok"
    assert report["processed"] >= 1


def test_olfactory_encoder_basic_flow():
    reg = EncoderRegistry()
    reg.register("olfactory_sample", OlfactoryEncoder())
    hub = _mk_hub(reg)
    t0 = time.time()

    hub.bus.publish(
        SensorEnvelope(
            sensor_type="olfactory_sample",
            ts=t0 + 0.01,
            device_id="nose",
            stream_id="s1",
            payload={"channels": [0.1, 0.2, 0.3]},
        )
    )
    report = hub.process_once()
    assert report["status"] == "ok"
    assert report["processed"] >= 1


def test_gustatory_encoder_basic_flow():
    reg = EncoderRegistry()
    reg.register("gustatory_sample", GustatoryEncoder())
    hub = _mk_hub(reg)
    t0 = time.time()

    hub.bus.publish(
        SensorEnvelope(
            sensor_type="gustatory_sample",
            ts=t0 + 0.01,
            device_id="tongue",
            stream_id="s1",
            payload={"sweet": 0.3, "sour": 0.0, "salty": 0.1, "bitter": 0.0, "umami": 0.2},
        )
    )
    report = hub.process_once()
    assert report["status"] == "ok"
    assert report["processed"] >= 1


def test_interoception_encoder_basic_flow():
    reg = EncoderRegistry()
    reg.register("interoceptive_state", InteroceptionEncoder())
    hub = _mk_hub(reg)
    t0 = time.time()

    hub.bus.publish(
        SensorEnvelope(
            sensor_type="interoceptive_state",
            ts=t0 + 0.01,
            device_id="body",
            stream_id="s1",
            payload={"heart_rate": 70, "resp_rate": 15, "temp_core": 36.8, "fatigue": 0.2, "stress": 0.1},
        )
    )
    report = hub.process_once()
    assert report["status"] == "ok"
    assert report["processed"] >= 1

