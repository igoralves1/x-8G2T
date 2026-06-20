# =============================================================================
# MQTT -> Kafka bridge.
# Open-source EMQX has no built-in Kafka sink, so this tiny service subscribes
# to device telemetry on the broker and produces normalised per-metric records
# into the Kafka `raw-telemetry` topic for Flink to consume.
# =============================================================================
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bridge.py .
CMD ["python", "bridge.py"]
