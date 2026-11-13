# SPEC V1.1 — the-echo (Tier 1: The Echo, current-layer reader)

SPEC_V1_1.md — specification for echo_v1_1.py, the layer above Echo v1.0.0.

Function:
    Moves The Echo onto P9's read API, P12's real engine, P13 v2's gate
    and P14's unit rule. echo.py v1.0.0 is not edited. Where this
    document is silent, SPEC.md 1.0.0 applies unchanged, including the
    output shape, the CLI and its exit codes.

Tier:     Tier 1 — Consumer (The Mirror)
Depends:  P9 substrate_v3 (read-only), P12 rules_v3, P13 datacube_v2,
          P14 leighton_engine_v3, P2 sign_v2 (preview signing)
Version:  SPEC 1.1.0
Licence:  MSL-1.0
Author:   James Gilbert (Giblets Forge)

---

## 1. Why v1.1

- v1.0.0 read `created_at` with `float()`; P9 writes ISO 8601, so
  every real claim's age was measured from 1970 and its "trust drift"
  was always the maximum. Trust used P14 v1 with a hand conversion.
- Its "P12 preview" was its own matcher, and a broken rules file was
  silently treated as no rules.
- It read `forge.db` with its own SQL and never verified a claim, and
  gated with P13 v1 (mis-cased faces skipped, any claim with a filled
  face taken as that face).

## 2. Memory

Active claims come from `substrate_v3.list_claims(db, verify=True)`
(read-only). A claim's face is its `face` key, else its single filled
face. The result gains `memory: {claims: int, unverified: int}`.

## 3. The Gate (fails closed)

For an UNKNOWN hypothetical, the gate does not pass if any active
claim fails verification ("memory has N unverified claim(s)") or has
no single face; otherwise datacube_v2 `keystone_gate` decides. Non-
UNKNOWN hypotheticals pass, as in v1.0.0.

## 4. The Rules

`--rules <path>` is loaded with `rules_v3.load_rules` (the stack's
declarative format, which is the Echo's v1.0.0 format). An invalid
file is an error (exit 1, "echo failed: …"), not "no rules". The
hypothetical is signed with a fresh throwaway key and previewed with
`rules_v3.preview` — the real v2 engine in dry-run mode. No action
runs.

## 5. The Shape

As SPEC.md §1.3, with `created_at` parsed as ISO 8601 (numeric
accepted) and λ from `leighton_engine_v3.compute_lambda` with
`STACK_CLAIM_K` and `time_unit = STACK_TIME_UNIT` (days).

## 6. Tests (test_echo_v1_1.py)

- On a substrate written by P9 itself, a 10-day-old dream shows
  λ ≈ 1.18 and drift ≈ 0.32; v1.0.0 on the same file shows ≈ 1.00
  (pins the defect).
- Gate: contradiction rejected; FICTION does not block; a tampered
  claim makes an UNKNOWN fail closed; non-UNKNOWN passes.
- Rules: fired through rules_v3 in engine order; an invalid rules
  file raises; no file → no rules.
- Read-only: database bytes unchanged.
- CLI: v1.0.0 exit codes (0 pass, 1 reject, 2 usage).

---

## Document control

- **SPEC 1.1.0** — 2026-11-13, by the VS Code AI on James's delegation
  ("fix all 11 issues").
