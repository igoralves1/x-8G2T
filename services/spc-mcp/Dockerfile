# =============================================================================
# X-8G2T SPC MCP server.
# Pure-Python Statistical Process Control MCP exposed over streamable HTTP.
# No GPU needed - the heavy AI reasoning happens in the LLM server; this is the
# deterministic statistics + chart-rendering engine the SPC agent calls as tools.
# =============================================================================
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 MPLBACKEND=Agg
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY spc_core.py charts.py server.py ./

EXPOSE 8765
CMD ["python", "server.py"]
