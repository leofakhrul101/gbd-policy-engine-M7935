"""Synthetic music-ingestion data generator (SD-1..5).

- No real artists, labels, ISRCs or fingerprints (SD-3).
- Seedable and deterministic (SD-5). Default seed 1742.
- Category distribution (documented, SD-5), default n=100:
    clean_pass          40%
    edge_case           20%   (values near band thresholds; stresses the law, not the happy path)
    ownership_conflict  20%
    behavioural_anomaly 20%
"""

from __future__ import annotations

import random
from typing import Any

GENRES = ["electronic", "hip-hop", "ambient", "pop", "techno", "drill", "jazz"]
DISTRIBUTION = {"clean_pass": 0.4, "edge_case": 0.2, "ownership_conflict": 0.2, "behavioural_anomaly": 0.2}


def _base(rng: random.Random, i: int) -> dict[str, Any]:
    return {
        "track_id": f"SYN-{i:08d}",
        "title": f"Synthetic Track {i:04d}",
        "artist": f"Test Artist {rng.randint(1, 500):03d}",
        "isrc": f"SYN{rng.randint(10_000_000, 99_999_999)}",
        "duration_s": rng.randint(90, 420),
        "genre": rng.choice(GENRES),
        "territory": rng.choice(["EU", "UK", "US", "GLOBAL"]),
        "distributor_id": f"DIST-{rng.randint(1, 9):02d}",
        "metadata_complete": True,
        "ai_generated": False,
        "ai_disclosed": False,
    }


def _make(category: str, rng: random.Random, i: int) -> dict[str, Any]:
    r = _base(rng, i)
    r["category"] = category  # generator label for evaluation only; engine never reads it
    if category == "clean_pass":
        r["ownership_claims"] = [{"claimant": f"C{rng.randint(1,999):03d}", "split_pct": 100}]
        r["behavioural_signals"] = {
            "account_age_days": rng.randint(120, 2000),
            "prior_uploads": rng.randint(5, 200),
            "takedown_history": 0,
            "upload_velocity_24h": rng.randint(0, 2),
        }
        r["fingerprint_match_score"] = round(rng.uniform(0.0, 0.15), 2)
    elif category == "edge_case":
        # deliberately near thresholds: partial fingerprint band, young-but-not-new accounts
        r["ownership_claims"] = [{"claimant": f"C{rng.randint(1,999):03d}", "split_pct": 100}]
        r["behavioural_signals"] = {
            "account_age_days": rng.choice([29, 30, 31, 45, 89]),
            "prior_uploads": rng.randint(0, 5),
            "takedown_history": 0,
            "upload_velocity_24h": rng.randint(0, 5),
        }
        r["fingerprint_match_score"] = round(rng.choice([0.29, 0.30, 0.31, 0.55, 0.74, 0.75]), 2)
        if rng.random() < 0.4:
            r["ai_generated"], r["ai_disclosed"] = True, rng.random() < 0.5
        if rng.random() < 0.3:
            r["metadata_complete"] = False
    elif category == "ownership_conflict":
        n = rng.randint(2, 3)
        splits = [100 // n] * n
        splits[0] += 100 - sum(splits)
        r["ownership_claims"] = [
            {"claimant": f"C{rng.randint(1,999):03d}", "split_pct": s} for s in splits
        ]
        r["behavioural_signals"] = {
            "account_age_days": rng.randint(1, 400),
            "prior_uploads": rng.randint(0, 40),
            "takedown_history": rng.choice([0, 0, 1]),
            "upload_velocity_24h": rng.randint(0, 10),
        }
        r["fingerprint_match_score"] = round(rng.uniform(0.0, 0.6), 2)
    elif category == "behavioural_anomaly":
        r["ownership_claims"] = [{"claimant": f"C{rng.randint(1,999):03d}", "split_pct": 100}]
        r["behavioural_signals"] = {
            "account_age_days": rng.randint(1, 25),
            "prior_uploads": rng.randint(0, 3),
            "takedown_history": rng.randint(1, 4),
            "upload_velocity_24h": rng.randint(10, 60),
        }
        r["fingerprint_match_score"] = round(rng.uniform(0.5, 0.99), 2)
    else:
        raise ValueError(category)
    return r


def generate(n: int = 100, seed: int = 1742) -> list[dict[str, Any]]:
    """Deterministic synthetic record set: same (n, seed) → identical output."""
    rng = random.Random(seed)
    records: list[dict[str, Any]] = []
    counts = {cat: int(n * share) for cat, share in DISTRIBUTION.items()}
    counts["clean_pass"] += n - sum(counts.values())  # remainder to clean
    i = 0
    for cat, count in counts.items():
        for _ in range(count):
            records.append(_make(cat, rng, i))
            i += 1
    return records
