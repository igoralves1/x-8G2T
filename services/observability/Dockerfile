# =============================================================================
# X-8G2T Observability API
# FastAPI server that exposes board + container metrics via REST and WebSocket.
# Clients subscribe on ws://host:8001/ws and receive a full snapshot every 1s.
# =============================================================================
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

EXPOSE 8001
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
