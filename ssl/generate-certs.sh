#!/usr/bin/env bash
# =============================================================================
# Generate the TLS material used for MQTT-over-TLS between the edge devices
# and the EMQX broker on the Jetson board.
#
# Produces (in this ssl/ directory):
#   ca.crt / ca.key          -> the Certificate Authority
#   server.crt / server.key  -> EMQX broker certificate (CN=emqx)
#   client.crt / client.key  -> a sample device certificate (CN=device)
#
# Ship ca.crt + client.crt + client.key to each edge device.
# =============================================================================
set -euo pipefail
cd "$(dirname "$0")"

DAYS=825
SUBJ_BASE="/C=BR/ST=State/L=City/O=X-8G2T/OU=IoT"

echo ">> Generating Certificate Authority..."
openssl genrsa -out ca.key 4096
openssl req -x509 -new -nodes -key ca.key -sha256 -days "$DAYS" -out ca.crt \
  -subj "${SUBJ_BASE}/CN=X-8G2T Root CA"

echo ">> Generating EMQX broker certificate..."
openssl genrsa -out server.key 2048
openssl req -new -key server.key -out server.csr -subj "${SUBJ_BASE}/CN=emqx"
cat > server.ext <<EOF
subjectAltName = DNS:emqx, DNS:localhost, IP:127.0.0.1
extendedKeyUsage = serverAuth
EOF
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
  -out server.crt -days "$DAYS" -sha256 -extfile server.ext

echo ">> Generating sample device (client) certificate..."
openssl genrsa -out client.key 2048
openssl req -new -key client.key -out client.csr -subj "${SUBJ_BASE}/CN=device-001"
cat > client.ext <<EOF
extendedKeyUsage = clientAuth
EOF
openssl x509 -req -in client.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
  -out client.crt -days "$DAYS" -sha256 -extfile client.ext

chmod 644 *.crt
chmod 600 *.key
rm -f ./*.csr ./*.ext ./*.srl

echo ""
echo "Done. Certificates written to $(pwd)"
echo "  Broker  : server.crt / server.key (mounted read-only into EMQX)"
echo "  CA      : ca.crt"
echo "  Device  : client.crt / client.key  (copy to each edge device)"
