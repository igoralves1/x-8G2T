# =============================================================================
# Apache Superset 4.0 for X-8G2T (self-initialising).
# =============================================================================
FROM apache/superset:4.0.0

USER root
RUN pip install --no-cache-dir psycopg2-binary

COPY superset_config.py /app/pythonpath/superset_config.py
COPY bootstrap.sh /app/bootstrap.sh
RUN chmod +x /app/bootstrap.sh

ENV SUPERSET_CONFIG_PATH=/app/pythonpath/superset_config.py
USER superset

ENTRYPOINT ["/app/bootstrap.sh"]
