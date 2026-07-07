from pathlib import Path

import pytest
import yaml

from gbd.policy import load_bundle

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def bundle():
    return load_bundle(ROOT / "policies" / "v0.1.0.yaml")


@pytest.fixture(scope="session")
def slice_records():
    data = yaml.safe_load((ROOT / "data" / "synthetic" / "slice.yaml").read_text())
    return {r["record_id"]: r for r in data["records"]}
