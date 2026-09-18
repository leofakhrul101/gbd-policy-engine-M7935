# gbd-policy-engine-M7935 — change spec: decision-certificate v0 → v0.1

Purpose: close the gaps found by the DSA Art 17(3) conformance test and the Sterz oversight test. Tag as `v0.1`; keep `v0` replayable. State in Ch 5 that the conformance test in Ch 6 found the schema one step short and v0.1 closes it.

## 1. Schema changes — `decision-certificate` payload (signed)

| Field | Type | Required | Legal anchor | Notes |
|---|---|---|---|---|
| `automated_means.detection` | bool | yes | DSA 17(3)(c); Commission `automated_detection` | Was the item surfaced by automated means |
| `automated_means.decision` | enum `FULLY \| PARTIALLY \| NOT_AUTOMATED` | yes | DSA 17(3)(c); Commission `automated_decision` | Two facts, not one flag. FULLY for automated ALLOW/REJECT/QUARANTINE; PARTIALLY where human decided on REVIEW |
| `trigger_source` | enum `ART16_NOTICE \| TRUSTED_FLAGGER \| OTHER_NOTIFICATION \| OWN_INITIATIVE` | yes | DSA 17(3)(b), 16(6); Commission `source_type` | `notice_ref` sub-field when not OWN_INITIATIVE |
| `rationale.triggered_rules[].norm_refs[]` | array of `{instrument, article, paragraph?, point?}` or `{tos_version, clause}` | yes (≥1 per rule) | DSA 17(3)(d) legal ground / 17(3)(e) contractual ground; Husovec p 255 "previously disclosed legal basis" | Inside the signed payload, never a side table |
| `decision.explanation` | string | **promote to required** | DSA 17(4) | Generated from triggered rules + norm_refs; human-readable |
| `redress` | `{internal_complaint: url/ref, ods: bool, judicial: bool}` | yes for adverse outcomes | DSA 17(3)(f); 20(1); 21 | Commission schema omits this; we don't |
| `review` (REVIEW and re-entry decisions only) | object | yes when present | AI Act 14(4); Sterz; Binns & Veale; Goddard | see §2 |
| `policy.approval` | `{distributor_id, approved_at, approver_hash, version}` | yes | EDPB 07/2020 paras 84, 116, 118; GDPR 28(3)(a) | Distributor sign-off sealed with the version it approved |

Bump `schema_version` to `decision-certificate/v0.1`. Certificates issued under `v0` remain valid and replayable; the verifier must accept both.

## 2. `review` object (REVIEW queue and re-entry)

```
review:
  reviewer_id: <pseudonymous stable id>      # accountability (Goddard); not personal data in exports (DSA 24(5))
  blind_first: true                           # reviewer chose before seeing engine proposal
  reviewer_outcome: ALLOW|REJECT|QUARANTINE   # chosen by reviewer
  engine_proposal: ALLOW|REVIEW|REJECT|QUARANTINE
  agreement: AGREE|OVERRIDE
  signals_shown: [six dimension ids]          # epistemic access
  time_to_decision_ms: int
  reason_text: string (optional)
  forwarded_to_provider: bool                 # Sterz causal power; AI Act 26(5)
```

UI rule: engine proposal is hidden until `reviewer_outcome` is committed. Agreement rate is a first-class metric (export monthly).

## 3. Controls (versioned, in `policy.controls`)

| Control | Default | Anchor |
|---|---|---|
| `automation_may_reach` | `[ALLOW, REVIEW]` per v0; adverse outcomes automated only where `contract_basis=true` | GDPR 22(2)(a); existing control, keep |
| `safe_state.on_signal_unavailable` | `ROUTE_ALL_TO_REVIEW` | AI Act 14(4)(e); recital 73 |
| `reentry.allow_on_notice` | `true` — an Art 16 notice against an ALLOW re-opens the item as REVIEW with `trigger_source=ART16_NOTICE` | Sterz causal power gap; Art 22 third-party strain |
| `reentry.window_days` | `180` | DSA 20(1) six months |
| `explanation.required` | `true` | DSA 17(4) |

