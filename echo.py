"""
echo.py — The Echo primitive layer

Function:
    The introspective consumer. Given a hypothetical claim, simulate
    the consequences of committing it — without committing anything.
    Read-only. Answers three questions: would the Keystone Gate reject
    it, what rules would fire, what shape would the mind be after.

Public API:
    1. echo(db_path, hypothetical, rules_path=None, now_ts=None) -> dict
    2. main(argv) -> int

Tier:     Tier 1 — Consumer (The Mirror)
Depends:  P9 Substrate (read-only), P13 DataCube, P14 Leighton Engine
Version:  1.0.0 (on freeze; 0.0.0-dev until then)
Licence:  MSL-1.0
Author:   James Gilbert (Giblets Forge)
"""

import os
import sys
import json
import sqlite3
import time

_FACES = ("FACT", "COUNTER", "OPINION", "FICTION", "CONTEXT", "UNKNOWN")
_DEFAULT_LAMBDA_0 = 1.5
_DEFAULT_K = 0.1

_LAYER_CACHE = {}


# ---------------------------------------------------------------------------
# Lazy layer loader. Finds datacube and leighton-engine siblings.
# ---------------------------------------------------------------------------
def _layer(name):
    if name in _LAYER_CACHE:
        return _LAYER_CACHE[name]
    here = os.path.dirname(os.path.abspath(__file__))
    mapping = {
        "datacube": ("datacube-layer", "datacube"),
        "leighton-engine": ("leighton-engine-layer", "leighton_engine"),
        "envelope": ("envelope-layer", "envelope_v2"),
    }
    dirname, modname = mapping.get(name, (name + "-layer", name))
    p = os.path.abspath(os.path.join(here, "..", dirname))
    if not os.path.isdir(p):
        raise RuntimeError(f"layer '{name}' not found at {p}")
    if p not in sys.path:
        sys.path.insert(0, p)
    import importlib
    mod = importlib.import_module(modname)
    _LAYER_CACHE[name] = mod
    return mod


def _forge_home():
    home = os.environ.get("FORGE_HOME")
    if not home:
        home = os.path.expanduser("~/.forge")
    return home


def _db_path():
    return os.path.join(_forge_home(), "forge.db")


# ---------------------------------------------------------------------------
# _extract_face
#    Returns the face name of a stored capsule by looking for the
#    non-None face key. Returns None if no face is set.
# ---------------------------------------------------------------------------
def _extract_face(capsule):
    for face in _FACES:
        if capsule.get(face) is not None:
            return face
    return None


# ---------------------------------------------------------------------------
# _matches
#    Simple predicate matcher for the rules preview. Supports
#    subject_matches (exact or "*"), face_matches (list), and
#    object_contains (substring).
# ---------------------------------------------------------------------------
def _matches(rule, hypothetical):
    spec = rule.get("predicate_spec", {})
    if "subject_matches" in spec:
        pattern = spec["subject_matches"]
        if pattern != "*" and hypothetical.get("subject") != pattern:
            return False
    if "face_matches" in spec:
        if hypothetical.get("face") not in spec["face_matches"]:
            return False
    if "object_contains" in spec:
        if spec["object_contains"] not in (hypothetical.get("object") or ""):
            return False
    return True


