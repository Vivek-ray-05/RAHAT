"""
Tests mqtt_adapter.py against a real, running Mosquitto broker --
`docker-compose.yml`'s `mqtt` service locally, a Mosquitto service
container in CI -- via genuine publish/subscribe round trips, not a
mocked MQTT client. MQTT_BROKER_HOST/MQTT_BROKER_PORT let this point
at either.

MQTT (QoS 0, no retained messages here) only delivers to a client
that's already subscribed -- publishing before the adapter has
connected loses the message, same as it would for a real subscriber.
So every test publishes from a background thread a moment *after*
calling poll_or_receive(), not before.
"""
import json
import os
import threading
import time

import paho.mqtt.publish as mqtt_publish
import pytest

from app.ingestion.mqtt_adapter import MqttSensorAdapter

BROKER_HOST = os.environ.get("MQTT_BROKER_HOST", "localhost")
BROKER_PORT = int(os.environ.get("MQTT_BROKER_PORT", "1883"))
PUBLISH_DELAY_SECONDS = 0.4


def _publish(zone_id: int, event_type: str, payload) -> None:
    body = payload if isinstance(payload, str) else json.dumps(payload)
    mqtt_publish.single(f"rahat/zones/{zone_id}/{event_type}", body, hostname=BROKER_HOST, port=BROKER_PORT)


def _poll_while_publishing(adapter: MqttSensorAdapter, messages: list[tuple[int, str, object]]) -> list[dict]:
    """Runs the real publishes on a delay in the background while the
    adapter's poll_or_receive() is already connected and subscribed,
    then returns what it actually received."""
    def publish_after_delay():
        time.sleep(PUBLISH_DELAY_SECONDS)
        for zone_id, event_type, payload in messages:
            _publish(zone_id, event_type, payload)

    thread = threading.Thread(target=publish_after_delay)
    thread.start()
    readings = adapter.poll_or_receive()
    thread.join()
    return readings


@pytest.fixture()
def adapter():
    return MqttSensorAdapter(broker_host=BROKER_HOST, broker_port=BROKER_PORT, collect_seconds=1.5)


def test_poll_or_receive_gets_a_real_published_reading(adapter):
    readings = _poll_while_publishing(adapter, [(1, "rainfall_mm", {"value": 6.5, "confidence": 0.9})])

    assert len(readings) == 1
    assert readings[0]["zone_id"] == 1
    assert readings[0]["event_type"] == "rainfall_mm"
    assert readings[0]["value"] == 6.5


def test_normalize_produces_a_valid_event_with_real_provenance(adapter):
    readings = _poll_while_publishing(adapter, [(2, "water_level_m", {"value": 1.1, "confidence": 0.95})])
    event = adapter.normalize(readings[0])

    assert event.source == "mqtt"
    assert event.zone_id == 2
    assert event.value == 1.1
    assert event.confidence == 0.95
    assert event.provenance["broker"] == f"{BROKER_HOST}:{BROKER_PORT}"


def test_missing_confidence_falls_back_to_a_default(adapter):
    readings = _poll_while_publishing(adapter, [(3, "rainfall_mm", {"value": 2.0})])
    event = adapter.normalize(readings[0])

    assert event.confidence == 0.85


def test_multiple_zones_each_get_their_own_reading(adapter):
    readings = _poll_while_publishing(adapter, [
        (4, "rainfall_mm", {"value": 3.3}),
        (5, "water_level_m", {"value": 0.9}),
    ])

    assert len(readings) == 2
    assert {r["zone_id"] for r in readings} == {4, 5}


def test_malformed_message_is_skipped_not_raised(adapter):
    readings = _poll_while_publishing(adapter, [
        (6, "rainfall_mm", "not json"),
        (6, "rainfall_mm", {"value": 4.4}),
    ])

    assert len(readings) == 1
    assert readings[0]["value"] == 4.4


def test_unreachable_broker_is_skipped_not_raised():
    adapter = MqttSensorAdapter(broker_host="localhost", broker_port=1, collect_seconds=0.5)

    readings = adapter.poll_or_receive()

    assert readings == []


def test_ingest_persists_a_real_sensor_event_row(session, make_run, make_zone, adapter):
    run = make_run()
    zone = make_zone()
    adapter.simulation_run_id = run.id

    rows_source = _poll_while_publishing(adapter, [(zone.id, "rainfall_mm", {"value": 5.5, "confidence": 0.88})])
    assert len(rows_source) == 1  # sanity: the real publish arrived before persisting

    rows = [adapter.ingest(session, raw) for raw in rows_source]

    assert len(rows) == 1
    assert rows[0].id is not None
    assert rows[0].source_adapter == "mqtt"
    assert rows[0].zone_id == zone.id
    assert rows[0].value == 5.5
    assert rows[0].confidence == 0.88
