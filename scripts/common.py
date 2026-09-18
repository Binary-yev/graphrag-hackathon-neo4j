"""Shared Aura connection helpers.

Every script in this repo reads credentials from .env via this module so that
there is exactly one place where connection details are resolved.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

_PLACEHOLDERS = {"", "YOUR_PASSWORD", "YOUR_DATABASE_ID"}


def neo4j_settings() -> tuple[str, str, str, str]:
    """Return (uri, username, password, database), failing loudly if unset."""
    uri = os.getenv("NEO4J_URI", "").strip()
    username = os.getenv("NEO4J_USERNAME", "neo4j").strip() or "neo4j"
    password = os.getenv("NEO4J_PASSWORD", "").strip()
    database = os.getenv("NEO4J_DATABASE", "neo4j").strip() or "neo4j"

    missing = []
    if not uri or "YOUR_DATABASE_ID" in uri:
        missing.append("NEO4J_URI")
    if password in _PLACEHOLDERS:
        missing.append("NEO4J_PASSWORD")

    if missing:
        raise RuntimeError(
            f"Missing Aura configuration: {', '.join(missing)}. "
            "Copy .env.example to .env and paste the values from the "
            "credential file in keys/."
        )

    return uri, username, password, database


def create_driver():
    uri, username, password, _ = neo4j_settings()
    return GraphDatabase.driver(uri, auth=(username, password))
