"""
test_echo_v1_1.py — The Echo v1.1 (current-layer reader) test suite

Function:
    Executable expression of SPEC_V1_1.md. Written before echo_v1_1.py
    and run red first. Uses a substrate written by P9 itself.

Functions in this file (pytest-collected):
    1. test_drift_on_real_substrate
    2. test_gate
    3. test_gate_fails_closed_on_tampered_memory
    4. test_rules_through_p12
    5. test_read_only
    6. test_cli_exit_codes

Fixtures and helpers:
    7. home  — FORGE_HOME with FACT, FICTION and an aged UNKNOWN claim
    8. _age  — set a claim's created_at to N days ago

Tier:     Tier 1 — Consumer (The Mirror)
Spec:     SPEC_V1_1.md 1.1.0
Licence:  MSL-1.0
Author:   James Gilbert (Giblets Forge)
"""

import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = os.path.dirname(os.path.abspath(__file__))
for _p in (ROOT, os.path.join(ROOT, "..", "substrate-layer")):
    if os.path.abspath(_p) not in sys.path:
        sys.path.insert(0, os.path.abspath(_p))

import substrate_v3  # noqa: E402
import echo  # noqa: E402
import echo_v1_1  # noqa: E402

KEY = Ed25519PrivateKey.generate()


# 8. _age
def _age(db, claim_id, days):
    ts = datetime.fromtimestamp(time.time() - days * 86400, tz=timezone.utc).isoformat()
    conn = sqlite3.connect(db)
    with conn:
        conn.execute("UPDATE claims SET created_at=? WHERE claim_id=?", (ts, claim_id))
    conn.close()


# 7. home
@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("FORGE_HOME", str(tmp_path))
    db = str(tmp_path / "forge.db")
    substrate_v3.init_db(db)
    fact = substrate_v3.write_claim(db, {"subject": "sky", "object": "blue",
                                         "FACT": "The sky is blue", "face": "FACT"}, KEY)
    substrate_v3.write_claim(db, {"subject": "moon", "object": "cheese",
                                  "FICTION": "The moon is cheese", "face": "FICTION"}, KEY)
    dream = substrate_v3.write_claim(db, {"subject": "tide", "object": "late",
                                          "UNKNOWN": "Why is the tide late?", "face": "UNKNOWN"}, KEY)
    _age(db, dream, 10)
    return db, fact, dream


# 1. test_drift_on_real_substrate
def test_drift_on_real_substrate(home):
    db, _, dream = home
    hyp = {"subject": "tide", "object": "moon", "text": "The moon pulls the tide", "face": "FACT"}
    out = echo_v1_1.echo(db, hyp)
    (r,) = out["shape"]["resolves"]
    assert r["claim_id"] == dream and r["lambda"] == pytest.approx(1.1839, abs=1e-3)
    assert out["shape"]["max_drift"] == pytest.approx(0.316, abs=1e-3)
    assert out["memory"] == {"claims": 3, "unverified": 0}
    assert echo.echo(db, hyp)["shape"]["max_drift"] == pytest.approx(0.5, abs=1e-3)  # v1 defect, pinned


# 2. test_gate
def test_gate(home):
    db, _, _ = home
    assert echo_v1_1.echo(db, {"subject": "sky", "object": "green", "face": "UNKNOWN"})["gate"]["passed"] is False
    assert echo_v1_1.echo(db, {"subject": "moon", "object": "rock", "face": "UNKNOWN"})["gate"]["passed"] is True
    assert echo_v1_1.echo(db, {"subject": "sky", "object": "green", "face": "OPINION"})["gate"]["passed"] is True


# 3. test_gate_fails_closed_on_tampered_memory
def test_gate_fails_closed_on_tampered_memory(home):
    db, fact, _ = home
    conn = sqlite3.connect(db)
    with conn:
        text = conn.execute("SELECT capsule FROM claims WHERE claim_id=?", (fact,)).fetchone()[0]
        conn.execute("UPDATE claims SET capsule=? WHERE claim_id=?", (text.replace("blue", "teal"), fact))
    conn.close()
    out = echo_v1_1.echo(db, {"subject": "sea", "object": "deep", "face": "UNKNOWN"})
    assert out["gate"]["passed"] is False and "unverified" in out["gate"]["reason"]
    assert out["memory"]["unverified"] == 1


# 4. test_rules_through_p12
def test_rules_through_p12(home, tmp_path):
    db, _, _ = home
    rules = tmp_path / "rules.json"
    rules.write_text(json.dumps([
        {"name": "dreams", "predicate_spec": {"face_matches": ["UNKNOWN"]}, "action_spec": {}},
        {"name": "tides", "predicate_spec": {"subject_matches": "tide"}, "action_spec": {}, "priority": 5},
        {"name": "never", "predicate_spec": {"object_contains": "zzz"}, "action_spec": {}},
    ]))
    hyp = {"subject": "tide", "object": "early", "face": "UNKNOWN"}
    assert echo_v1_1.echo(db, hyp, rules_path=str(rules))["rules_fired"] == ["tides", "dreams"]
    assert echo_v1_1.echo(db, hyp)["rules_fired"] == []
    rules.write_text(json.dumps([{"name": "typo", "predicate_spec": {"subjct": "x"}}]))
    with pytest.raises(ValueError):
        echo_v1_1.echo(db, hyp, rules_path=str(rules))


# 5. test_read_only
def test_read_only(home):
    db, _, _ = home
    before = open(db, "rb").read()
    echo_v1_1.echo(db, {"subject": "tide", "object": "x", "face": "UNKNOWN"})
    assert open(db, "rb").read() == before


# 6. test_cli_exit_codes
def test_cli_exit_codes(home, capsys):
    assert echo_v1_1.main(["sky | grey | maybe grey", "--face", "UNKNOWN"]) == 1
    assert echo_v1_1.main(["sea | deep | how deep", "--face", "UNKNOWN"]) == 0
    assert echo_v1_1.main(["sea | deep | how deep"]) == 2
    out = capsys.readouterr().out
    assert "Gate: REJECTED" in out and "Gate: PASSED" in out
    assert echo.echo is not echo_v1_1.echo
