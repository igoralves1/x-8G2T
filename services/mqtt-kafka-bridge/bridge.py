#!/usr/bin/env python3
"""MQTT -> Kafka bridge.

Subscribes to device telemetry on EMQX and republishes normalised per-metric
records to the Kafka `raw-telemetry` topic, which Flink consumes.

Expected device payload (published to topic `telemetry/<external_id>`):
    {
      "device_id": "sensor_001",
      "timestamp": "2026-06-19T14:30:00Z",   # optional; epoch-ms also accepted
      "metrics": {"temperature": 7.2, "humidity": 61.0}
    }

Emitted to Kafka (one message per metric):
    {"device_id": "sensor_001", "metric": "temperature", "value": 7.2, "ts": 1750000000000}
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
from kafka import KafkaProducer
from loguru import logger

MQTT_HOST = os.getenv("MQTT_HOST", "emqx")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "telemetry/#")
KAFKA_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "raw-telemetry")


def to_epoch_ms(ts) -> int:
    if ts is None:
        return int(time.time() * 1000)
    if isinstance(ts, (int, float)):
        return int(ts if ts > 1e12 else ts * 1000)
    try:
        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        return int(dt.replace(tzinfo=dt.tzinfo or timezone.utc).timestamp() * 1000)
    except ValueError:
        return int(time.time() * 1000)


def make_producer() -> KafkaProducer:
    for attempt in range(30):
        try:
            return KafkaProducer(
                bootstrap_servers=KAFKA_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode(),
                key_serializer=lambda k: k.encode() if k else None,
                retries=5,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Kafka not ready ({attempt+1}/30): {exc}")
            time.sleep(5)
    raise SystemExit("Could not connect to Kafka")


producer = make_producer()


def on_connect(client, userdata, flags, reason_code, properties=None):
    logger.info(f"Connected to MQTT {MQTT_HOST}:{MQTT_PORT} (rc={reason_code})")
    client.subscribe(MQTT_TOPIC, qos=1)
    logger.info(f"Subscribed to {MQTT_TOPIC}")


def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
    except (json.JSONDecodeError, UnicodeDecodeError):
        logger.warning(f"dropping non-JSON message on {msg.topic}")
        return

    device_id = payload.get("device_id") or msg.topic.split("/")[-1]
    ts = to_epoch_ms(payload.get("timestamp"))
    metrics = payload.get("metrics", {})
    if not isinstance(metrics, dict):
        return

    for metric, value in metrics.items():
        if not isinstance(value, (int, float)):
            continue
        record = {"device_id": device_id, "metric": metric,
                  "value": float(value), "ts": ts}
        producer.send(KAFKA_TOPIC, key=device_id, value=record)
    producer.flush()


def main() -> None:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="mqtt-kafka-bridge")
    client.on_connect = on_connect
    client.on_message = on_message
    while True:
        try:
            client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
            client.loop_forever()
        except Exception as exc:  # noqa: BLE001
            logger.error(f"MQTT loop error: {exc}; reconnecting in 5s")
            time.sleep(5)


if __name__ == "__main__":
    main()
