# =============================================================================
# Apache Flink 1.18 image for X-8G2T with PyFlink + the Kafka SQL connector.
# Used by both flink-jobmanager and flink-taskmanager.
# =============================================================================
FROM apache/flink:1.18.1-scala_2.12-java11

ENV PYTHONUNBUFFERED=1

# Python runtime for PyFlink jobs.
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 python3-pip && \
    ln -sf /usr/bin/python3 /usr/bin/python && \
    pip3 install --no-cache-dir apache-flink==1.18.1 && \
    rm -rf /var/lib/apt/lists/*

# Kafka SQL connector (matches Flink 1.18) so the job can read/write Kafka.
ADD https://repo1.maven.org/maven2/org/apache/flink/flink-sql-connector-kafka/3.1.0-1.18/flink-sql-connector-kafka-3.1.0-1.18.jar \
    /opt/flink/lib/flink-sql-connector-kafka.jar
RUN chmod 644 /opt/flink/lib/flink-sql-connector-kafka.jar

WORKDIR /opt/flink
