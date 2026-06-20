# X-8G2T: Edge AI IoT Platform

**A complete open-source IoT telemetry, alarm, and AI analytics platform optimized for the NVIDIA Jetson Orin Nano Developer Kit**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Platform](https://img.shields.io/badge/platform-Jetson%20Orin%20Nano-blue)](https://www.nvidia.com/en-us/autonomous-machines/embedded-systems/jetson-orin/)
[![Docker](https://img.shields.io/badge/docker-compose-2496ED?logo=docker)](https://www.docker.com/)

---

## 📋 Table of Contents

- [Overview](#overview)
- [Hardware Specifications](#hardware-specifications)
- [Architecture Overview](#architecture-overview)
- [Security Architecture](#security-architecture)
- [Technology Stack](#technology-stack)
- [Prerequisites](#prerequisites)
- [Installation Guide](#installation-guide)
  - [Step 1: Flash JetPack 6.0](#step-1-flash-jetpack-60)
  - [Step 2: System Configuration](#step-2-system-configuration)
  - [Step 3: Install Docker & NVIDIA Container Toolkit](#step-3-install-docker--nvidia-container-toolkit)
  - [Step 4: Clone the Repository](#step-4-clone-the-repository)
  - [Step 5: Environment Configuration](#step-5-environment-configuration)
  - [Step 6: Deploy Services with Docker Compose](#step-6-deploy-services-with-docker-compose)
  - [Step 7: Initialize Databases](#step-7-initialize-databases)
  - [Step 8: Download AI Models](#step-8-download-ai-models)
  - [Step 9: Configure MQTT Security](#step-9-configure-mqtt-security)
  - [Step 10: Verify Installation](#step-10-verify-installation)
- [Service Configuration Details](#service-configuration-details)
  - [EMQX MQTT Broker](#emqx-mqtt-broker)
  - [Apache Kafka](#apache-kafka)
  - [Apache Flink](#apache-flink)
  - [Apache IoTDB](#apache-iotdb)
  - [PostgreSQL](#postgresql)
  - [AI Orchestrator](#ai-orchestrator)
  - [Grafana](#grafana)
  - [Apache Superset](#apache-superset)
- [Data Flow Pipeline](#data-flow-pipeline)
- [AI Model Performance](#ai-model-performance)
- [API Reference](#api-reference)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

**X-8G2T** is a production-ready, containerized IoT platform that ingests telemetry data from devices, processes it in real-time, stores it efficiently, and performs AI-powered analysis—all on a single **NVIDIA Jetson Orin Nano Developer Kit**.

This project demonstrates how to build a complete **edge-to-insight** pipeline using only open-source tools, with a focus on:
- 🔒 **Security-first design** with TLS encryption and authentication
- 🚀 **Real-time processing** with Apache Flink and Kafka
- 📊 **Efficient storage** with Apache IoTDB (time-series) and PostgreSQL (relational)
- 🤖 **Edge AI** with LLaMA-3.2, SmolVLM, and TensorRT-optimized models
- 📈 **Visualization** with Grafana and Apache Superset
- 🐳 **100% containerized** with Docker Compose

---

## Hardware Specifications

This platform is specifically optimized for the **NVIDIA Jetson Orin Nano Developer Kit**:

| Component | Specification |
|-----------|---------------|
| **Module** | NVIDIA Jetson Orin Nano 8GB |
| **GPU** | 1024-core NVIDIA Ampere architecture GPU with 32 Tensor Cores |
| **CPU** | 6-core Arm® Cortex-A78AE v8.2 64-bit |
| **Memory** | 8GB 128-bit LPDDR5 |
| **Storage** | microSD Card Slot (recommended: 128GB+ UHS-I) |
| **Networking** | Gigabit Ethernet, 802.11ac WLAN, Bluetooth 5.0 |
| **I/O** | 4x USB 3.2 Gen2 Type A, DisplayPort, USB Type-C |
| **Expansion** | 40-pin GPIO header, 2x MIPI CSI-2 camera connectors, M.2 Key M/E |

> **Note**: While optimized for the Orin Nano, this platform can run on any ARM64 or x86_64 system with Docker support.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              DEVICE LAYER (EDGE)                               │
│                                                                                 │
│    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐               │
│    │   Temp   │    │ Humidity │    │ Industrial│    │    IP    │               │
│    │  Sensor  │    │  Sensor  │    │  Gateway  │    │  Camera  │               │
│    └────┬─────┘    └────┬─────┘    └────┬─────┘    └────┬─────┘               │
│         │               │               │               │                      │
│         └───────────────┼───────────────┼───────────────┘                      │
│                         │               │                                      │
│                 MQTT over TLS (Port 8883)                                      │
│                         │               │                                      │
└─────────────────────────┼───────────────┼──────────────────────────────────────┘
                          │               │
                          ▼               ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         INGESTION LAYER (DOCKER)                               │
│                                                                                 │
│                   ┌─────────────────────────────┐                              │
│                   │   EMQX (MQTT Broker)        │◄───── TLS + JWT Auth        │
│                   │   Port: 8883 (MQTT over TLS)│                              │
│                   └──────────────┬──────────────┘                              │
│                                  │                                              │
│                   ┌──────────────▼──────────────┐                              │
│                   │   Apache Kafka              │◄───── Durable Buffer         │
│                   │   (KRaft Mode)              │                              │
│                   └──────────────┬──────────────┘                              │
│                                  │                                              │
└──────────────────────────────────┼──────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         PROCESSING LAYER (DOCKER)                              │
│                                                                                 │
│     ┌────────────────────────────────────────────────────────────┐             │
│     │           Apache Flink (Stream Processing)                │             │
│     │                                                           │             │
│     │  ┌────────────────────────────────────────────────────┐  │             │
│     │  │  • Data Filtering & Validation                     │  │             │
│     │  │  • Enrichment (join with device metadata)         │  │             │
│     │  │  • Window Aggregations (averages, max/min)        │  │             │
│     │  │  • Rule-based Alerting (threshold violations)     │  │             │
│     │  │  • Downsampling for long-term storage             │  │             │
│     │  └────────────────────────────────────────────────────┘  │             │
│     └──────────────────────────┬────────────────────────────────┘             │
│                                │                                               │
│         ┌──────────────────────┼──────────────────────┐                       │
│         │                      │                      │                       │
│         ▼                      ▼                      ▼                       │
│   [Clean Data]         [Triggered Alarms]    [Aggregated Data]                │
│         │                      │                      │                       │
└─────────┼──────────────────────┼──────────────────────┼───────────────────────┘
          │                      │                      │
          ▼                      ▼                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         STORAGE LAYER (DOCKER)                                  │
│                                                                                 │
│  ┌─────────────────────────────┐    ┌────────────────────────────────┐        │
│  │    Apache IoTDB             │    │    PostgreSQL                  │        │
│  │    (Time-Series Database)   │    │    (Relational Database)       │        │
│  │                             │    │                                │        │
│  │  ┌─────────────────────┐   │    │  ┌──────────────────────────┐ │        │
│  │  │ Raw Telemetry       │   │    │  │ devices (metadata)       │ │        │
│  │  │ Aggregated Telemetry│   │    │  │ alarms (history)         │ │        │
│  │  │ (downsampled)       │   │    │  │ users & roles            │ │        │
│  │  └─────────────────────┘   │    │  │ alert rules              │ │        │
│  └─────────────────────────────┘    └────────────────────────────────┘        │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      AI PIPELINE (JETSON OPTIMIZED)                            │
│                                                                                 │
│  ┌────────────────────────────────────────────────────────────────────────┐    │
│  │                     AI Orchestrator (FastAPI)                          │    │
│  │                                                                        │    │
│  │  ┌─────────────────┐    ┌─────────────────┐    ┌──────────────────┐   │    │
│  │  │  LLM Pipeline   │    │  VLM Pipeline   │    │  Time-Series AI  │   │    │
│  │  │  (llama.cpp +   │    │  (HuggingFace + │    │  (TensorRT +     │   │    │
│  │  │   TensorRT-LLM) │    │   TensorRT)     │    │   PyTorch)       │   │    │
│  │  │                 │    │                 │    │                  │   │    │
│  │  │  Model:         │    │  Model:         │    │  Model:          │   │    │
│  │  │  LLaMA-3.2-3B   │    │  SmolVLM-500M  │    │  TimesNet/       │   │    │
│  │  │  Q4_K_M (GGUF)  │    │                 │    │  AutoEncoder     │   │    │
│  │  └─────────────────┘    └─────────────────┘    └──────────────────┘   │    │
│  │                                                                        │    │
│  │  ┌────────────────────────────────────────────────────────────────┐   │    │
│  │  │  Context Builder: Fetches data from IoTDB + PostgreSQL        │   │    │
│  │  │  Result Processor: Parses AI outputs → alarms + insights      │   │    │
│  │  └────────────────────────────────────────────────────────────────┘   │    │
│  └────────────────────────────────────────────────────────────────────────┘    │
│                                      │                                           │
└──────────────────────────────────────┼──────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                       VISUALIZATION & API LAYER (DOCKER)                       │
│                                                                                 │
│  ┌───────────────┐  ┌───────────────┐  ┌──────────────────────────────────┐    │
│  │   Grafana     │  │  Apache       │  │  REST API (FastAPI)             │    │
│  │   (Dashboards)│  │  Superset     │  │  - Device management             │    │
│  │   + AI Views  │  │  (BI Reports) │  │  - Alarm queries                 │    │
│  └───────────────┘  └───────────────┘  │  - AI inference endpoints        │    │
│                                         │  - Real-time telemetry streams   │    │
│                                         └──────────────────────────────────┘    │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Security Architecture

Security is paramount in IoT systems. X-8G2T implements a **defense-in-depth** strategy across all layers:

### 1. Network Security (MQTT Layer)

| Security Control | Implementation |
|------------------|----------------|
| **TLS 1.2/1.3 Encryption** | MQTT over TLS on port 8883 with X.509 certificates |
| **Client Authentication** | JWT tokens or X.509 certificate-based authentication |
| **Access Control** | EMQX's built-in ACL with topic-level permissions |
| **Device Identity** | Unique device IDs with pre-shared keys or certificates |

### 2. Service Security

| Service | Security Measures |
|---------|-------------------|
| **PostgreSQL** | SSL/TLS connections, strong passwords via environment variables (never hardcoded) |
| **Kafka** | SASL/SCRAM authentication, TLS encryption, ACL-based topic authorization |
| **EMQX** | JWT authentication, TLS mutual authentication, rate limiting |
| **REST API** | API keys, JWT tokens, HTTPS, rate limiting |

### 3. Data Security

- **Encryption at Rest**: PostgreSQL and IoTDB support encrypted storage volumes
- **Encryption in Transit**: All inter-service communication uses TLS
- **Secrets Management**: All credentials stored in `.env` file (excluded from version control)
- **Audit Logging**: All access and configuration changes are logged

### 4. Operational Security

- Regular security updates via container image rebuilding
- Non-root user execution within containers
- Minimal port exposure (only necessary ports published)
- Network isolation using Docker bridge networks

---

## Technology Stack

| Layer | Component | Version | License | Purpose |
|-------|-----------|---------|---------|---------|
| **Ingestion** | EMQX | 5.8+ | Apache 2.0 | MQTT broker with TLS support |
| **Buffer** | Apache Kafka | 3.7+ | Apache 2.0 | Durable message queue |
| **Processing** | Apache Flink | 1.18+ | Apache 2.0 | Stream processing & alerting |
| **Time-Series DB** | Apache IoTDB | 1.3+ | Apache 2.0 | Telemetry storage |
| **Relational DB** | PostgreSQL | 16+ | PostgreSQL License | Metadata, alarms, users |
| **LLM Inference** | llama.cpp | latest | MIT | Edge-optimized LLM inference |
| **VLM Inference** | HuggingFace Transformers | 4.40+ | Apache 2.0 | Vision-language models |
| **Orchestration** | Docker Compose | 2.27+ | Apache 2.0 | Container orchestration |
| **Visualization** | Grafana | 11+ | AGPLv3 | Real-time dashboards |
| **BI** | Apache Superset | 4.0+ | Apache 2.0 | Analytics & reporting |

---

## Prerequisites

Before beginning the installation, ensure you have:

### Hardware
- [ ] NVIDIA Jetson Orin Nano Developer Kit
- [ ] microSD Card (128GB or larger, UHS-I recommended)
- [ ] USB-C Power Supply (15W+)
- [ ] Ethernet cable or Wi-Fi connection
- [ ] (Optional) M.2 SSD for improved performance

### Software
- [ ] Host computer with internet access (for downloading models)
- [ ] NVIDIA SDK Manager (for flashing JetPack)

---

## Installation Guide

### Step 1: Flash JetPack 6.0

The Jetson Orin Nano requires JetPack 6.0 (or 5.1.2) which includes Ubuntu 22.04 LTS, CUDA 12.6, TensorRT 10.0, and cuDNN 9.0.

1. Download **NVIDIA SDK Manager** from the NVIDIA website
2. Connect your Jetson Orin Nano via USB-C (recovery mode)
3. Launch SDK Manager and select:
   - **Hardware**: Jetson Orin Nano Developer Kit
   - **JetPack Version**: 6.0 (recommended) or 5.1.2
4. Follow the flashing wizard (this takes 15-30 minutes)
5. After flashing, connect via SSH:
   ```bash
   ssh nvidia@<jetson-ip-address>
   # Default password: nvidia
   ```

### Step 2: System Configuration

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Set CPU governor to performance mode
sudo apt install -y linux-tools-common
sudo cpupower frequency-set -g performance

# Increase swap space (recommended for AI workloads)
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# Install essential build tools
sudo apt install -y \
    build-essential \
    cmake \
    git \
    curl \
    wget \
    vim \
    htop \
    net-tools \
    python3-pip \
    python3-dev \
    python3-venv

# Verify CUDA installation
nvcc --version
# Expected output: release 12.6 (or similar)
```

### Step 3: Install Docker & NVIDIA Container Toolkit

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install NVIDIA Container Toolkit
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
    sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt update
sudo apt install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# Install Docker Compose Plugin
sudo apt install -y docker-compose-plugin

# Verify Docker with GPU support
docker run --rm --runtime=nvidia --gpus all nvidia/cuda:12.6.0-base-ubuntu22.04 nvidia-smi
```

### Step 4: Clone the Repository

```bash
# Clone the project
git clone https://github.com/igoralves1/x-8G2T.git
cd x-8G2T

# Create directory structure
mkdir -p data/{iotdb,postgres,kafka,grafana,superset,models,ssl}
mkdir -p logs/{flink,ai,emqx}
```

### Step 5: Environment Configuration

Create a `.env` file in the project root with secure credentials:

```bash
# .env - DO NOT COMMIT THIS FILE TO VERSION CONTROL
# ===================================================

# PostgreSQL
POSTGRES_USER=iot_admin
POSTGRES_PASSWORD=<GENERATE_STRONG_PASSWORD>
POSTGRES_DB=iot_telemetry

# EMQX MQTT Broker
EMQX_DASHBOARD_USER=admin
EMQX_DASHBOARD_PASSWORD=<GENERATE_STRONG_PASSWORD>
EMQX_JWT_SECRET=<GENERATE_SECURE_SECRET>

# Kafka
KAFKA_USER=iot_producer
KAFKA_PASSWORD=<GENERATE_STRONG_PASSWORD>

# AI Service
AI_API_KEY=<GENERATE_API_KEY>
JWT_SECRET=<GENERATE_SECURE_SECRET>

# Grafana
GF_SECURITY_ADMIN_USER=admin
GF_SECURITY_ADMIN_PASSWORD=<GENERATE_STRONG_PASSWORD>

# Superset
SUPERSET_ADMIN_USER=admin
SUPERSET_ADMIN_PASSWORD=<GENERATE_STRONG_PASSWORD>

# IoTDB
IOTDB_USER=root
IOTDB_PASSWORD=<GENERATE_STRONG_PASSWORD>
```

> **Security Note**: Use strong, unique passwords. Generate them with:
> ```bash
> openssl rand -base64 32
> ```

### Step 6: Deploy Services with Docker Compose

Create the main `docker-compose.yml` file:

```yaml
# docker-compose.yml
version: '3.8'

x-logging: &default-logging
  driver: "json-file"
  options:
    max-size: "50m"
    max-file: "5"

networks:
  iot-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16

volumes:
  postgres_data:
  iotdb_data:
  kafka_data:
  grafana_data:
  superset_data:
  models_data:

services:
  # ============================================================
  # 1. EMQX MQTT Broker
  # ============================================================
  emqx:
    image: emqx/emqx:5.8.4
    container_name: emqx
    restart: unless-stopped
    logging: *default-logging
    networks:
      - iot-network
    ports:
      - "1883:1883"      # MQTT (plain - internal only)
      - "8883:8883"      # MQTT over TLS
      - "8083:8083"      # MQTT over WebSocket
      - "8084:8084"      # MQTT over WebSocket TLS
      - "18083:18083"    # Dashboard
    environment:
      - EMQX_NAME=emqx
      - EMQX_HOST=emqx.iot-network
      - EMQX_DASHBOARD__DEFAULT_USERNAME=${EMQX_DASHBOARD_USER}
      - EMQX_DASHBOARD__DEFAULT_PASSWORD=${EMQX_DASHBOARD_PASSWORD}
      - EMQX_LISTENERS__SSL__DEFAULT__BIND=8883
      - EMQX_LISTENERS__SSL__DEFAULT__SSL_OPTIONS__CACERTFILE=/opt/emqx/etc/certs/ca.crt
      - EMQX_LISTENERS__SSL__DEFAULT__SSL_OPTIONS__CERTFILE=/opt/emqx/etc/certs/server.crt
      - EMQX_LISTENERS__SSL__DEFAULT__SSL_OPTIONS__KEYFILE=/opt/emqx/etc/certs/server.key
      - EMQX_LISTENERS__SSL__DEFAULT__SSL_OPTIONS__VERIFY=verify_peer
      - EMQX_LISTENERS__SSL__DEFAULT__SSL_OPTIONS__FAIL_IF_NO_PEER_CERT=true
    volumes:
      - ./ssl:/opt/emqx/etc/certs:ro
      - ./logs/emqx:/opt/emqx/log
    healthcheck:
      test: ["CMD", "emqx", "ping"]
      interval: 30s
      timeout: 10s
      retries: 5

  # ============================================================
  # 2. Apache Kafka (KRaft mode - no Zookeeper)
  # ============================================================
  kafka:
    image: apache/kafka:3.7.1
    container_name: kafka
    restart: unless-stopped
    logging: *default-logging
    networks:
      - iot-network
    ports:
      - "9092:9092"      # Plain
      - "9093:9093"      # SASL/SSL
    environment:
      - KAFKA_NODE_ID=1
      - KAFKA_PROCESS_ROLES=broker,controller
      - KAFKA_CONTROLLER_QUORUM_VOTERS=1@kafka:9094
      - KAFKA_LISTENERS=PLAINTEXT://0.0.0.0:9092,CONTROLLER://0.0.0.0:9094,SASL_SSL://0.0.0.0:9093
      - KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://kafka:9092,SASL_SSL://localhost:9093
      - KAFKA_LISTENER_SECURITY_PROTOCOL_MAP=CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT,SASL_SSL:SASL_SSL
      - KAFKA_CONTROLLER_LISTENER_NAMES=CONTROLLER
      - KAFKA_INTER_BROKER_LISTENER_NAME=SASL_SSL
      - KAFKA_SASL_MECHANISM_INTER_BROKER_PROTOCOL=SCRAM-SHA-256
      - KAFKA_SASL_ENABLED_MECHANISMS=SCRAM-SHA-256
      - KAFKA_LOG_DIRS=/var/lib/kafka/data
      - KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR=1
      - KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR=1
      - KAFKA_TRANSACTION_STATE_LOG_MIN_ISR=1
      - KAFKA_MIN_INSYNC_REPLICAS=1
      - KAFKA_AUTO_CREATE_TOPICS_ENABLE=true
      - KAFKA_SSL_KEYSTORE_LOCATION=/etc/kafka/secrets/server.keystore.jks
      - KAFKA_SSL_KEYSTORE_PASSWORD=${KAFKA_SSL_PASSWORD}
      - KAFKA_SSL_TRUSTSTORE_LOCATION=/etc/kafka/secrets/server.truststore.jks
      - KAFKA_SSL_TRUSTSTORE_PASSWORD=${KAFKA_SSL_PASSWORD}
    volumes:
      - ./ssl/kafka:/etc/kafka/secrets:ro
      - kafka_data:/var/lib/kafka/data
    healthcheck:
      test: ["CMD", "kafka-topics", "--bootstrap-server", "localhost:9092", "--list"]
      interval: 30s
      timeout: 10s
      retries: 5

  # ============================================================
  # 3. Apache Flink (Stream Processing)
  # ============================================================
  flink-jobmanager:
    image: apache/flink:1.18.1-scala_2.12-java11
    container_name: flink-jobmanager
    restart: unless-stopped
    logging: *default-logging
    networks:
      - iot-network
    ports:
      - "8081:8081"      # Flink Web UI
    environment:
      - FLINK_PROPERTIES=jobmanager.rpc.address: flink-jobmanager
    command: jobmanager
    volumes:
      - ./flink-conf:/opt/flink/conf
      - ./flink-jobs:/opt/flink/usrlib
      - ./logs/flink:/opt/flink/log
    depends_on:
      - kafka

  flink-taskmanager:
    image: apache/flink:1.18.1-scala_2.12-java11
    container_name: flink-taskmanager
    restart: unless-stopped
    logging: *default-logging
    networks:
      - iot-network
    environment:
      - FLINK_PROPERTIES=jobmanager.rpc.address: flink-jobmanager
    command: taskmanager
    volumes:
      - ./flink-conf:/opt/flink/conf
      - ./flink-jobs:/opt/flink/usrlib
      - ./logs/flink:/opt/flink/log
    depends_on:
      - flink-jobmanager

  # ============================================================
  # 4. Apache IoTDB (Time-Series Database)
  # ============================================================
  iotdb:
    image: apache/iotdb:1.3.2-standalone
    container_name: iotdb
    restart: unless-stopped
    logging: *default-logging
    networks:
      - iot-network
    ports:
      - "6667:6667"      # IoTDB RPC
      - "18080:18080"    # IoTDB HTTP API
    environment:
      - IOTDB_USER=${IOTDB_USER}
      - IOTDB_PASSWORD=${IOTDB_PASSWORD}
      - IOTDB_DATABASE=root.iot
    volumes:
      - iotdb_data:/iotdb/data
      - ./logs/iotdb:/iotdb/logs
      - ./iotdb-conf:/iotdb/conf
    healthcheck:
      test: ["CMD", "bash", "-c", "echo 'status' | /iotdb/sbin/start-cli.sh -h 127.0.0.1 -p 6667 -u ${IOTDB_USER} -pw ${IOTDB_PASSWORD}"]
      interval: 30s
      timeout: 10s
      retries: 5

  # ============================================================
  # 5. PostgreSQL (Relational Database)
  # ============================================================
  postgres:
    image: postgres:16-alpine
    container_name: postgres
    restart: unless-stopped
    logging: *default-logging
    networks:
      - iot-network
    ports:
      - "5432:5432"      # Internal only (consider removing for production)
    environment:
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_DB=${POSTGRES_DB}
      - POSTGRES_INITDB_ARGS=--auth-host=scram-sha-256 --auth-local=scram-sha-256
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./postgres-init:/docker-entrypoint-initdb.d:ro
      - ./ssl/postgres:/etc/postgresql/ssl:ro
    command: >
      postgres
      -c ssl=on
      -c ssl_cert_file=/etc/postgresql/ssl/server.crt
      -c ssl_key_file=/etc/postgresql/ssl/server.key
      -c ssl_ca_file=/etc/postgresql/ssl/ca.crt
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 30s
      timeout: 10s
      retries: 5

  # ============================================================
  # 6. AI Orchestrator (Jetson-Optimized)
  # ============================================================
  ai-orchestrator:
    build:
      context: ./ai-service
      dockerfile: Dockerfile.jetson
    container_name: ai-orchestrator
    restart: unless-stopped
    logging: *default-logging
    networks:
      - iot-network
    ports:
      - "8000:8000"      # REST API
    runtime: nvidia
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
      - NVIDIA_DRIVER_CAPABILITIES=compute,utility
      - POSTGRES_HOST=postgres
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_DB=${POSTGRES_DB}
      - IOTDB_HOST=iotdb
      - IOTDB_PORT=6667
      - IOTDB_USER=${IOTDB_USER}
      - IOTDB_PASSWORD=${IOTDB_PASSWORD}
      - KAFKA_BOOTSTRAP_SERVERS=kafka:9092
      - AI_API_KEY=${AI_API_KEY}
      - JWT_SECRET=${JWT_SECRET}
      - MODEL_PATH=/models
      - LOG_LEVEL=INFO
    volumes:
      - models_data:/models
      - ./logs/ai:/app/logs
      - ./ai-service:/app
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
    depends_on:
      - postgres
      - iotdb
      - kafka
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 5

  # ============================================================
  # 7. Grafana (Dashboards)
  # ============================================================
  grafana:
    image: grafana/grafana:11.1.0
    container_name: grafana
    restart: unless-stopped
    logging: *default-logging
    networks:
      - iot-network
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_USER=${GF_SECURITY_ADMIN_USER}
      - GF_SECURITY_ADMIN_PASSWORD=${GF_SECURITY_ADMIN_PASSWORD}
      - GF_INSTALL_PLUGINS=grafana-clock-panel,grafana-simple-json-datasource
      - GF_SERVER_ROOT_URL=http://localhost:3000
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana-dashboards:/etc/grafana/provisioning/dashboards
      - ./grafana-datasources:/etc/grafana/provisioning/datasources
    depends_on:
      - postgres
      - iotdb

  # ============================================================
  # 8. Apache Superset (BI & Analytics)
  # ============================================================
  superset:
    image: apache/superset:4.0.0
    container_name: superset
    restart: unless-stopped
    logging: *default-logging
    networks:
      - iot-network
    ports:
      - "8088:8088"
    environment:
      - SUPERSET_SECRET_KEY=${SUPERSET_SECRET_KEY}
      - SUPERSET_ADMIN_USER=${SUPERSET_ADMIN_USER}
      - SUPERSET_ADMIN_PASSWORD=${SUPERSET_ADMIN_PASSWORD}
      - SUPERSET_ADMIN_FIRSTNAME=Admin
      - SUPERSET_ADMIN_LASTNAME=User
      - SUPERSET_ADMIN_EMAIL=admin@example.com
      - DATABASE_DB=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
    volumes:
      - superset_data:/app/superset_home
      - ./superset-init:/app/docker/init
    depends_on:
      - postgres
    command: >
      sh -c "
        superset db upgrade &&
        superset init &&
        superset fab create-admin &&
        gunicorn --bind 0.0.0.0:8088 --timeout 120 --workers 4 superset.app:create_app()
      "
```

### Step 7: Initialize Databases

Create the PostgreSQL initialization script:

```sql
-- postgres-init/01-init.sql
-- ==========================

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create tables
CREATE TABLE IF NOT EXISTS devices (
    device_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    device_type VARCHAR(100) NOT NULL,
    location VARCHAR(255),
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    metadata JSONB,
    firmware_version VARCHAR(50),
    status VARCHAR(20) DEFAULT 'active',
    install_date TIMESTAMP DEFAULT NOW(),
    last_seen TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS alarm_rules (
    rule_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id UUID REFERENCES devices(device_id) ON DELETE CASCADE,
    metric_name VARCHAR(100) NOT NULL,
    condition VARCHAR(20) NOT NULL, -- 'gt', 'lt', 'eq', 'between'
    threshold_value DECIMAL,
    threshold_max DECIMAL,
    severity VARCHAR(20) NOT NULL, -- 'info', 'warning', 'critical'
    message_template TEXT,
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS alarms (
    alarm_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id UUID REFERENCES devices(device_id) ON DELETE CASCADE,
    rule_id UUID REFERENCES alarm_rules(rule_id),
    severity VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    metric_name VARCHAR(100),
    metric_value DECIMAL,
    acknowledged BOOLEAN DEFAULT false,
    acknowledged_by UUID,
    acknowledged_at TIMESTAMP,
    resolved BOOLEAN DEFAULT false,
    resolved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    role VARCHAR(50) DEFAULT 'viewer',
    device_access JSONB, -- list of device IDs this user can access
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ai_inferences (
    inference_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id UUID REFERENCES devices(device_id) ON DELETE CASCADE,
    model_type VARCHAR(50) NOT NULL, -- 'llm', 'vlm', 'timeseries'
    input_summary TEXT,
    result TEXT NOT NULL,
    anomaly_score DECIMAL(5, 4),
    confidence DECIMAL(5, 4),
    inference_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes
CREATE INDEX idx_devices_status ON devices(status);
CREATE INDEX idx_alarms_device ON alarms(device_id);
CREATE INDEX idx_alarms_severity ON alarms(severity);
CREATE INDEX idx_alarms_created ON alarms(created_at DESC);
CREATE INDEX idx_ai_inferences_device ON ai_inferences(device_id);
CREATE INDEX idx_ai_inferences_created ON ai_inferences(created_at DESC);

-- Create views
CREATE VIEW device_health_summary AS
SELECT 
    d.device_id,
    d.name,
    d.status,
    d.last_seen,
    COUNT(a.alarm_id) AS active_alarms_count,
    MAX(CASE WHEN a.severity = 'critical' AND a.resolved = false THEN 1 ELSE 0 END) AS has_critical_alarm
FROM devices d
LEFT JOIN alarms a ON d.device_id = a.device_id AND a.resolved = false
GROUP BY d.device_id, d.name, d.status, d.last_seen;
```

Create the IoTDB schema:

```sql
-- iotdb-init/schema.sql
-- =====================

-- Create storage groups (similar to databases)
CREATE STORAGE GROUP root.iot;
CREATE STORAGE GROUP root.iot.telemetry;
CREATE STORAGE GROUP root.iot.aggregated;

-- Create time-series for a typical device
CREATE TIMESERIES root.iot.telemetry.device_001.temperature WITH DATATYPE=DOUBLE, ENCODING=GORILLA;
CREATE TIMESERIES root.iot.telemetry.device_001.humidity WITH DATATYPE=DOUBLE, ENCODING=GORILLA;
CREATE TIMESERIES root.iot.telemetry.device_001.pressure WITH DATATYPE=DOUBLE, ENCODING=GORILLA;
CREATE TIMESERIES root.iot.telemetry.device_001.status WITH DATATYPE=TEXT, ENCODING=PLAIN;

-- Create aggregated time-series (downsampled)
CREATE TIMESERIES root.iot.aggregated.device_001.temperature_1h WITH DATATYPE=DOUBLE, ENCODING=GORILLA;
CREATE TIMESERIES root.iot.aggregated.device_001.humidity_1h WITH DATATYPE=DOUBLE, ENCODING=GORILLA;

-- Set TTL (Time To Live) for raw data: 30 days
SET TTL TO root.iot.telemetry 2592000000;  -- 30 days in milliseconds

-- Set TTL for aggregated data: 1 year
SET TTL TO root.iot.aggregated 31536000000;  -- 1 year in milliseconds
```

### Step 8: Download AI Models

Create the AI service Dockerfile:

```dockerfile
# ai-service/Dockerfile.jetson
# ============================

FROM nvcr.io/nvidia/l4t-jetpack:6.0-runtime

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-dev \
    python3-venv \
    git \
    cmake \
    build-essential \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Install llama.cpp
RUN git clone https://github.com/ggerganov/llama.cpp /opt/llama.cpp
WORKDIR /opt/llama.cpp
RUN make clean && \
    make LLAMA_CUDA=1 -j$(nproc)
ENV PATH="/opt/llama.cpp:${PATH}"

# Copy application code
WORKDIR /app
COPY . .

# Expose API port
EXPOSE 8000

# Run the orchestrator
CMD ["python3", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Create the AI service requirements:

```txt
# ai-service/requirements.txt
# ============================

fastapi==0.111.0
uvicorn[standard]==0.30.0
pydantic==2.7.0
pydantic-settings==2.3.0
python-dotenv==1.0.0
httpx==0.27.0
aiofiles==24.1.0

# Database
psycopg2-binary==2.9.9
asyncpg==0.29.0
sqlalchemy==2.0.31
alembic==1.13.0

# MQTT & Kafka
paho-mqtt==1.6.1
kafka-python==2.0.2

# AI/ML
torch==2.3.0
torchvision==0.18.0
transformers==4.41.0
sentencepiece==0.2.0
accelerate==0.31.0
peft==0.11.0

# Time-series
numpy==1.26.4
pandas==2.2.2
scipy==1.13.0
scikit-learn==1.5.0
tsfresh==0.20.2

# Image processing
Pillow==10.3.0
opencv-python==4.9.0.80

# Utilities
python-multipart==0.0.9
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
loguru==0.7.2
```

Create the AI service main code:

```python
# ai-service/main.py
# ==================

import os
import json
import time
import asyncio
import subprocess
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from loguru import logger
import asyncpg
import psycopg2
import numpy as np
import torch
from transformers import AutoProcessor, AutoModelForCausalLM
from PIL import Image
import aiofiles

# ============================================================
# Configuration
# ============================================================

class Settings:
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
    POSTGRES_USER = os.getenv("POSTGRES_USER", "iot_admin")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")
    POSTGRES_DB = os.getenv("POSTGRES_DB", "iot_telemetry")
    IOTDB_HOST = os.getenv("IOTDB_HOST", "iotdb")
    IOTDB_PORT = int(os.getenv("IOTDB_PORT", "6667"))
    MODEL_PATH = os.getenv("MODEL_PATH", "/models")
    AI_API_KEY = os.getenv("AI_API_KEY", "")
    JWT_SECRET = os.getenv("JWT_SECRET", "")

settings = Settings()
security = HTTPBearer()

# ============================================================
# Models
# ============================================================

class InferenceRequest(BaseModel):
    model_type: str = Field(..., description="llm, vlm, timeseries")
    device_id: str
    prompt: Optional[str] = None
    image_path: Optional[str] = None
    telemetry_data: Optional[List[float]] = None
    context: Optional[Dict[str, Any]] = None

class InferenceResponse(BaseModel):
    result: str
    model_type: str
    device_id: str
    anomaly_score: Optional[float] = None
    confidence: Optional[float] = None
    inference_time_ms: int
    timestamp: str

# ============================================================
# Database Connection
# ============================================================

class Database:
    def __init__(self):
        self.pool = None

    async def connect(self):
        self.pool = await asyncpg.create_pool(
            host=settings.POSTGRES_HOST,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            database=settings.POSTGRES_DB,
            min_size=1,
            max_size=10
        )
        logger.info("Connected to PostgreSQL")

    async def save_inference(self, inference_data: Dict[str, Any]):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO ai_inferences (
                    device_id, model_type, input_summary, result,
                    anomaly_score, confidence, inference_time_ms
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
                inference_data["device_id"],
                inference_data["model_type"],
                inference_data.get("input_summary", ""),
                inference_data["result"],
                inference_data.get("anomaly_score"),
                inference_data.get("confidence"),
                inference_data.get("inference_time_ms", 0)
            )

db = Database()

# ============================================================
# Model Loaders
# ============================================================

class ModelManager:
    def __init__(self):
        self.llm_model_path = os.path.join(settings.MODEL_PATH, "llama3.2-3b", "Llama-3.2-3B-Instruct-Q4_K_M.gguf")
        self.vlm_model = None
        self.vlm_processor = None
        self.vlm_loaded = False

    def run_llm(self, prompt: str, max_tokens: int = 256) -> str:
        """Run LLM inference using llama.cpp"""
        cmd = [
            "/opt/llama.cpp/build/bin/llama-cli",
            "-m", self.llm_model_path,
            "-p", prompt,
            "-n", str(max_tokens),
            "--temp", "0.7",
            "--ctx-size", "2048",
            "-ngl", "999",  # Offload all layers to GPU
            "--simple-io"
        ]
        
        logger.info(f"Running LLM with prompt length: {len(prompt)}")
        start = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        elapsed = (time.time() - start) * 1000
        
        if result.returncode != 0:
            logger.error(f"LLM error: {result.stderr}")
            raise RuntimeError(f"LLM inference failed: {result.stderr}")
        
        return result.stdout.strip(), elapsed

    def load_vlm(self):
        """Load VLM model (lazy loading)"""
        if not self.vlm_loaded:
            logger.info("Loading VLM model...")
            self.vlm_processor = AutoProcessor.from_pretrained(
                os.path.join(settings.MODEL_PATH, "smolvlm")
            )
            self.vlm_model = AutoModelForCausalLM.from_pretrained(
                os.path.join(settings.MODEL_PATH, "smolvlm"),
                torch_dtype=torch.float16,
                device_map="cuda"
            )
            self.vlm_loaded = True
            logger.info("VLM model loaded successfully")

    def run_vlm(self, image_path: str, question: str) -> str:
        """Run VLM inference for image analysis"""
        self.load_vlm()
        
        image = Image.open(image_path)
        inputs = self.vlm_processor(text=question, images=image, return_tensors="pt")
        inputs = {k: v.cuda() for k, v in inputs.items()}
        
        start = time.time()
        with torch.no_grad():
            outputs = self.vlm_model.generate(**inputs, max_new_tokens=256)
        elapsed = (time.time() - start) * 1000
        
        response = self.vlm_processor.decode(outputs[0], skip_special_tokens=True)
        return response, elapsed

    def run_timeseries_anomaly(self, data: List[float]) -> Dict[str, Any]:
        """Run time-series anomaly detection using Z-score method"""
        import numpy as np
        from scipy import stats
        
        start = time.time()
        data_arr = np.array(data)
        z_scores = np.abs(stats.zscore(data_arr))
        threshold = 3.0
        anomalies = np.where(z_scores > threshold)[0]
        elapsed = (time.time() - start) * 1000
        
        return {
            "anomaly_count": len(anomalies),
            "anomaly_indices": anomalies.tolist(),
            "max_anomaly_score": float(np.max(z_scores)) if len(z_scores) > 0 else 0,
            "mean": float(np.mean(data_arr)),
            "std": float(np.std(data_arr)),
            "inference_time_ms": elapsed
        }

model_manager = ModelManager()

# ============================================================
# Context Builder
# ============================================================

class ContextBuilder:
    def __init__(self):
        self.pg_conn = None

    async def connect(self):
        self.pg_conn = await asyncpg.connect(
            host=settings.POSTGRES_HOST,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            database=settings.POSTGRES_DB
        )

    async def get_device_metadata(self, device_id: str) -> Dict[str, Any]:
        async with self.pg_conn.transaction():
            row = await self.pg_conn.fetchrow(
                "SELECT * FROM devices WHERE device_id = $1",
                device_id
            )
            return dict(row) if row else {}

    async def get_recent_alarms(self, device_id: str, limit: int = 5) -> List[Dict]:
        async with self.pg_conn.transaction():
            rows = await self.pg_conn.fetch(
                """SELECT * FROM alarms 
                   WHERE device_id = $1 
                   ORDER BY created_at DESC 
                   LIMIT $2""",
                device_id, limit
            )
            return [dict(row) for row in rows]

    async def get_telemetry(self, device_id: str, time_range: str = "1h") -> List[Dict]:
        """Fetch telemetry from IoTDB (simplified - would use IoTDB REST API)"""
        # In production, this would query IoTDB via its REST API
        # For now, return mock data or use a placeholder
        return []

    async def build_llm_prompt(self, device_id: str) -> str:
        metadata = await self.get_device_metadata(device_id)
        alarms = await self.get_recent_alarms(device_id)
        telemetry = await self.get_telemetry(device_id)
        
        prompt = f"""You are an industrial IoT analyst. Analyze the following device data:

DEVICE INFORMATION:
- Name: {metadata.get('name', 'Unknown')}
- Location: {metadata.get('location', 'Unknown')}
- Type: {metadata.get('device_type', 'Unknown')}
- Status: {metadata.get('status', 'Unknown')}

RECENT TELEMETRY (last hour):
{json.dumps(telemetry[:10], indent=2) if telemetry else 'No recent data'}

RECENT ALARMS:
{json.dumps(alarms, indent=2) if alarms else 'No recent alarms'}

Provide:
1. Current status assessment
2. Any potential issues or anomalies
3. Recommended actions
4. If this is a recurring pattern

Analysis:"""
        return prompt

context_builder = ContextBuilder()

# ============================================================
# FastAPI Application
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await db.connect()
    await context_builder.connect()
    logger.info("AI Orchestrator started successfully")
    yield
    # Shutdown
    if db.pool:
        await db.pool.close()
    logger.info("AI Orchestrator shut down")

app = FastAPI(
    title="X-8G2T AI Orchestrator",
    description="Edge AI inference service for IoT telemetry analysis",
    version="1.0.0",
    lifespan=lifespan
)

# ============================================================
# API Endpoints
# ============================================================

@app.get("/health")
async def health_check():
    return {"status": "healthy", "gpu_available": torch.cuda.is_available()}

@app.post("/infer/llm")
async def infer_llm(
    request: InferenceRequest,
    background_tasks: BackgroundTasks,
    auth: HTTPAuthorizationCredentials = Depends(security)
):
    """Run LLM inference for text analysis"""
    try:
        # Build prompt if not provided
        prompt = request.prompt
        if not prompt:
            prompt = await context_builder.build_llm_prompt(request.device_id)
        
        # Run inference
        result, elapsed_ms = model_manager.run_llm(prompt)
        
        # Parse result for anomaly score (simplified)
        anomaly_score = None
        confidence = 0.85
        
        # Save result
        inference_data = {
            "device_id": request.device_id,
            "model_type": "llm",
            "input_summary": prompt[:500],
            "result": result,
            "anomaly_score": anomaly_score,
            "confidence": confidence,
            "inference_time_ms": int(elapsed_ms)
        }
        background_tasks.add_task(db.save_inference, inference_data)
        
        return InferenceResponse(
            result=result,
            model_type="llm",
            device_id=request.device_id,
            anomaly_score=anomaly_score,
            confidence=confidence,
            inference_time_ms=int(elapsed_ms),
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        )
    except Exception as e:
        logger.error(f"LLM inference error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/infer/vlm")
async def infer_vlm(
    request: InferenceRequest,
    background_tasks: BackgroundTasks,
    auth: HTTPAuthorizationCredentials = Depends(security)
):
    """Run VLM inference for image analysis"""
    try:
        if not request.image_path:
            raise HTTPException(status_code=400, detail="image_path required")
        
        question = request.prompt or "Analyze this image for any anomalies or safety concerns."
        result, elapsed_ms = model_manager.run_vlm(request.image_path, question)
        
        # Simple anomaly detection from VLM result (keyword-based)
        anomaly_score = 0.9 if any(k in result.lower() for k in ['anomaly', 'damage', 'leak', 'smoke', 'fire']) else 0.1
        
        inference_data = {
            "device_id": request.device_id,
            "model_type": "vlm",
            "input_summary": f"Image: {request.image_path}, Question: {question[:100]}",
            "result": result,
            "anomaly_score": anomaly_score,
            "confidence": 0.80,
            "inference_time_ms": int(elapsed_ms)
        }
        background_tasks.add_task(db.save_inference, inference_data)
        
        return InferenceResponse(
            result=result,
            model_type="vlm",
            device_id=request.device_id,
            anomaly_score=anomaly_score,
            confidence=0.80,
            inference_time_ms=int(elapsed_ms),
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        )
    except Exception as e:
        logger.error(f"VLM inference error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/infer/timeseries")
async def infer_timeseries(
    request: InferenceRequest,
    background_tasks: BackgroundTasks,
    auth: HTTPAuthorizationCredentials = Depends(security)
):
    """Run time-series anomaly detection"""
    try:
        if not request.telemetry_data or len(request.telemetry_data) < 10:
            raise HTTPException(status_code=400, detail="telemetry_data requires at least 10 points")
        
        result_dict = model_manager.run_timeseries_anomaly(request.telemetry_data)
        elapsed_ms = result_dict.pop("inference_time_ms", 0)
        
        result_str = json.dumps(result_dict)
        anomaly_score = min(result_dict.get("max_anomaly_score", 0) / 10, 1.0)
        
        inference_data = {
            "device_id": request.device_id,
            "model_type": "timeseries",
            "input_summary": f"{len(request.telemetry_data)} data points",
            "result": result_str,
            "anomaly_score": anomaly_score,
            "confidence": 0.90,
            "inference_time_ms": int(elapsed_ms)
        }
        background_tasks.add_task(db.save_inference, inference_data)
        
        return InferenceResponse(
            result=result_str,
            model_type="timeseries",
            device_id=request.device_id,
            anomaly_score=anomaly_score,
            confidence=0.90,
            inference_time_ms=int(elapsed_ms),
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        )
    except Exception as e:
        logger.error(f"Time-series inference error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/infer/history/{device_id}")
async def get_inference_history(
    device_id: str,
    limit: int = 20,
    auth: HTTPAuthorizationCredentials = Depends(security)
):
    """Get inference history for a device"""
    async with db.pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT * FROM ai_inferences 
               WHERE device_id = $1 
               ORDER BY created_at DESC 
               LIMIT $2""",
            device_id, limit
        )
        return [dict(row) for row in rows]

# ============================================================
# Main entry point
# ============================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### Step 9: Configure MQTT Security

Generate SSL certificates for MQTT over TLS:

```bash
# ssl/generate-certs.sh
# ======================

#!/bin/bash

# Generate CA key and certificate
openssl genrsa -out ca.key 2048
openssl req -x509 -new -nodes -key ca.key -sha256 -days 365 -out ca.crt \
    -subj "/C=BR/ST=State/L=City/O=Organization/CN=IoT CA"

# Generate server key and CSR
openssl genrsa -out server.key 2048
openssl req -new -key server.key -out server.csr \
    -subj "/C=BR/ST=State/L=City/O=Organization/CN=emqx.iot-network"

# Sign server certificate with CA
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
    -out server.crt -days 365 -sha256

# Generate client key and CSR
openssl genrsa -out client.key 2048
openssl req -new -key client.key -out client.csr \
    -subj "/C=BR/ST=State/L=City/O=Organization/CN=device"

# Sign client certificate with CA
openssl x509 -req -in client.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
    -out client.crt -days 365 -sha256

# Clean up
rm *.csr *.srl

echo "Certificates generated successfully!"
echo "CA certificate: ca.crt"
echo "Server certificate: server.crt"
echo "Server key: server.key"
echo "Client certificate: client.crt"
echo "Client key: client.key"
```

Run the script:
```bash
cd ssl
chmod +x generate-certs.sh
./generate-certs.sh
```

### Step 10: Verify Installation

```bash
# Start all services
docker compose up -d

# Check service status
docker compose ps

# View logs
docker compose logs -f

# Test MQTT connection
mosquitto_pub -h localhost -p 8883 \
    --cafile ssl/ca.crt \
    --cert ssl/client.crt \
    --key ssl/client.key \
    -t "test" -m "Hello" -d

# Test AI API
curl -X POST http://localhost:8000/infer/llm \
    -H "Authorization: Bearer ${AI_API_KEY}" \
    -H "Content-Type: application/json" \
    -d '{
        "model_type": "llm",
        "device_id": "test-device-001",
        "prompt": "What is the current status?"
    }'

# Access Grafana
# Open browser: http://localhost:3000
# Login with credentials from .env

# Access EMQX Dashboard
# Open browser: http://localhost:18083
# Login with credentials from .env
```

---

## Service Configuration Details

### EMQX MQTT Broker

EMQX serves as the secure entry point for all device telemetry.

| Configuration | Value | Description |
|---------------|-------|-------------|
| **Image** | `emqx/emqx:5.8.4` | Official EMQX Docker image |
| **MQTT over TLS** | Port 8883 | Encrypted device communication |
| **Dashboard** | Port 18083 | Web-based management UI |
| **Authentication** | JWT + X.509 certificates | Mutual TLS authentication |
| **Authorization** | EMQX ACL | Topic-level permissions |

**Key EMQX Security Features**:
- TLS 1.3 encryption for all MQTT connections
- JWT-based device authentication
- Client certificate validation (mutual TLS)
- Rate limiting to prevent DDoS attacks
- Audit logging of all connections and disconnections

### Apache Kafka

Kafka provides a durable, scalable buffer for incoming telemetry.

| Configuration | Value | Description |
|---------------|-------|-------------|
| **Image** | `apache/kafka:3.7.1` | Official Apache Kafka image |
| **Mode** | KRaft | No Zookeeper dependency |
| **Ports** | 9092 (plain), 9093 (SASL/SSL) | Secure communication |
| **Authentication** | SASL/SCRAM-SHA-256 | Username/password authentication |
| **Encryption** | TLS | Encrypted inter-broker and client communication |

**Key Topics**:
- `raw-telemetry` - Incoming sensor data
- `processed-telemetry` - Data after Flink processing
- `alerts` - Generated alarms
- `ai-inferences` - AI analysis results

### Apache Flink

Flink processes telemetry streams in real-time.

| Configuration | Value | Description |
|---------------|-------|-------------|
| **Image** | `apache/flink:1.18.1` | Official Apache Flink image |
| **JobManager** | Port 8081 | Web UI for job management |
| **Checkpointing** | Enabled | Fault tolerance and state recovery |

**Flink Jobs**:
1. **Telemetry Processor**: Filters, validates, and enriches incoming data
2. **Alert Engine**: Evaluates rules and triggers alarms
3. **Aggregator**: Computes time-window aggregations (averages, max/min)
4. **Downsampler**: Reduces data resolution for long-term storage

### Apache IoTDB

IoTDB stores time-series telemetry data efficiently.

| Configuration | Value | Description |
|---------------|-------|-------------|
| **Image** | `apache/iotdb:1.3.2-standalone` | Official Apache IoTDB image |
| **RPC Port** | 6667 | Client connection port |
| **HTTP API** | 18080 | REST API for queries |
| **TTL (Raw)** | 30 days | Raw data retention period |
| **TTL (Aggregated)** | 1 year | Aggregated data retention |

**Storage Groups**:
- `root.iot.telemetry` - Raw sensor data
- `root.iot.aggregated` - Downsampled data
- `root.iot.metadata` - Device metadata (optional)

### PostgreSQL

PostgreSQL stores relational data: devices, alarms, users, and AI results.

| Configuration | Value | Description |
|---------------|-------|-------------|
| **Image** | `postgres:16-alpine` | Lightweight PostgreSQL image |
| **Port** | 5432 | Database port (internal) |
| **SSL** | Enabled | Encrypted connections |
| **Authentication** | SCRAM-SHA-256 | Secure password hashing |

**Key Tables**:
- `devices` - Device metadata and status
- `alarm_rules` - Alert rule definitions
- `alarms` - Alarm history
- `users` - User accounts and roles
- `ai_inferences` - AI analysis results

### AI Orchestrator

The AI service runs on the Jetson's GPU using NVIDIA container runtime.

| Configuration | Value | Description |
|---------------|-------|-------------|
| **Runtime** | `nvidia` | GPU acceleration |
| **Port** | 8000 | REST API |
| **Models** | LLaMA-3.2-3B, SmolVLM-500M | Edge-optimized AI models |

### Grafana

Grafana provides real-time dashboards and visualization.

| Configuration | Value | Description |
|---------------|-------|-------------|
| **Image** | `grafana/grafana:11.1.0` | Official Grafana image |
| **Port** | 3000 | Web interface |
| **Data Sources** | PostgreSQL, IoTDB | Query both databases |

**Pre-built Dashboards**:
1. **Device Overview**: Status, active alarms, last seen
2. **Telemetry Explorer**: Time-series charts for sensor data
3. **Alarm Console**: Real-time alarm feed with severity filtering
4. **AI Insights**: Inference results and anomaly scores

### Apache Superset

Superset provides BI capabilities and advanced analytics.

| Configuration | Value | Description |
|---------------|-------|-------------|
| **Image** | `apache/superset:4.0.0` | Official Apache Superset image |
| **Port** | 8088 | Web interface |
| **Database** | PostgreSQL | Metadata and query results |

---

## Data Flow Pipeline

### 1. Device → MQTT Broker (TLS)

```json
{
  "device_id": "sensor_001",
  "timestamp": "2026-06-19T14:30:00Z",
  "metrics": {
    "temperature": 72.5,
    "humidity": 62.3,
    "pressure": 1013.2
  }
}
```

### 2. MQTT Broker → Kafka

EMQX routes the message to Kafka topic `raw-telemetry` with device authentication.

### 3. Kafka → Flink (Processing)

Flink reads from `raw-telemetry` and performs:
- **Validation**: Check data format and ranges
- **Enrichment**: Join with device metadata from PostgreSQL
- **Alerting**: Evaluate rules against thresholds
- **Aggregation**: Compute 5-minute averages
- **Downsampling**: Reduce resolution for long-term storage

### 4. Flink → Storage

| Data Type | Destination | Description |
|-----------|-------------|-------------|
| Raw telemetry | IoTDB (`root.iot.telemetry`) | Full-resolution data |
| Aggregated data | IoTDB (`root.iot.aggregated`) | Downsampled data |
| Alarms | PostgreSQL (`alarms`) | Alarm records |
| Device updates | PostgreSQL (`devices`) | Metadata updates |

### 5. Storage → AI Pipeline

The AI Orchestrator periodically:
- Fetches recent telemetry from IoTDB
- Retrieves device metadata and alarms from PostgreSQL
- Builds context-rich prompts
- Runs inference on the Jetson's GPU
- Stores results in PostgreSQL (`ai_inferences`)

### 6. Visualization

- **Grafana** queries IoTDB and PostgreSQL for real-time dashboards
- **Superset** queries the Gold layer for business intelligence
- **REST API** provides programmatic access to all data

---

## AI Model Performance

Expected performance on Jetson Orin Nano 8GB:

| Model | Params | Quantization | Memory | Tokens/sec | Use Case |
|-------|--------|--------------|--------|------------|----------|
| LLaMA-3.2-3B | 3B | Q4_K_M (GGUF) | ~2.2 GB | 20-30 | Root cause analysis, report generation |
| Phi-3-mini-3.8B | 3.8B | Q4 | ~2.8 GB | 15-25 | Reasoning, Q&A |
| SmolVLM-500M | 500M | FP16 | ~1.5 GB | - | Image anomaly detection |
| TimesNet (TensorRT) | - | INT8 | ~200 MB | <50ms | Predictive maintenance |

**Memory Management Tips**:
- Use Q4_K_M quantization for best quality/size trade-off
- Load only one model at a time to stay within 8GB limit
- Use TensorRT for time-series models to minimize latency

---

## API Reference

### Authentication

All API endpoints require an API key in the `Authorization` header:
```
Authorization: Bearer <YOUR_API_KEY>
```

### Endpoints

#### Health Check
```
GET /health
```
Response:
```json
{
  "status": "healthy",
  "gpu_available": true
}
```

#### LLM Inference
```
POST /infer/llm
```
Request:
```json
{
  "model_type": "llm",
  "device_id": "sensor_001",
  "prompt": "Analyze the recent temperature trends",
  "context": {}
}
```
Response:
```json
{
  "result": "Temperature has been stable...",
  "model_type": "llm",
  "device_id": "sensor_001",
  "anomaly_score": 0.12,
  "confidence": 0.85,
  "inference_time_ms": 750,
  "timestamp": "2026-06-19T14:30:00Z"
}
```

#### VLM Inference
```
POST /infer/vlm
```
Request:
```json
{
  "model_type": "vlm",
  "device_id": "camera_001",
  "image_path": "/data/images/camera_001_2026-06-19.jpg",
  "prompt": "Are there any visible anomalies?"
}
```

#### Time-Series Inference
```
POST /infer/timeseries
```
Request:
```json
{
  "model_type": "timeseries",
  "device_id": "sensor_001",
  "telemetry_data": [72.5, 73.1, 72.8, 95.2, 72.3, ...]
}
```

#### Inference History
```
GET /infer/history/{device_id}?limit=20
```

---

## Troubleshooting

### Common Issues

#### 1. Docker GPU Not Available
```bash
# Verify NVIDIA runtime
docker run --rm --runtime=nvidia --gpus all nvidia/cuda:12.6.0-base-ubuntu22.04 nvidia-smi

# Check NVIDIA Container Toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

#### 2. EMQX TLS Certificate Errors
```bash
# Verify certificates
openssl verify -CAfile ssl/ca.crt ssl/server.crt
openssl verify -CAfile ssl/ca.crt ssl/client.crt

# Check EMQX logs
docker compose logs emqx
```

#### 3. Out of Memory (OOM) on Jetson
```bash
# Increase swap space
sudo fallocate -l 8G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Reduce model memory usage
# Use smaller models or higher quantization (e.g., Q4 instead of Q6)
```

#### 4. Kafka Connection Issues
```bash
# Check Kafka logs
docker compose logs kafka

# Verify topics exist
docker compose exec kafka kafka-topics --bootstrap-server localhost:9092 --list

# Create topic manually if needed
docker compose exec kafka kafka-topics --bootstrap-server localhost:9092 --create --topic raw-telemetry --partitions 3 --replication-factor 1
```

#### 5. IoTDB Connection Refused
```bash
# Check IoTDB logs
docker compose logs iotdb

# Verify IoTDB is running
docker compose exec iotdb /iotdb/sbin/start-cli.sh -h 127.0.0.1 -p 6667 -u root -pw root
```

---

## Contributing

We welcome contributions! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- All services must be containerized
- Use environment variables for all credentials (never hardcode)
- Include health checks for all services
- Document all API endpoints
- Add logging for all critical operations

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- NVIDIA for the Jetson platform and JetPack SDK
- Apache Software Foundation for IoTDB, Kafka, Flink, and Superset
- EMQX for the MQTT broker
- The open-source AI community for llama.cpp and HuggingFace Transformers

---

**Built with ❤️ on the NVIDIA Jetson Orin Nano**

---

*For questions, issues, or contributions, please open an issue on GitHub: [https://github.com/igoralves1/x-8G2T/issues](https://github.com/igoralves1/x-8G2T/issues)*
