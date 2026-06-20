#!/usr/bin/env python3
"""Simulate an edge device publishing telemetry to the Jetson board.

This represents ENVIRONMENT 1 (the devices). Run it from any machine that can
reach the Jetson's EMQX broker.

Plain (dev) connection:
    python3 simulate-device.py --device sensor_001 --metric temperature

TLS connection (production), using the certs from ssl/generate-certs.sh:
    python3 simulate-device.py --host <jetson-ip> --tls \
        --ca ../ssl/ca.crt --cert ../ssl/client.crt --key ../ssl/client.key \
        --device sensor_001 --metric temperature
"""
from __future__ import annotations

import argparse
import json
import random
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="X-8G2T device simulator")
    p.add_argument("--host", default="localhost")
    p.add_argument("--port", type=int, default=1883)
    p.add_argument("--device", default="sensor_001")
    p.add_argument("--metric", default="temperature")
    p.add_argument("--base", type=float, default=4.0, help="baseline value")
    p.add_argument("--noise", type=float, default=0.5)
    p.add_argument("--interval", type=float, default=2.0, help="seconds between samples")
    p.add_argument("--spike-prob", type=float, default=0.05,
                   help="probability of injecting an anomalous spike")
    p.add_argument("--tls", action="store_true")
    p.add_argument("--ca"); p.add_argument("--cert"); p.add_argument("--key")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                         client_id=f"sim-{args.device}")
    if args.tls:
        client.tls_set(ca_certs=args.ca, certfile=args.cert, keyfile=args.key)
        if args.port == 1883:
            args.port = 8883
    client.connect(args.host, args.port, keepalive=60)
    client.loop_start()

    topic = f"telemetry/{args.device}"
    print(f"Publishing {args.metric} for {args.device} -> mqtt://{args.host}:{args.port}/{topic}")
    try:
        while True:
            value = args.base + random.gauss(0, args.noise)
            if random.random() < args.spike_prob:
                value += random.uniform(5, 12)   # anomalous spike
                print("  ! injected anomaly")
            payload = {
                "device_id": args.device,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "metrics": {args.metric: round(value, 3)},
            }
            client.publish(topic, json.dumps(payload), qos=1)
            print(f"  -> {payload['metrics']}")
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nstopping...")
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
