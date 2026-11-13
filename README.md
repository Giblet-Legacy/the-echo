# the-echo — Tier 1: The Echo

README.md — repository purpose and consumer contract for The Echo.

Function:
    The introspective consumer. Given a hypothetical claim, simulate
    the consequences of committing it — without committing anything.
    Read-only. It answers: would the Keystone Gate reject this? What
    rules would fire? What would the shape of the mind look like
    after?

Tier:     Tier 1 — Consumer (The Mirror)
Depends:  P9 Substrate (read-only), P12 Rules, P13 DataCube, P14 Leighton Engine
Licence:  MSL-1.0
Author:   James Gilbert (Giblets Forge)
Status:   1.0.0 frozen (echo.py). v1.1 (echo_v1_1.py, SPEC_V1_1.md) frozen at 1.1.0. Run `python echo_v1_1.py`.

## The three questions

For any hypothetical claim, The Echo answers:

1. **The Gate.** Would the Keystone Gate reject it? (Does it
   contradict a FACT, COUNTER, or CONTEXT?)
2. **The Rules.** What rules would fire on it? (P12 preview.)
3. **The Shape.** What UNKNOWNs would it resolve? What new UNKNOWNs
   would it introduce? What would the substrate look like if it were
   committed?

## What it is not
- Not a write path. It never modifies `forge.db`.
- Not a claim oracle. It does not tell you whether a claim is *true*,
  only whether it would be *accepted* by the system.
- Not a rules engine. It previews rules; it does not fire them.