# ---------------------------------------------------------------------------
# echo
#    The simulation. Reads the substrate read-only, runs the gate,
#    previews rules, projects the shape of the mind.
# ---------------------------------------------------------------------------
def echo(db_path, hypothetical, rules_path=None, now_ts=None):
    if now_ts is None:
        now_ts = time.time()

    if not os.path.exists(db_path):
        raise FileNotFoundError(f"database missing: {db_path}")

    # Read-only connection. Any write attempt fails at the SQLite level.
    uri = f"file:{db_path}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        rows = conn.execute(
            "SELECT claim_id, capsule, created_at FROM claims WHERE is_active = 1"
        ).fetchall()
    finally:
        conn.close()

    existing = []
    for cid, cap_json, created_at in rows:
        try:
            cap = json.loads(cap_json)
        except json.JSONDecodeError:
            continue
        try:
            created_ts = float(created_at) if created_at else 0.0
        except (TypeError, ValueError):
            created_ts = 0.0
        existing.append({
            "claim_id": cid,
            "subject": cap.get("subject", ""),
            "object": cap.get("object", ""),
            "face": _extract_face(cap),
            "created_at": created_ts,
        })

    face = (hypothetical.get("face") or "").upper()
    gate_passed = True
    gate_reason = ""

    if face == "UNKNOWN":
        gate_input = [
            {"subject": e["subject"], "object": e["object"], "face": e["face"]}
            for e in existing
        ]
        try:
            dc = _layer("datacube")
            dc.keystone_gate(hypothetical, gate_input)
            gate_passed = True
        except ValueError as e:
            gate_passed = False
            gate_reason = str(e)
        except Exception as e:
            gate_passed = False
            gate_reason = f"gate error: {e}"

    rules_fired = []
    if rules_path:
        try:
            with open(rules_path) as f:
                rules = json.load(f)
        except (json.JSONDecodeError, IOError):
            rules = []
        for rule in rules:
            if _matches(rule, hypothetical):
                rules_fired.append(rule.get("name", "unnamed"))

    resolves = []
    for e in existing:
        if e["face"] != "UNKNOWN":
            continue
        if e["subject"] != hypothetical.get("subject"):
            continue
        try:
            le = _layer("leighton-engine")
            created_days = e["created_at"] / 86400.0
            now_days = now_ts / 86400.0
            lam = le.compute_lambda(
                [{"timestamp": created_days, "value": _DEFAULT_LAMBDA_0}],
                k=_DEFAULT_K,
                reference_time=now_days,
                computed_at=now_ts,
            )["lambda"]
        except Exception:
            continue
        resolves.append({
            "claim_id": e["claim_id"],
            "subject": e["subject"],
            "object": e["object"],
            "lambda": lam,
        })

    max_drift = 0.0
    for r in resolves:
        drift = _DEFAULT_LAMBDA_0 - r["lambda"]
        if drift > max_drift:
            max_drift = drift

    introduces = 1 if face == "UNKNOWN" else 0

    return {
        "hypothetical": hypothetical,
        "gate": {"passed": gate_passed, "reason": gate_reason},
        "rules_fired": rules_fired,
        "shape": {
            "resolves": resolves,
            "introduces": introduces,
            "max_drift": max_drift,
        },
    }


# ---------------------------------------------------------------------------
# main
#    CLI entry point. Exit codes: 0 passed, 1 rejected/failed, 2 usage.
# ---------------------------------------------------------------------------
def main(argv):
    if not argv:
        print("usage: echo '<subject> | <object> | <text>' --face <FACE> [--rules <path>]",
              file=sys.stderr)
        return 2

    face = None
    rules_path = None
    positional = []

    i = 0
    while i < len(argv):
        if argv[i] == "--face":
            if i + 1 >= len(argv):
                print("--face requires a value", file=sys.stderr)
                return 2
            face = argv[i + 1].upper()
            i += 2
        elif argv[i] == "--rules":
            if i + 1 >= len(argv):
                print("--rules requires a value", file=sys.stderr)
                return 2
            rules_path = argv[i + 1]
            i += 2
        else:
            positional.append(argv[i])
            i += 1

    if face is None:
        print("--face is required", file=sys.stderr)
        return 2
    if face not in _FACES:
        print(f"invalid face: {face}", file=sys.stderr)
        return 2
    if not positional:
        print("missing claim argument", file=sys.stderr)
        return 2

    claim_str = " ".join(positional)
    parts = [p.strip() for p in claim_str.split("|")]
    if len(parts) != 3:
        print("claim must be '<subject> | <object> | <text>'", file=sys.stderr)
        return 2
    subject, obj, text = parts
    hypothetical = {"subject": subject, "object": obj, "text": text, "face": face}

    db_path = _db_path()
    if not os.path.exists(db_path):
        print(f"database missing: {db_path}", file=sys.stderr)
        return 1

    try:
        result = echo(db_path, hypothetical, rules_path=rules_path)
    except Exception as e:
        print(f"echo failed: {e}", file=sys.stderr)
        return 1

    if result["gate"]["passed"]:
        print("Gate: PASSED")
    else:
        print(f"Gate: REJECTED — {result['gate']['reason']}")

    if result["rules_fired"]:
        print(f"Rules: {', '.join(result['rules_fired'])}")
    else:
        print("Rules: (none)")

    shape = result["shape"]
    if shape["resolves"]:
        print(f"Shape: would answer {len(shape['resolves'])} existing dream(s):")
        for r in shape["resolves"]:
            print(f"  - [{r['subject']}/{r['object']}] λ={r['lambda']:.3f}")
        print(f"  max drift: {shape['max_drift']:.3f}")
    if shape["introduces"]:
        print(f"Shape: introduces {shape['introduces']} new dream(s)")

    return 0 if result["gate"]["passed"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
