# Appendix — Four Demonstration Edge Cases

> **This is the v0.1.0 exhibit, kept deliberately.** The packs below have 13 fields and carry no
> `norm_refs`, no `submission_ref` and no two-limb automation record. That is the *before* state
> the dissertation's conformance test reports in Chapter 6; `docs/CHANGES-v0.2.md` records what
> changed and why. For current output, open `docs/demo.html` or run the test suite.

Engine: gbd-policy-engine v0.1.0 · policy bundle 0.1.0 · fixed timestamp 2026-07-06T12:00:00Z for reproducibility.
Reproduce: `python -m pytest tests/test_engine.py` or re-run any record via `gbd.evaluate()`.


---

## Edge case 1 — Clean pass (the unconditional disclosure)

**Input (synthetic):** claims=1, account_age=540d, takedowns=0, fingerprint=0.02

**Rule trace:**

- `RULE_STATEMENT_OF_REASONS` (w=0.0) — Structured statement of reasons emitted per DSA Art 17. · [DSA Art 17(1), DSA Art 17(3)(a), DSA Art 17(3)(b), DSA Art 17(3)(c), DSA Art 17(3)(f)]
- `RULE_PROVENANCE_RECORD` (w=0.0) — Policy version and decision recorded for accountability (GDPR Arts 5(2), 24). · [GDPR Art 24, GDPR Art 5(2)]

**Outcome:** confidence 1.000 · band **High** · direction no_concerns_identified · human_review=False · 17(1) quality flag: **informational**

**What it shows:** DSA Art 17(3)(c) disclosure fires even when nothing is wrong: automation must announce itself unconditionally. The statement of reasons is informational — the obligation is procedural, not outcome-dependent.

**Evidence Pack (verbatim):**

```json
{
  "pack_id": "c3b263b3-e4b0-5d82-9675-594bd8b43ba7",
  "decision_timestamp": "2026-07-06T12:00:00Z",
  "policy_version": "0.1.0",
  "confidence_score": 1.0,
  "confidence_band": "High",
  "triggered_rules": [
    {
      "rule_id": "RULE_STATEMENT_OF_REASONS",
      "description": "Structured statement of reasons emitted per DSA Art 17."
    },
    {
      "rule_id": "RULE_PROVENANCE_RECORD",
      "description": "Policy version and decision recorded for accountability (GDPR Arts 5(2), 24)."
    }
  ],
  "input_categories": [
    "no_risk_signals_detected"
  ],
  "regulatory_mapping": {
    "DSA Art 17(1)": {
      "rule_id": "RULE_STATEMENT_OF_REASONS",
      "status": "evidenced"
    },
    "DSA Art 17(3)(a)": {
      "rule_id": "RULE_STATEMENT_OF_REASONS",
      "status": "evidenced"
    },
    "DSA Art 17(3)(b)": {
      "rule_id": "RULE_STATEMENT_OF_REASONS",
      "status": "evidenced"
    },
    "DSA Art 17(3)(c)": {
      "rule_id": "RULE_STATEMENT_OF_REASONS",
      "status": "evidenced"
    },
    "DSA Art 17(3)(f)": {
      "rule_id": "RULE_STATEMENT_OF_REASONS",
      "status": "evidenced"
    },
    "GDPR Art 24": {
      "rule_id": "RULE_PROVENANCE_RECORD",
      "status": "evidenced"
    },
    "GDPR Art 5(2)": {
      "rule_id": "RULE_PROVENANCE_RECORD",
      "status": "evidenced"
    },
    "DSA Art 17 \u2014 statement of reasons": {
      "action_context": "no_restriction_indicated",
      "facts_relied_on": [],
      "automated_means_used": true,
      "legal_ground": null,
      "contractual_ground": "distributor terms: metadata, ownership and originality requirements",
      "redress": "internal-complaint-v1",
      "quality_flag_17_4": "informational"
    }
  },
  "plain_english_explanation": "This submission was assessed by an automated system using policy version 0.1.0. The system's confidence in its assessment is 1.000 (High). No risk signals were detected in this submission. You can contest this outcome via: internal-complaint-v1. This record is a readiness signal produced by compliance-support software. It is not a legal determination and does not constitute legal advice.",
  "oversight_pathway": "internal-complaint-v1",
  "retention_reference": "retention-policy-v1 (synthetic demo: indefinite)",
  "integrity_hash": "96f010aa12a003c544ed4cce27c1e58cff098d51fe81f9fd226a342d500c7db0"
}
```


