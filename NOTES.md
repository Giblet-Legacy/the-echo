# NOTES — the-echo (Tier 1: The Echo)

NOTES.md — open questions and decisions for The Echo.

## Decisions
- Read-only. Opens `forge.db` with `mode=ro`. The Echo cannot
  accidentally damage the substrate.
- Reads P13's `keystone_gate` function directly. If a claim would be
  rejected, it reports the rejection; it does not simulate what would
  have happened if the gate were bypassed.
- Reads P12's rule engine by creating a fresh `Engine`, registering
  the node's current rules (loaded from the ledger), and calling
  `evaluate` against the hypothetical capsule. This previews which
  rules would fire without any of their actions taking effect.
- Calls P14's `compute_lambda` to project how trust would evolve if
  the claim were committed. Reports the projected λ, not just the
  current λ.

## Open questions
- Q1. Rule actions in preview: should the Echo show what each rule's
  action *would* do (by reading the rule's spec) or suppress them?
  v1.0.0 suppresses. Future: a "verbose" mode that describes the
  action without executing it.
- Q2. How to handle the case where the hypothetical claim itself is
  an UNKNOWN that passes the gate — do we report it as a new
  unresolved dream, or as a successful claim? Both, in different
  sections of the output.
- Q3. Simulation depth. The Echo simulates one step (the claim
  itself). Should it simulate cascading rule fires (rules firing on
  the claim's outputs)? v1.0.0 does not — chains are complex enough
  without a simulator.
