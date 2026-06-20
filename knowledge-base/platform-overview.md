# X-8G2T Platform Operations Notes (global)

This document is global context available to all agents.

## What the platform does
Edge devices publish telemetry over MQTT/TLS to a Jetson Orin Nano. Flink
processes the stream, IoTDB stores time-series, PostgreSQL stores metadata and
alarms, and a multi-agent system backed by a local LLM and a RAG knowledge base
performs root-cause analysis and recommends actions.

## Escalation policy
- **info**: recorded only, no notification.
- **warning**: notify the on-shift operator.
- **critical**: page the maintenance lead and create a work order.

## Maintenance windows
Planned maintenance runs Tuesdays 02:00–04:00 local time. Avoid raising
non-critical alarms that recommend immediate dispatch during this window;
prefer scheduling the work for the window instead.

## Data retention
Raw telemetry in IoTDB is retained for 30 days; downsampled (hourly) data for
1 year. Alarms and agent investigations are retained indefinitely in PostgreSQL.