---

## Edge case 2 — Ambiguous ownership (automation yields to oversight)

**Input (synthetic):** claims=2, account_age=4d, takedowns=0, fingerprint=0.41

**Rule trace:**

- `RULE_OWNERSHIP_CONFLICT` (w=0.35) — Conflicting ownership claims detected on submitted recording. · [GDPR Art 22, DSA Art 17(3)(b)]
- `RULE_FINGERPRINT_PARTIAL` (w=0.25) — Partial acoustic fingerprint match against an existing recording. · [DSA Art 17(3)(b), DSA Art 14]
- `RULE_NEW_ACCOUNT` (w=0.15) — Uploading account is less than 30 days old. · [DSA Art 14]
- `RULE_STATEMENT_OF_REASONS` (w=0.0) — Structured statement of reasons emitted per DSA Art 17. · [DSA Art 17(1), DSA Art 17(3)(a), DSA Art 17(3)(b), DSA Art 17(3)(c), DSA Art 17(3)(f)]
- `RULE_HUMAN_REVIEW_ROUTING` (w=0.0) — Decision routed to human reviewer (GDPR Art 22 / AI Act Art 14 / DSA Art 20). · [GDPR Art 22, AI Act Art 14, DSA Art 20]
- `RULE_PROVENANCE_RECORD` (w=0.0) — Policy version and decision recorded for accountability (GDPR Arts 5(2), 24). · [GDPR Art 24, GDPR Art 5(2)]

**Outcome:** confidence 0.500 · band **Human-Review-Required** · direction concerns_identified · human_review=True · 17(1) quality flag: **specific**

**What it shows:** Two ownership claimants force human review regardless of score (GDPR Art 22; AI Act Art 14; DSA Art 20). The engine's uncertainty is recorded honestly (score 0.500) rather than resolved silently — the design refuses to let automation absorb a significant contested decision.

**Evidence Pack (verbatim):**