## 4. Export

`export/commission_sor.py`: map certificate → Commission SoR schema (`decision_visibility`, `decision_ground`, `decision_ground_reference_url` ← first `norm_refs` URL, `source_type`, `automated_detection`, `automated_decision`, `content_date`, `application_date`), strip personal data (24(5)). This is the falsifiable test made executable: every 17(3) field and every Commission field must populate from the certificate alone.

## 5. Tests to add (target 38 → ~46)

1. v0.1 certificate validates; v0 certificate still validates and replays.
2. Every triggered rule carries ≥1 `norm_refs`; reject otherwise.
3. `explanation` missing → certificate rejected.
4. REVIEW decision without `review.reviewer_id` or `agreement` → rejected.
5. Blind-first: engine proposal not readable before commit (unit test on the review API).
6. Signal unavailable → all items route to REVIEW; certificate records `safe_state=true`.
7. Art 16 notice on an ALLOW → new REVIEW item referencing prior certificate hash.
8. Commission export: all required fields populated from certificate; no personal data in output.

## 6. Out of scope (say so in Ch 5)

Reviewer training, staffing, throughput — deployer process (AI Act 26(2)). Calibration of the advisory ML on live traffic — unproven; disclosed under Art 13(3)(b)(ii). Online-platform status of the distributor — scope question, argued in Ch 6, not coded.

---

## Implemented 22 Aug 2026 (this commit)

- `engine.py`: safe state on missing required signals (routes to REVIEW); `trigger_source`/`notice_ref` parameters; triggered rules now carry `reason_code`, `norm_refs`, `articles` inside the sealed payload; SoR gains `automated_detection` / `automated_decision` (17(3)(c) two limbs), `notice_ref`, `safe_state`, `missing_signals`. `legal_ground` stays deliberately None — the boundary thesis is unchanged.
- `policy.py` + `policy_bundle.schema.json`: optional `required_signals` and `approval` (controller sign-off, EDPB 07/2020 para 84).
- `review.py` (new): blind-first `ReviewSession` — engine proposal unreadable before commit; sealed review record with reviewer_id, agreement, time-to-decision; `reentry_from_notice` re-opens a prior ALLOW on an Art 16 notice; `agreement_rate` is the rubber-stamp metric.
- `audit_log.py`: append-only `review_events` table.
- `export.py` (new): projection onto the Commission SoR schema; ground reference never NULL by construction.
- `policies/v0.2.0.yaml` (new): same nine rules; adds required_signals + approval. v0.1.0 packs still validate and replay (test 1).
- Tests: 38 → 49. Two stale duplicate tests in `tests/` fixed (`quality_flag_17_1` → `17_4`, `action_context` → `action_taken`).

Certificate top-level schema remains exactly 13 fields; all additions live inside `triggered_rules` and the SoR block, as the module docstring prescribes.

---

## v0.2.1 — 13 September 2026: four defects closed before submission

Found by a line-by-line audit of the repository against the dissertation text.
Each is recorded here because the dissertation reports them: a design-science
artefact that hides its own failed conformance checks is not evidence of
anything.

**A1 · The Evidence Pack could not name the submission it decided.**
`pack_id` was derived from timestamp, policy version, rule trace and confidence
score. Two different submissions with the same signal profile in the same second
produced byte-identical packs and the second could not be written to the log
(`UNIQUE constraint failed: evidence_packs.pack_id`). A record that cannot be
tied to a submission cannot be served on the recipient under Art 17(1), cannot
be retrieved on an Art 16 notice, and cannot be reconciled against the
Transparency Database.

