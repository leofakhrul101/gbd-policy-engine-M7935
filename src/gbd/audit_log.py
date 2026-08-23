"""Governance & Provenance Layer — append-only SQLite audit log (GOV-1..5).

Append-only is enforced at the application layer AND by SQLite triggers that
abort any UPDATE or DELETE on the audited tables.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import json

from gbd.policy import PolicyBundle, bundle_from_dict, bundle_to_yaml
import yaml

_DDL = """
CREATE TABLE IF NOT EXISTS policy_versions (
    version        TEXT PRIMARY KEY,
    effective_date TEXT NOT NULL,
    bundle_yaml    TEXT NOT NULL,
    registered_at  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS evidence_packs (
    pack_id        TEXT PRIMARY KEY,
    policy_version TEXT NOT NULL REFERENCES policy_versions(version),
    created_at     TEXT NOT NULL,
    pack_json      TEXT NOT NULL
);
CREATE TRIGGER IF NOT EXISTS no_update_policy BEFORE UPDATE ON policy_versions
BEGIN SELECT RAISE(ABORT, 'audit log is append-only'); END;
CREATE TRIGGER IF NOT EXISTS no_delete_policy BEFORE DELETE ON policy_versions
BEGIN SELECT RAISE(ABORT, 'audit log is append-only'); END;
CREATE TRIGGER IF NOT EXISTS no_update_packs BEFORE UPDATE ON evidence_packs
BEGIN SELECT RAISE(ABORT, 'audit log is append-only'); END;
CREATE TRIGGER IF NOT EXISTS no_delete_packs BEFORE DELETE ON evidence_packs
BEGIN SELECT RAISE(ABORT, 'audit log is append-only'); END;
CREATE TABLE IF NOT EXISTS review_events (
    review_id      TEXT PRIMARY KEY,
    pack_id        TEXT NOT NULL REFERENCES evidence_packs(pack_id),
    reviewer_id    TEXT NOT NULL,
    agreement      TEXT NOT NULL,
    created_at     TEXT NOT NULL,
    review_json    TEXT NOT NULL
);
CREATE TRIGGER IF NOT EXISTS no_update_reviews BEFORE UPDATE ON review_events
BEGIN SELECT RAISE(ABORT, 'audit log is append-only'); END;
CREATE TRIGGER IF NOT EXISTS no_delete_reviews BEFORE DELETE ON review_events
BEGIN SELECT RAISE(ABORT, 'audit log is append-only'); END;
"""


class AuditLog:
    def __init__(self, path: str | Path = ":memory:"):
        self._conn = sqlite3.connect(str(path))
        self._conn.executescript(_DDL)

    # ── GOV-1/GOV-4: policy provenance ────────────────────────────────────
    def register_policy(self, bundle: PolicyBundle) -> None:
        self._conn.execute(
            "INSERT INTO policy_versions VALUES (?, ?, ?, ?)",
            (bundle.policy_version, bundle.effective_date, bundle_to_yaml(bundle),
             datetime.now(timezone.utc).isoformat()),
        )
        self._conn.commit()

    def reconstruct_policy(self, version: str) -> PolicyBundle:
        """Rebuild the exact bundle in force for any prior decision (GOV-4)."""
        row = self._conn.execute(
            "SELECT bundle_yaml FROM policy_versions WHERE version = ?", (version,)
        ).fetchone()
        if row is None:
            raise KeyError(f"policy version not in log: {version}")
        return bundle_from_dict(yaml.safe_load(row[0]))

    # ── GOV-2/3/5: decisions ──────────────────────────────────────────────
    def record_decision(self, pack: dict[str, Any]) -> None:
        self._conn.execute(
            "INSERT INTO evidence_packs VALUES (?, ?, ?, ?)",
            (pack["pack_id"], pack["policy_version"], pack["decision_timestamp"],
             json.dumps(pack)),
        )
        self._conn.commit()

    def get_pack(self, pack_id: str) -> dict[str, Any]:
        row = self._conn.execute(
            "SELECT pack_json FROM evidence_packs WHERE pack_id = ?", (pack_id,)
        ).fetchone()
        if row is None:
            raise KeyError(f"no Evidence Pack: {pack_id}")
        return json.loads(row[0])

    # ── v0.2: review events (GDPR Art 22(3); DSA Art 20(6); AI Act Art 14) ──
    def record_review(self, review: dict[str, Any]) -> None:
        self._conn.execute(
            "INSERT INTO review_events VALUES (?, ?, ?, ?, ?, ?)",
            (review["review_id"], review["pack_id"], review["reviewer_id"],
             review["agreement"], review["review_timestamp"], json.dumps(review)),
        )
        self._conn.commit()

    def reviews_for(self, pack_id: str) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT review_json FROM review_events WHERE pack_id = ? ORDER BY created_at",
            (pack_id,),
        ).fetchall()
        return [json.loads(r[0]) for r in rows]

    def all_reviews(self) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT review_json FROM review_events ORDER BY created_at").fetchall()
        return [json.loads(r[0]) for r in rows]

    def list_decisions(self) -> list[tuple[str, str, str]]:
        return list(self._conn.execute(
            "SELECT pack_id, policy_version, created_at FROM evidence_packs ORDER BY created_at"
        ))

    def close(self) -> None:
        self._conn.close()