```json
{
  "pack_id": "548eebf1-27b3-5894-bed5-41418daa3a3e",
  "decision_timestamp": "2026-07-06T12:00:00Z",
  "policy_version": "0.1.0",
  "confidence_score": 0.5,
  "confidence_band": "Human-Review-Required",
  "triggered_rules": [
    {
      "rule_id": "RULE_OWNERSHIP_CONFLICT",
      "description": "Conflicting ownership claims detected on submitted recording."
    },
    {
      "rule_id": "RULE_FINGERPRINT_PARTIAL",
      "description": "Partial acoustic fingerprint match against an existing recording."
    },
    {
      "rule_id": "RULE_NEW_ACCOUNT",
      "description": "Uploading account is less than 30 days old."
    },
    {
      "rule_id": "RULE_STATEMENT_OF_REASONS",
      "description": "Structured statement of reasons emitted per DSA Art 17."
    },
    {
      "rule_id": "RULE_HUMAN_REVIEW_ROUTING",
      "description": "Decision routed to human reviewer (GDPR Art 22 / AI Act Art 14 / DSA Art 20)."
    },
    {
      "rule_id": "RULE_PROVENANCE_RECORD",
      "description": "Policy version and decision recorded for accountability (GDPR Arts 5(2), 24)."
    }
  ],
  "input_categories": [
    "multiple_ownership_claims",
    "fingerprint_match_partial",
    "account_age_lt_30d"
  ],
  "regulatory_mapping": {
    "DSA Art 17(1)": {
      "rule_id": "RULE_STATEMENT_OF_REASONS",
      "status": "evidenced"
    },
    "DSA Art 17(3)(a)": {
      "rule_id": "RULE_STATEMENT_OF_REASONS",
      "status": "evidenced"
    },
    "DSA Art 17(3)(b)": {
      "rule_id": "RULE_STATEMENT_OF_REASONS",
      "status": "evidenced"
    },
    "DSA Art 17(3)(c)": {
      "rule_id": "RULE_STATEMENT_OF_REASONS",
      "status": "evidenced"
    },
    "DSA Art 17(3)(f)": {
      "rule_id": "RULE_STATEMENT_OF_REASONS",
      "status": "evidenced"
    },
    "GDPR Art 22": {
      "rule_id": "RULE_HUMAN_REVIEW_ROUTING",
      "status": "evidenced"
    },
    "AI Act Art 14": {
      "rule_id": "RULE_HUMAN_REVIEW_ROUTING",
      "status": "evidenced"
    },
    "DSA Art 20": {
      "rule_id": "RULE_HUMAN_REVIEW_ROUTING",
      "status": "evidenced"
    },
    "GDPR Art 24": {
      "rule_id": "RULE_PROVENANCE_RECORD",
      "status": "evidenced"
    },
    "GDPR Art 5(2)": {
      "rule_id": "RULE_PROVENANCE_RECORD",
      "status": "evidenced"
    },
    "DSA Art 14": {
      "rule_id": "RULE_FINGERPRINT_PARTIAL",
      "status": "evidenced"
    },
    "DSA Art 17 \u2014 statement of reasons": {
      "action_context": "routed_to_human_review",
      "facts_relied_on": [
        "multiple_ownership_claims",
        "fingerprint_match_partial",
        "account_age_lt_30d"
      ],
      "automated_means_used": true,
      "legal_ground": null,
      "contractual_ground": "distributor terms: metadata, ownership and originality requirements",
      "redress": "internal-complaint-v1",
      "quality_flag_17_4": "specific"
    }
  },
  "plain_english_explanation": "This submission was assessed by an automated system using policy version 0.1.0. The system's confidence in its assessment is 0.500 (Human-Review-Required). The assessment relied on the following observations: more than one party claims ownership of this recording; the audio partially matches an existing recording; the uploading account was created less than 30 days ago. This outcome has been routed to a human reviewer and no automated restriction takes effect on its own. You can contest or ask about this outcome via: internal-complaint-v1. This record is a readiness signal produced by compliance-support software. It is not a legal determination and does not constitute legal advice.",
  "oversight_pathway": "internal-complaint-v1",
  "retention_reference": "retention-policy-v1 (synthetic demo: indefinite)",
  "integrity_hash": "e586698322deb6f9aa92dd1546a12305e93cc7b808a8ed2188a0f03c96962ef5"
}
```


---

## Edge case 3 — Thin reasons (form without sufficiency)

**Input (synthetic):** claims=1, account_age=90d, takedowns=0, fingerprint=0.55

**Rule trace:**

- `RULE_FINGERPRINT_PARTIAL` (w=0.25) — Partial acoustic fingerprint match against an existing recording. · [DSA Art 17(3)(b), DSA Art 14]
- `RULE_STATEMENT_OF_REASONS` (w=0.0) — Structured statement of reasons emitted per DSA Art 17. · [DSA Art 17(1), DSA Art 17(3)(a), DSA Art 17(3)(b), DSA Art 17(3)(c), DSA Art 17(3)(f)]
- `RULE_PROVENANCE_RECORD` (w=0.0) — Policy version and decision recorded for accountability (GDPR Arts 5(2), 24). · [GDPR Art 24, GDPR Art 5(2)]

**Outcome:** confidence 0.500 · band **Medium** · direction no_concerns_identified · human_review=False · 17(1) quality flag: **informational**

**What it shows:** One weak signal produces a structurally complete statement of reasons — every 17(3) field populated — that the engine itself flags as 'thin' against 17(1)'s clear-and-specific standard. The artefact can guarantee FORM but not SUFFICIENCY. This single flag carries the boundary thesis.

**Evidence Pack (verbatim):**

