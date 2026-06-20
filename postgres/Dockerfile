# =============================================================================
# PostgreSQL 16 + pgvector for X-8G2T
# pgvector is used for agent long-term memory and for a lightweight in-DB
# semantic search fallback when Qdrant is not reachable.
# =============================================================================
FROM pgvector/pgvector:pg16

# Schema + seed data are executed (in alphabetical order) the first time the
# data volume is initialised.
COPY init/ /docker-entrypoint-initdb.d/