Fixed by adding `submission_ref` — a salted SHA-256 digest of the submission
identifier, truncated to 32 hex characters — as the second field of the pack, and
folding it into the `pack_id` derivation. The raw identifier never enters the
pack, so Art 24(5)'s bar on personal data holds; the controller can resolve the
digest against their own catalogue, and nobody else can. Schema is now 14 fields.
Test 12.

**A2 · The reviewer saw only the dimensions that fired.**
`ReviewSession.signals()` returned four items, all derived from rules that had
triggered. A reviewer who cannot see which dimensions stayed silent cannot judge
whether the engine looked at the right things — which is exactly the competence
WP29 requires (WP251rev.01, 21). `signals()` now returns all six risk dimensions,
each marked fired or not-fired with its reason code, ahead of the four context
items. Test 6.

**A3 · The 17(4) sufficiency flag was never asserted.**
The only test touching `quality_flag_17_4` accepted either `"thin"` or
`"informational"`, and the demonstration record named `thin_reasons` produces
`"informational"` — so the boundary thesis rested on a flag nothing pinned down.
Test 13 now exercises the `thin` branch exactly: a lone strong fingerprint match
gives QUARANTINE on one named fact, structurally complete under 17(3) and thin
under 17(4). The looser assertion in `tests/test_engine.py` is now exact.

**A4 · Notice-triggered re-entry produced an orphan decision.**
`reentry_from_notice()` recorded the trigger source and notice reference but
nothing linking the new decision to the one it re-opened. The rightsholder's
route — the dissertation's answer to the third party Art 22 does not reach —
therefore yielded a decision that could not be tied to the ALLOW it contested.
`evaluate()` now takes `supersedes_pack_id` and the statement of reasons carries
it. Test 8.

Housekeeping: `pyproject.toml` version 0.1.0 → 0.2.1; two stale, never-collected
test files deleted from the repository root; the `tests/test_v02.py` docstring
now points at this file rather than a changelog that does not exist.

Tests: 49 → 52, all passing.

---

## v0.2.2 — 18 September 2026: the statement of reasons, written for its reader

Article 17(4) requires a statement that is "clear and easily comprehensible" and precise enough
to let the recipient "effectively exercise the possibilities for redress". Until now the
recipient-facing text told an artist that they could contest the decision "via:
internal-complaint-v1", and reported a confidence score and a policy version in the same breath.
Every one of those is a machine reference. None of them is comprehensible to the person the
article is written for.

The decision is now expressed in two registers from one source of truth. The sentences say what
happened, what it rested on, and what the artist can do — the redress route named in words, from
a new `oversight_pathway_label` in the policy bundle. The identifiers are gathered into a single
closing line, explicitly labelled as a reference for a query or an audit.

Nothing moved in the sealed payload or the Commission export: `oversight_pathway` still carries
`internal-complaint-v1`, because that is the value an auditor resolves. The record keeps the
scheme identifier; the person gets a sentence. That split is the chapter's argument about form
and sufficiency, made operational rather than asserted.

Also in this release, so that what a reviewer opens matches what the dissertation describes:

- `docs/demo.html` — the engine ported to JavaScript and running in the browser, verified
  field-for-field and hash-for-hash against this implementation over 576 signal combinations.
  `README` now points a non-running reader here. `docs/walkthrough.html` is kept and labelled as
  the v0.1.0 exhibit.
- `demo/app.py` loaded `policies/v0.1.0.yaml` and simulated a "v0.2.0" by moving a threshold
  slider — a version number that now collides with a real bundle meaning something else. It runs
  the real v0.2.0 and simulates a prospective 0.3.0.
- `norms/norms.yaml` header said one norm was verified; four are, and the file's own status
  fields have said so since 4 August. `SOURCES.md` pointed at the v0.1.0 bundle and repeated the
  stale statuses.
- `APPENDIX-four-edge-cases.md` is now labelled as the v0.1.0 exhibit it is.
- `LICENSE.md` added: all rights reserved, with an express grant for assessment.

Tests: 52, all passing.