```json
{
  "pack_id": "b722aef3-f514-5d3c-a2ae-16222ca880c7",
  "decision_timestamp": "2026-07-06T12:00:00Z",
  "policy_version": "0.1.0",
  "confidence_score": 0.5,
  "confidence_band": "Medium",
  "triggered_rules": [
    {
      "rule_id": "RULE_FINGERPRINT_PARTIAL",
      "description": "Partial acoustic fingerprint match against an existing recording."
    },
    {
      "rule_id": "RULE_STATEMENT_OF_REASONS",
      "description": "Structured statement of reasons emitted per DSA Art 17."
    },
    {
      "rule_id": "RULE_PROVENANCE_RECORD",
      "description": "Policy version and decision recorded for accountability (GDPR Arts 5(2), 24)."
    }
  ],
  "input_categories": [
    "fingerprint_match_partial"
  ],
  "regulatory_mapping": {
    "DSA Art 17(1)": {
      "rule_id": "RULE_STATEMENT_OF_REASONS",
      "status": "evidenced"
    },
    "DSA Art 17(3)(a)": {
      "rule_id": "RULE_STATEMENT_OF_REASONS",
      "status": "evidenced"
    },
    "DSA Art 17(3)(b)": {
      "rule_id": "RULE_STATEMENT_OF_REASONS",
      "status": "evidenced"
    },
    "DSA Art 17(3)(c)": {
      "rule_id": "RULE_STATEMENT_OF_REASONS",
      "status": "evidenced"
    },
    "DSA Art 17(3)(f)": {
      "rule_id": "RULE_STATEMENT_OF_REASONS",
      "status": "evidenced"
    },
    "GDPR Art 24": {
      "rule_id": "RULE_PROVENANCE_RECORD",
      "status": "evidenced"
    },
    "GDPR Art 5(2)": {
      "rule_id": "RULE_PROVENANCE_RECORD",
      "status": "evidenced"
    },
    "DSA Art 14": {
      "rule_id": "RULE_FINGERPRINT_PARTIAL",
      "status": "evidenced"
    },
    "DSA Art 17 \u2014 statement of reasons": {
      "action_context": "no_restriction_indicated",
      "facts_relied_on": [
        "fingerprint_match_partial"
      ],
      "automated_means_used": true,
      "legal_ground": null,
      "contractual_ground": "distributor terms: metadata, ownership and originality requirements",
      "redress": "internal-complaint-v1",
      "quality_flag_17_4": "informational"
    }
  },
  "plain_english_explanation": "This submission was assessed by an automated system using policy version 0.1.0. The system's confidence in its assessment is 0.500 (Medium). The assessment relied on the following observations: the audio partially matches an existing recording. You can contest this outcome via: internal-complaint-v1. This record is a readiness signal produced by compliance-support software. It is not a legal determination and does not constitute legal advice.",
  "oversight_pathway": "internal-complaint-v1",
  "retention_reference": "retention-policy-v1 (synthetic demo: indefinite)",
  "integrity_hash": "c9fd78ba9ad534025f06a3297cc4d8d7204e04c68675c55b6f97f893820c98fc"
}
```


---

## Edge case 4 — Judgment illusion (confident evidence is still not adjudication)

**Input (synthetic):** claims=1, account_age=12d, takedowns=2, fingerprint=0.93

**Rule trace:**

- `RULE_FINGERPRINT_STRONG` (w=0.55) — Strong acoustic fingerprint match against an existing recording. · [DSA Art 17(3)(b), DSA Art 14]
- `RULE_NEW_ACCOUNT` (w=0.15) — Uploading account is less than 30 days old. · [DSA Art 14]
- `RULE_TAKEDOWN_HISTORY` (w=0.25) — Account has one or more prior takedowns. · [DSA Art 14]
- `RULE_STATEMENT_OF_REASONS` (w=0.0) — Structured statement of reasons emitted per DSA Art 17. · [DSA Art 17(1), DSA Art 17(3)(a), DSA Art 17(3)(b), DSA Art 17(3)(c), DSA Art 17(3)(f)]
- `RULE_PROVENANCE_RECORD` (w=0.0) — Policy version and decision recorded for accountability (GDPR Arts 5(2), 24). · [GDPR Art 24, GDPR Art 5(2)]

