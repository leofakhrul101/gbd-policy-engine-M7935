"""Governance-by-Design Policy Engine — M7935 dissertation artefact.

Five layers:
  norm records (norms/norms.yaml)          — Regulatory Norm Layer
  policy bundles (policies/*.yaml)         — Policy Translation Layer (Norm-to-Control)
  gbd.engine                               — Decision Logic Layer (confidence scoring)
  gbd.evidence_pack                        — Evidence Pack Layer
  gbd.audit_log                            — Governance & Provenance Layer

Not legal advice. A readiness signal, not a determination of compliance.
"""

from gbd.policy import PolicyBundle, load_bundle
from gbd.engine import evaluate, band_for
from gbd.evidence_pack import build_pack, verify_integrity
from gbd.audit_log import AuditLog
from gbd.data_generator import generate

__all__ = [
    "PolicyBundle", "load_bundle", "evaluate", "band_for",
    "build_pack", "verify_integrity", "AuditLog", "generate",
]
