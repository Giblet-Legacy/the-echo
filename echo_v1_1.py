"""
echo_v1_1.py — The Echo v1.1, on the current layers

Function:
    The layer above The Echo v1.0.0 (echo.py), and the entry point to
    run from v1.1 on. Same three questions, same output and CLI, but:
    memory comes from P9 substrate_v3 (read-only, verified), the gate
    is P13 v2 and fails closed on unverified or faceless memory, rule
    previews run through P12 rules_v3 on the real engine (dry run), and
    λ comes from P14 V3 in days with P9's ISO 8601 timestamps parsed
    correctly (SPEC_V1_1.md).

    echo.py is not edited.

Public API:
    1. echo(db_path, hypothetical, rules_path=None, now_ts=None) -> dict
    2. main(argv) -> int   (v1.0.0's CLI, running this echo)

Internal helpers (not exported):
    3. _layer   — sibling layer import by directory and module name
    4. _face_of — `face` key, else the single filled face, else None
    5. _epoch   — P9 created_at → epoch seconds, or None
    6. _rules   — rules_v3 preview of the hypothetical, signed by a throwaway key

Tier:     Tier 1 — Consumer (The Mirror)
Depends:  P9 substrate_v3, P12 rules_v3, P13 datacube_v2,
          P14 leighton_engine_v3, P2 sign_v2
Spec:     SPEC_V1_1.md 1.1.0 (over SPEC.md 1.0.0)
Version:  1.1.0
Licence:  MSL-1.0
Author:   James Gilbert (Giblets Forge)
"""

import importlib
import os
import sys
import time
from datetime import datetime

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import echo as _v1  # noqa: E402

_FACES = _v1._FACES
LAMBDA_ZERO = 1.5


# ---------------------------------------------------------------------------
# 3. _layer
# ---------------------------------------------------------------------------
def _layer(dirname, modname):
    path = os.path.abspath(os.path.join(_HERE, "..", dirname))
    if path not in sys.path:
        sys.path.insert(0, path)
    return importlib.import_module(modname)


# ---------------------------------------------------------------------------
# 4. _face_of
# ---------------------------------------------------------------------------
def _face_of(capsule):
    if capsule.get("face") in _FACES:
        return capsule["face"]
    filled = [f for f in _FACES if isinstance(capsule.get(f), str) and capsule[f]]
    return filled[0] if len(filled) == 1 else None


# ---------------------------------------------------------------------------
# 5. _epoch
# ---------------------------------------------------------------------------
def _epoch(created_at):
    try:
        return datetime.fromisoformat(created_at).timestamp()
    except (TypeError, ValueError):
        pass
    try:
        return float(created_at)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# 6. _rules
#    SPEC_V1_1 §4. Invalid rule files raise ValueError (rules_v3).
# ---------------------------------------------------------------------------
def _rules(rules_path, hypothetical):
    if not rules_path:
        return []
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    rules_v3 = _layer("rules-layer", "rules_v3")
    sign_v2 = _layer("sign-layer", "sign_v2")
    with open(rules_path, encoding="utf-8") as f:
        rules = rules_v3.load_rules(f.read())
    key = Ed25519PrivateKey.generate()
    capsule = sign_v2.sign_capsule(dict(hypothetical, signature=None), key)
    return rules_v3.preview(rules, capsule, key.public_key())


# ---------------------------------------------------------------------------
# 1. echo
#    SPEC_V1_1 §2–§5.
# ---------------------------------------------------------------------------
def echo(db_path, hypothetical, rules_path=None, now_ts=None):
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"database missing: {db_path}")
    now = time.time() if now_ts is None else now_ts
    substrate = _layer("substrate-layer", "substrate_v3")

    rows = substrate.list_claims(db_path, verify=True)
    unverified = sum(1 for r in rows if not r["verified"])
    existing = []
    for r in rows:
        if not r["verified"]:
            continue
        cap = r["capsule"] or {}
        existing.append({"claim_id": r["claim_id"], "subject": cap.get("subject", ""),
                         "object": cap.get("object", ""), "face": _face_of(cap),
                         "created_at": _epoch(r["created_at"])})

    face = (hypothetical.get("face") or "").upper()
    gate_passed, gate_reason = True, ""
    if face == "UNKNOWN":
        faceless = [e for e in existing if e["face"] is None]
        if unverified:
            gate_passed, gate_reason = False, f"memory has {unverified} unverified claim(s); gate fails closed"
        elif faceless:
            gate_passed, gate_reason = False, f"claim {faceless[0]['claim_id'][:12]} has no single face; gate fails closed"
        else:
            try:
                _layer("datacube-layer", "datacube_v2").keystone_gate(
                    hypothetical, [{"subject": e["subject"], "object": e["object"], "face": e["face"]}
                                   for e in existing])
            except ValueError as e:
                gate_passed, gate_reason = False, str(e)

    rules_fired = _rules(rules_path, hypothetical)

    le = _layer("leighton-engine-layer", "leighton_engine_v3")
    resolves = []
    for e in existing:
        if e["face"] != "UNKNOWN" or e["subject"] != hypothetical.get("subject") or e["created_at"] is None:
            continue
        ref = max(now, e["created_at"])
        lam = le.compute_lambda([{"timestamp": e["created_at"], "value": LAMBDA_ZERO}],
                                le.STACK_CLAIM_K, ref, now, time_unit=le.STACK_TIME_UNIT)["lambda"]
        resolves.append({"claim_id": e["claim_id"], "subject": e["subject"],
                         "object": e["object"], "lambda": lam})

    return {
        "hypothetical": hypothetical,
        "gate": {"passed": gate_passed, "reason": gate_reason},
        "rules_fired": rules_fired,
        "shape": {
            "resolves": resolves,
            "introduces": 1 if face == "UNKNOWN" else 0,
            "max_drift": max([LAMBDA_ZERO - r["lambda"] for r in resolves] + [0.0]),
        },
        "memory": {"claims": len(rows), "unverified": unverified},
    }


# ---------------------------------------------------------------------------
# 2. main
#    v1.0.0's CLI (parsing, printing, exit codes), with this echo in place
#    of v1's for the duration of the call only.
# ---------------------------------------------------------------------------
def main(argv):
    saved = _v1.echo
    _v1.echo = echo
    try:
        return _v1.main(argv)
    finally:
        _v1.echo = saved


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