**Outcome:** confidence 0.900 · band **High** · direction concerns_identified · human_review=False · 17(1) quality flag: **specific**

**What it shows:** Strong signals produce a confident (0.900, High) concern. The pack reads authoritative — yet legal_ground is null by design: the engine never characterised anything as illegal. The risk is the reader treating evidence AS adjudication; the design answers with disclosure, not capability.

**Evidence Pack (verbatim):**

```json
{
  "pack_id": "501f5e7b-fc1f-5b4b-9284-24b22802afcb",
  "decision_timestamp": "2026-07-06T12:00:00Z",
  "policy_version": "0.1.0",
  "confidence_score": 0.9,
  "confidence_band": "High",
  "triggered_rules": [
    {
      "rule_id": "RULE_FINGERPRINT_STRONG",
      "description": "Strong acoustic fingerprint match against an existing recording."
    },
    {
      "rule_id": "RULE_NEW_ACCOUNT",
      "description": "Uploading account is less than 30 days old."
    },
    {
      "rule_id": "RULE_TAKEDOWN_HISTORY",
      "description": "Account has one or more prior takedowns."
    },
    {
      "rule_id": "RULE_STATEMENT_OF_REASONS",
      "description": "Structured statement of reasons emitted per DSA Art 17."
    },
    {
      "rule_id": "RULE_PROVENANCE_RECORD",
      "description": "Policy version and decision recorded for accountability (GDPR Arts 5(2), 24)."
    }
  ],
  "input_categories": [
    "fingerprint_match_strong",
    "account_age_lt_30d",
    "prior_takedowns_present"
  ],
  "regulatory_mapping": {
    "DSA Art 17(1)": {
      "rule_id": "RULE_STATEMENT_OF_REASONS",
      "status": "evidenced"
    },
    "DSA Art 17(3)(a)": {
      "rule_id": "RULE_STATEMENT_OF_REASONS",
      "status": "evidenced"
    },
    "DSA Art 17(3)(b)": {
      "rule_id": "RULE_STATEMENT_OF_REASONS",
      "status": "evidenced"
    },
    "DSA Art 17(3)(c)": {
      "rule_id": "RULE_STATEMENT_OF_REASONS",
      "status": "evidenced"
    },
    "DSA Art 17(3)(f)": {
      "rule_id": "RULE_STATEMENT_OF_REASONS",
      "status": "evidenced"
    },
    "GDPR Art 24": {
      "rule_id": "RULE_PROVENANCE_RECORD",
      "status": "evidenced"
    },
    "GDPR Art 5(2)": {
      "rule_id": "RULE_PROVENANCE_RECORD",
      "status": "evidenced"
    },
    "DSA Art 14": {
      "rule_id": "RULE_FINGERPRINT_STRONG",
      "status": "evidenced"
    },
    "DSA Art 17 \u2014 statement of reasons": {
      "action_context": "flagged_with_concerns",
      "facts_relied_on": [
        "fingerprint_match_strong",
        "account_age_lt_30d",
        "prior_takedowns_present"
      ],
      "automated_means_used": true,
      "legal_ground": null,
      "contractual_ground": "distributor terms: metadata, ownership and originality requirements",
      "redress": "internal-complaint-v1",
      "quality_flag_17_4": "specific"
    }
  },
  "plain_english_explanation": "This submission was assessed by an automated system using policy version 0.1.0. The system's confidence in its assessment is 0.900 (High). The assessment relied on the following observations: the audio strongly matches an existing recording; the uploading account was created less than 30 days ago; the uploading account has previous takedowns. You can contest this outcome via: internal-complaint-v1. This record is a readiness signal produced by compliance-support software. It is not a legal determination and does not constitute legal advice.",
  "oversight_pathway": "internal-complaint-v1",
  "retention_reference": "retention-policy-v1 (synthetic demo: indefinite)",
  "integrity_hash": "5d6bcd5eeaf9ba52c33ec5c404eb18f542f5b427c3e4c5319415dde8f2e1bec1"
}
```
