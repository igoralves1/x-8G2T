#!/usr/bin/env python3
"""X-8G2T Flink telemetry processor (PyFlink Table API).

Reads raw device telemetry from Kafka, validates and enriches it, evaluates
simple threshold rules, and writes two streams back to Kafka:
  * processed-telemetry : clean, normalised readings
  * alerts              : rule violations

Downstream sink connectors (IoTDB / Postgres) can be attached the same way;
this job focuses on the streaming transform that feeds the storage + agent
layers.

Submit after the cluster is up:
  docker compose exec flink-jobmanager \
    flink run -py /opt/flink/usrlib/telemetry_processor.py
"""
from pyflink.table import EnvironmentSettings, TableEnvironment

KAFKA = "kafka:9092"


def build() -> TableEnvironment:
    t_env = TableEnvironment.create(EnvironmentSettings.in_streaming_mode())

    # ---- Source: raw telemetry (JSON) ----
    t_env.execute_sql(f"""
        CREATE TABLE raw_telemetry (
            device_id   STRING,
            `metric`    STRING,
            `value`     DOUBLE,
            `ts`        BIGINT,
            event_time  AS TO_TIMESTAMP_LTZ(`ts`, 3),
            WATERMARK FOR event_time AS event_time - INTERVAL '15' SECOND
        ) WITH (
            'connector' = 'kafka',
            'topic' = 'raw-telemetry',
            'properties.bootstrap.servers' = '{KAFKA}',
            'properties.group.id' = 'flink-telemetry',
            'scan.startup.mode' = 'latest-offset',
            'format' = 'json',
            'json.ignore-parse-errors' = 'true'
        )
    """)

    # ---- Sink: processed telemetry ----
    t_env.execute_sql(f"""
        CREATE TABLE processed_telemetry (
            device_id STRING,
            `metric`  STRING,
            `value`   DOUBLE,
            `ts`      BIGINT
        ) WITH (
            'connector' = 'kafka',
            'topic' = 'processed-telemetry',
            'properties.bootstrap.servers' = '{KAFKA}',
            'format' = 'json'
        )
    """)

    # ---- Sink: alerts ----
    t_env.execute_sql(f"""
        CREATE TABLE alerts (
            device_id STRING,
            `metric`  STRING,
            `value`   DOUBLE,
            severity  STRING,
            message   STRING,
            `ts`      BIGINT
        ) WITH (
            'connector' = 'kafka',
            'topic' = 'alerts',
            'properties.bootstrap.servers' = '{KAFKA}',
            'format' = 'json'
        )
    """)
    return t_env


def main() -> None:
    t_env = build()
    stmt = t_env.create_statement_set()

    # 1) Validate + forward clean readings.
    stmt.add_insert_sql("""
        INSERT INTO processed_telemetry
        SELECT device_id, `metric`, `value`, `ts`
        FROM raw_telemetry
        WHERE device_id IS NOT NULL AND `value` IS NOT NULL
          AND `value` BETWEEN -1e6 AND 1e6
    """)

    # 2) Threshold-based alerting (example rules; the agent layer adds reasoning).
    stmt.add_insert_sql("""
        INSERT INTO alerts
        SELECT device_id, `metric`, `value`,
               CASE WHEN `metric` = 'temperature' AND `value` > 8  THEN 'critical'
                    WHEN `metric` = 'vibration'   AND `value` > 7.1 THEN 'warning'
                    ELSE 'info' END AS severity,
               CONCAT('threshold breach on ', `metric`, ' = ', CAST(`value` AS STRING)) AS message,
               `ts`
        FROM raw_telemetry
        WHERE (`metric` = 'temperature' AND `value` > 8)
           OR (`metric` = 'vibration'   AND `value` > 7.1)
    """)

    stmt.execute()


if __name__ == "__main__":
    main()
