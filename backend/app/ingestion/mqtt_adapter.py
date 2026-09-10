"""
Real MQTT ingestion adapter -- subscribes to a Mosquitto broker and
collects real sensor readings published on
`rahat/zones/<zone_id>/<event_type>` topics. Demonstrated against a
real, running Mosquitto broker (docker-compose.yml's `mqtt` service
locally, a Mosquitto service container in CI) via a real publish/
subscribe round trip, the same "prove it against something real"
standard http_adapter.py met with live Open-Meteo calls -- not just a
mocked client.

Not wired into the live tick loop yet, for the same reason
http_adapter.py isn't: SyntheticFloodAdapter's determinism is what the
tick loop and its tests are built around. This adapter is ready for a
real publisher (a real gauge, a bridge from a municipal feed) whenever
one exists.
"""
import json
import queue
import time

from datetime import datetime, timezone

import paho.mqtt.client as mqtt

from app.ingestion.base import AbstractIngestionAdapter, NormalizedEvent

TOPIC_FILTER = "rahat/zones/+/+"


class MqttSensorAdapter(AbstractIngestionAdapter):
    source_name = "mqtt"

    def __init__(self, broker_host: str, broker_port: int = 1883,
                 collect_seconds: float = 2.0, simulation_run_id: int | None = None):
        """Connects fresh for each poll_or_receive() call rather than
        holding a persistent connection -- this adapter is polled
        alongside the other batch-oriented adapters (see
        AbstractIngestionAdapter), so it collects whatever real
        messages arrive in a short window rather than streaming
        continuously."""
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.collect_seconds = collect_seconds
        self.simulation_run_id = simulation_run_id

    def poll_or_receive(self) -> list[dict]:
        received: queue.Queue = queue.Queue()

        def on_message(client, userdata, msg):
            parts = msg.topic.split("/")
            try:
                zone_id = int(parts[2])
                event_type = parts[3]
                payload = json.loads(msg.payload.decode())
                value = float(payload["value"])
            except (IndexError, ValueError, KeyError, json.JSONDecodeError):
                # A malformed reading from one publisher shouldn't
                # drop the rest of the batch.
                return
            received.put({
                "zone_id": zone_id,
                "event_type": event_type,
                "value": value,
                "raw": payload,
            })

        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        client.on_message = on_message
        try:
            client.connect(self.broker_host, self.broker_port, keepalive=int(self.collect_seconds) + 5)
        except (ConnectionRefusedError, OSError):
            # A live broker being unreachable shouldn't crash a tick --
            # treat it the same as "no readings this round".
            return []
        client.subscribe(TOPIC_FILTER)
        client.loop_start()
        time.sleep(self.collect_seconds)
        client.loop_stop()
        client.disconnect()

        readings = []
        while not received.empty():
            readings.append(received.get_nowait())
        return readings

    def normalize(self, raw: dict) -> NormalizedEvent:
        return NormalizedEvent(
            source=self.source_name,
            zone_id=raw["zone_id"],
            event_type=raw["event_type"],
            value=raw["value"],
            confidence=float(raw["raw"].get("confidence", 0.85)),
            observed_at=datetime.now(timezone.utc),
            provenance={"broker": f"{self.broker_host}:{self.broker_port}", "raw": raw["raw"]},
            simulation_run_id=self.simulation_run_id,
        )
