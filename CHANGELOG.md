# CHANGELOG — the-echo (Tier 1: The Echo)

CHANGELOG.md — build history for The Echo, latest entry at top.

## [Unreleased]

### Good

- (none)

### Bad

- (none)

### Ugly

- (none)

## [v1.1.0] — 2026-11-13 — FROZEN

### Good

- `SPEC_V1_1.md`, `test_echo_v1_1.py` (6 tests, run red first) and `echo_v1_1.py`: memory read through P9 substrate_v3 (read-only, verified); gate is P13 v2 and fails closed on unverified or faceless memory; rule previews run through P12 rules_v3 on the real engine in dry-run mode (the Echo's matcher format is now the stack's declarative rule format); λ from P14 V3 in days. v1.0.0's CLI and exit codes reused. 21/21 pass.
- Built on James's delegation ("fix all 11 issues"). Frozen at 1.1.0 on James's sign-off ("freeze all", 2026-11-13).

### Bad

- Frozen on the laptop run alone (2026-11-13); the S24 run is still to be confirmed.
- v1.0.0 parsed P9's ISO 8601 `created_at` with `float()`, so on a real substrate every dream's age ran from 1970: drift was always the maximum (0.5). A broken rules file was silently "no rules". Pinned in test_echo_v1_1; fixed in v1.1.

### Ugly

- (none)

## [v1.0.0] — 2026-11-13

### Good
- Repository scaffolded: `Giblet-Legacy/the-echo` created as Tier 1
  Consumer (The Mirror).
- `echo.py` implemented to SPEC v1.0.0.
- 15/15 pytest tests pass.
- Three-question introspection for any hypothetical claim:
  - Gate preview (contradiction check via P13 keystone_gate).
  - Rules preview (simple matcher for subject/face/object).
  - Shape projection (resolvable dreams, max drift via P14).
- Read-only discipline enforced: opens `forge.db` with `mode=ro`.
- Trust drift uses k in days⁻¹ (Weaver's resolved convention).
- No LLLM. Numeric simulation only.

### Bad
- (none)

### Ugly
- (none)
