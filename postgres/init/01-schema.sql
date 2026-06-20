-- =============================================================================
-- X-8G2T relational schema (PostgreSQL 16 + pgvector)
-- Stores device metadata, alarm rules/history, users, AI inferences, and the
-- agent memory used by the multi-agent system.
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS vector;

-- -----------------------------------------------------------------------------
-- Devices (the edge environment is described here)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS devices (
    device_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id      VARCHAR(128) UNIQUE,          -- the id used in MQTT topics
    name             VARCHAR(255) NOT NULL,
    device_type      VARCHAR(100) NOT NULL,        -- sensor | gateway | camera ...
    location         VARCHAR(255),
    latitude         DECIMAL(10, 8),
    longitude        DECIMAL(11, 8),
    metadata         JSONB,
    firmware_version VARCHAR(50),
    status           VARCHAR(20) DEFAULT 'active',
    install_date     TIMESTAMPTZ DEFAULT NOW(),
    last_seen        TIMESTAMPTZ,
    created_at       TIMESTAMPTZ DEFAULT NOW(),
    updated_at       TIMESTAMPTZ DEFAULT NOW()
);

-- -----------------------------------------------------------------------------
-- Alarm rules + alarm history
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS alarm_rules (
    rule_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id        UUID REFERENCES devices(device_id) ON DELETE CASCADE,
    metric_name      VARCHAR(100) NOT NULL,
    condition        VARCHAR(20) NOT NULL,         -- gt | lt | eq | between
    threshold_value  DECIMAL,
    threshold_max    DECIMAL,
    severity         VARCHAR(20) NOT NULL,         -- info | warning | critical
    message_template TEXT,
    enabled          BOOLEAN DEFAULT TRUE,
    created_at       TIMESTAMPTZ DEFAULT NOW(),
    updated_at       TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS alarms (
    alarm_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id       UUID REFERENCES devices(device_id) ON DELETE CASCADE,
    rule_id         UUID REFERENCES alarm_rules(rule_id),
    severity        VARCHAR(20) NOT NULL,
    message         TEXT NOT NULL,
    metric_name     VARCHAR(100),
    metric_value    DECIMAL,
    source          VARCHAR(20) DEFAULT 'flink',   -- flink | agent | manual
    acknowledged    BOOLEAN DEFAULT FALSE,
    acknowledged_by UUID,
    acknowledged_at TIMESTAMPTZ,
    resolved        BOOLEAN DEFAULT FALSE,
    resolved_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- -----------------------------------------------------------------------------
-- Users & roles
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    user_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username      VARCHAR(100) UNIQUE NOT NULL,
    email         VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name     VARCHAR(255),
    role          VARCHAR(50) DEFAULT 'viewer',
    device_access JSONB,
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    updated_at    TIMESTAMPTZ DEFAULT NOW()
);

-- -----------------------------------------------------------------------------
-- AI inferences (output of single-shot model calls)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ai_inferences (
    inference_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id         UUID REFERENCES devices(device_id) ON DELETE CASCADE,
    model_type        VARCHAR(50) NOT NULL,        -- llm | vlm | timeseries
    input_summary     TEXT,
    result            TEXT NOT NULL,
    anomaly_score     DECIMAL(5, 4),
    confidence        DECIMAL(5, 4),
    inference_time_ms INTEGER,
    created_at        TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- AGENTIC LAYER
-- =============================================================================

-- Every agent run (a full multi-step investigation) is recorded here.
CREATE TABLE IF NOT EXISTS agent_runs (
    run_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id     UUID REFERENCES devices(device_id) ON DELETE SET NULL,
    objective     TEXT NOT NULL,                   -- the task given to the supervisor
    triggered_by  VARCHAR(50) DEFAULT 'api',       -- api | alarm | schedule
    final_answer  TEXT,
    status        VARCHAR(20) DEFAULT 'running',    -- running | done | failed
    total_steps   INTEGER DEFAULT 0,
    total_tokens  INTEGER DEFAULT 0,
    duration_ms   INTEGER,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

-- The step-by-step trace (thought / tool call / observation) for auditability.
CREATE TABLE IF NOT EXISTS agent_steps (
    step_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id       UUID REFERENCES agent_runs(run_id) ON DELETE CASCADE,
    step_index   INTEGER NOT NULL,
    agent_name   VARCHAR(80) NOT NULL,
    thought      TEXT,
    tool_name    VARCHAR(80),
    tool_input   JSONB,
    observation  TEXT,
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

-- Long-term semantic memory: distilled facts/insights an agent can recall later.
-- 768 dims matches nomic-embed-text-v1.5 (see EMBED_DIM in .env).
CREATE TABLE IF NOT EXISTS agent_memory (
    memory_id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id   UUID REFERENCES devices(device_id) ON DELETE CASCADE,
    kind        VARCHAR(40) DEFAULT 'insight',     -- insight | incident | resolution
    content     TEXT NOT NULL,
    embedding   vector(768),
    importance  REAL DEFAULT 0.5,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Bookkeeping for documents indexed into the RAG vector store (Qdrant).
CREATE TABLE IF NOT EXISTS rag_documents (
    doc_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_path  TEXT NOT NULL,
    title        TEXT,
    sha256       VARCHAR(64) UNIQUE,
    chunk_count  INTEGER DEFAULT 0,
    indexed_at   TIMESTAMPTZ DEFAULT NOW()
);

-- -----------------------------------------------------------------------------
-- Indexes
-- -----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_devices_status      ON devices(status);
CREATE INDEX IF NOT EXISTS idx_devices_external    ON devices(external_id);
CREATE INDEX IF NOT EXISTS idx_alarms_device       ON alarms(device_id);
CREATE INDEX IF NOT EXISTS idx_alarms_severity     ON alarms(severity);
CREATE INDEX IF NOT EXISTS idx_alarms_created       ON alarms(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_inf_device       ON ai_inferences(device_id);
CREATE INDEX IF NOT EXISTS idx_ai_inf_created      ON ai_inferences(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_runs_device   ON agent_runs(device_id);
CREATE INDEX IF NOT EXISTS idx_agent_steps_run     ON agent_steps(run_id, step_index);

-- IVFFlat index for cosine similarity over agent memory.
CREATE INDEX IF NOT EXISTS idx_agent_memory_vec
    ON agent_memory USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- -----------------------------------------------------------------------------
-- Convenience view
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW device_health_summary AS
SELECT
    d.device_id,
    d.external_id,
    d.name,
    d.status,
    d.last_seen,
    COUNT(a.alarm_id) FILTER (WHERE a.resolved = FALSE)                       AS active_alarms,
    COUNT(a.alarm_id) FILTER (WHERE a.severity = 'critical' AND a.resolved = FALSE) AS critical_alarms
FROM devices d
LEFT JOIN alarms a ON d.device_id = a.device_id
GROUP BY d.device_id, d.external_id, d.name, d.status, d.last_seen;
