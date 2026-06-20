"""Superset configuration for X-8G2T.

Superset stores its own metadata in the same PostgreSQL instance and connects
to it as an analytics source as well.
"""
import os

SECRET_KEY = os.environ.get("SUPERSET_SECRET_KEY", "change-me")
SQLALCHEMY_DATABASE_URI = os.environ["DATABASE_URL"]

# Quality-of-life defaults for an edge BI deployment.
SUPERSET_WEBSERVER_TIMEOUT = 120
ROW_LIMIT = 50000
FEATURE_FLAGS = {
    "DASHBOARD_RBAC": True,
    "ENABLE_TEMPLATE_PROCESSING": True,
}
