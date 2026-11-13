# SPEC — the-echo (Tier 1: The Echo)

SPEC.md — specification for The Echo.

Function:
    The introspective consumer. Given a hypothetical claim, simulate
    the consequences of committing it — without committing anything.
    Read-only. Answers three questions: would the gate reject it,
    what rules would fire, what shape would the mind be after.

Tier:     Tier 1 — Consumer (The Mirror)
Depends:  P9 Substrate (read-only), P12 Rules, P13 DataCube, P14 Leighton Engine
Version:  SPEC 1.0.0
Licence:  MSL-1.0
Author:   James Gilbert (Giblets Forge)

## 1. The Three Questions

For a hypothetical claim `{subject, object, text, face}`:

### 1.1 The Gate
Would P13 `keystone_gate` reject it? If `face == UNKNOWN`, does the
claim contradict an existing FACT/COUNTER/CONTEXT (same subject,
different object)? Return: `{passed: bool, reason: str}`.

### 1.2 The Rules (optional, requires `--rules <path>`)
Load rule definitions from a JSON file. Each rule is:
    {"name": str, "predicate_spec": {...}, "action_spec": {...}}

For v1.0.0 the predicates are simple matchers over the claim:
- `face_matches`: list of face names
- `subject_matches`: string (exact or "*" wildcard)
- `object_contains`: string

Preview which rules would fire. Actions are NOT executed; only the
`name` of each fired rule is returned.

### 1.3 The Shape of the Mind
Using P9 (read-only) and P14:
- **Resolves:** list of existing UNKNOWN claim_ids with the same
  subject as the hypothetical. If the hypothetical is a FACT, these
  dreams would be resolvable (or at least answerable). For v1.0.0
  this is reported as informational; it does not assert that the
  dreams are actually resolved.
- **Introduces:** if the hypothetical is UNKNOWN, report it as one
  new dream being added (count: 1). Otherwise count: 0.
- **Trust drift:** for each resolved claim, compute its current λ
  via P14 (using k in days⁻¹, per the Weaver's resolved convention).
  Report the maximum drift across resolved claims.

## 2. Function Contracts

### 2.1 echo(db_path: str, hypothetical: dict, rules_path: str = None, now_ts: float = None) -> dict
Returns:
    {
      "hypothetical": hypothetical,
      "gate": {"passed": bool, "reason": str},
      "rules_fired": [str, ...],
      "shape": {
        "resolves": [{"claim_id", "subject", "object", "unknown_text", "lambda"}, ...],
        "introduces": int,
        "max_drift": float
      }
    }

### 2.2 main(argv) -> int
Parses CLI args:
- `echo "<subject> | <object> | <text>" --face <FACE> [--rules <path>]`
- Exit 0 if the gate passes, 1 if rejected, 2 on usage error.

## 3. Read-Only Discipline

The Echo opens `forge.db` with `mode=ro`. Any attempt to write will
fail at the SQLite level. This is a hard architectural commitment,
not a soft policy.

## 4. Known Limitations (v1.0.0)

- Rule previews are limited to simple matchers. Does not simulate
  cascading rule fires (rules firing on the claim's outputs).
- Rule actions are not executed and not described; only the rule
  names are returned.
- "Resolves" list is informational. It lists dreams with the same
  subject but does not assert that the hypothetical actually
  resolves them (that is the operator's judgment, not the Echo's).
- Trust drift uses k in days⁻¹ (per the Weaver's resolved convention).
  Per-domain calibration is a v2 concern.
- No LLLM. The Echo is a numeric simulator, not a language model.
