-- =============================================================================
-- IoTDB schema reference for X-8G2T.
-- IoTDB 1.3 auto-creates timeseries on first insert, so this file is mainly a
-- reference for the path layout and the retention (TTL) policy.
--
-- Apply with:
--   docker compose exec iotdb /iotdb/sbin/start-cli.sh -h iotdb -p 6667 \
--       -u root -pw root -e "$(cat iotdb/conf/schema.sql)"
-- =============================================================================

-- Databases (a.k.a. storage groups)
CREATE DATABASE root.iot.telemetry;
CREATE DATABASE root.iot.aggregated;

-- Path layout used by the bridge / Flink / agent tools:
--   root.iot.telemetry.<external_id>.<metric>
-- Example timeseries (auto-created on insert, shown here for clarity):
CREATE TIMESERIES root.iot.telemetry.sensor_001.temperature WITH DATATYPE=DOUBLE, ENCODING=GORILLA;
CREATE TIMESERIES root.iot.telemetry.sensor_001.humidity    WITH DATATYPE=DOUBLE, ENCODING=GORILLA;
CREATE TIMESERIES root.iot.telemetry.sensor_002.vibration   WITH DATATYPE=DOUBLE, ENCODING=GORILLA;

-- Hourly downsampled rollups produced by Flink:
CREATE TIMESERIES root.iot.aggregated.sensor_001.temperature_1h WITH DATATYPE=DOUBLE, ENCODING=GORILLA;

-- Retention: raw 30 days, aggregated 1 year (milliseconds).
SET TTL TO root.iot.telemetry  2592000000;
SET TTL TO root.iot.aggregated 31536000000;
