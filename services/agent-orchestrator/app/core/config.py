"""Central configuration, loaded from environment variables (.env)."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Inference servers (OpenAI-compatible, served by llama.cpp) ---
    llm_base_url: str = "http://llm-server:8080/v1"
    vlm_base_url: str = "http://vlm-server:8080/v1"
    embed_base_url: str = "http://embeddings:8080/v1"

    # --- Postgres ---
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_user: str = "iot_admin"
    postgres_password: str = ""
    postgres_db: str = "iot_telemetry"

    # --- IoTDB REST ---
    iotdb_host: str = "iotdb"
    iotdb_rest_port: int = 18080
    iotdb_user: str = "root"
    iotdb_password: str = "root"

    # --- Qdrant (RAG vector store) ---
    qdrant_url: str = "http://qdrant:6333"
    rag_collection: str = "x8g2t_knowledge"
    rag_top_k: int = 5
    embed_dim: int = 768

    # --- Local SPC MCP server (Statistical Process Control tools) ---
    spc_mcp_url: str = "http://spc-mcp:8765/mcp"

    # --- Agent behaviour ---
    agent_max_steps: int = 6
    agent_temperature: float = 0.3

    # --- Security ---
    ai_api_key: str = ""
    jwt_secret: str = ""

    log_level: str = "INFO"

    @property
    def pg_dsn(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
