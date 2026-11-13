"""
test_echo.py — The Echo test suite

Function:
    Executable expression of SPEC.md. Written before echo.py per
    build discipline.

Tier:    Tier 1 — Consumer (The Echo)
Spec:    SPEC.md v1.0.0
Licence: MSL-1.0
"""

import os
import sys
import json
import sqlite3
import time
import pytest
from unittest.mock import patch

# Bootstrap: add sibling layers for P13/P14 access
ROOT = os.path.dirname(os.path.abspath(__file__))
for layer in ("envelope-layer", "datacube-layer", "leighton-engine-layer", "rules-layer"):
    p = os.path.abspath(os.path.join(ROOT, "..", layer))
    if os.path.isdir(p):
        sys.path.insert(0, p)

import echo


@pytest.fixture
def forge_home(tmp_path, monkeypatch):
    """Isolated FORGE_HOME with a P9-schema database + a couple of claims."""
    monkeypatch.setenv("FORGE_HOME", str(tmp_path))
    db_path = tmp_path / "forge.db"
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE claims (
            claim_id TEXT PRIMARY KEY,
            signer TEXT NOT NULL,
            capsule TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            superseded_by TEXT,
            created_at TEXT NOT NULL
        )
    """)

    now = time.time()

    def insert(cid, capsule, created_ts):
        conn.execute(
            "INSERT INTO claims (claim_id, signer, capsule, is_active, created_at) "
            "VALUES (?, ?, ?, 1, ?)",
            (cid, "did:key:z6Mktest", json.dumps(capsule), str(created_ts)),
        )

    # A stored FACT: sky is blue
    insert("fact-sky", {
        "subject": "sky", "object": "blue",
        "FACT": "The sky is blue.",
    }, now - 5 * 86400)

    # A stored UNKNOWN about the moon
    insert("unknown-moon", {
        "subject": "moon", "object": "cheese",
        "UNKNOWN": "What if the moon is cheese?",
    }, now - 10 * 86400)

    conn.commit()
    conn.close()
    return tmp_path


@pytest.fixture
def rules_file(tmp_path):
    """A minimal rules JSON file."""
    rules = [
        {"name": "sky-alert", "predicate_spec": {"subject_matches": "sky"}},
        {"name": "moon-alert", "predicate_spec": {"subject_matches": "moon"}},
    ]
    path = tmp_path / "rules.json"
    path.write_text(json.dumps(rules))
    return str(path)


def test_missing_db_returns_error(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("FORGE_HOME", str(tmp_path))  # no forge.db
    rc = echo.main(["sky | blue | The sky is blue", "--face", "FACT"])
    assert rc == 1
    captured = capsys.readouterr()
    assert "database missing" in captured.err.lower() or "not found" in captured.err.lower()


def test_gate_passes_when_no_contradiction(forge_home):
    db_path = str(forge_home / "forge.db")
    hyp = {"subject": "sun", "object": "star", "text": "The sun is a star", "face": "FACT"}
    result = echo.echo(db_path, hyp)
    assert result["gate"]["passed"] is True


def test_gate_passes_when_unknown_agrees(forge_home):
    db_path = str(forge_home / "forge.db")
    # Existing fact: sky is blue. UNKNOWN saying sky is blue does not contradict.
    hyp = {"subject": "sky", "object": "blue", "text": "Maybe the sky is blue", "face": "UNKNOWN"}
    result = echo.echo(db_path, hyp)
    assert result["gate"]["passed"] is True


def test_gate_rejects_unknown_contradicting_fact(forge_home):
    db_path = str(forge_home / "forge.db")
    # Existing fact: sky is blue. UNKNOWN saying sky is green contradicts.
    hyp = {"subject": "sky", "object": "green", "text": "Maybe the sky is green", "face": "UNKNOWN"}
    result = echo.echo(db_path, hyp)
    assert result["gate"]["passed"] is False
    assert "contradict" in result["gate"]["reason"].lower() or "keystone" in result["gate"]["reason"].lower()


def test_gate_ignores_non_gate_faces(forge_home):
    # The gate only applies to UNKNOWN. FACT/OPINION/etc are never rejected.
    db_path = str(forge_home / "forge.db")
    hyp = {"subject": "sky", "object": "green", "text": "The sky is green", "face": "FACT"}
    result = echo.echo(db_path, hyp)
    assert result["gate"]["passed"] is True


def test_rules_preview_fires_matching(forge_home, rules_file):
    db_path = str(forge_home / "forge.db")
    hyp = {"subject": "sky", "object": "blue", "text": "The sky is blue", "face": "FACT"}
    result = echo.echo(db_path, hyp, rules_path=rules_file)
    assert "sky-alert" in result["rules_fired"]
    assert "moon-alert" not in result["rules_fired"]


def test_rules_preview_empty_when_no_file(forge_home):
    db_path = str(forge_home / "forge.db")
    hyp = {"subject": "sky", "object": "blue", "text": "The sky is blue", "face": "FACT"}
    result = echo.echo(db_path, hyp)
    assert result["rules_fired"] == []


def test_shape_reports_resolvable_unknowns(forge_home):
    db_path = str(forge_home / "forge.db")
    # A new claim about the moon would touch the existing UNKNOWN claim.
    hyp = {"subject": "moon", "object": "cheese", "text": "The moon is cheese", "face": "FACT"}
    result = echo.echo(db_path, hyp)
    resolved_subjects = [r["subject"] for r in result["shape"]["resolves"]]
    assert "moon" in resolved_subjects


def test_shape_introduces_new_unknown_count(forge_home):
    db_path = str(forge_home / "forge.db")
    hyp = {"subject": "sky", "object": "green", "text": "The sky might be green", "face": "UNKNOWN"}
    result = echo.echo(db_path, hyp)
    assert result["shape"]["introduces"] == 1


def test_shape_introduces_zero_for_non_unknown(forge_home):
    db_path = str(forge_home / "forge.db")
    hyp = {"subject": "sun", "object": "star", "text": "The sun is a star", "face": "FACT"}
    result = echo.echo(db_path, hyp)
    assert result["shape"]["introduces"] == 0


def test_main_exit_zero_when_gate_passes(forge_home, capsys):
    rc = echo.main(["sun | star | The sun is a star", "--face", "FACT"])
    assert rc == 0
    captured = capsys.readouterr()
    assert "passed" in captured.out.lower() or "pass" in captured.out.lower()


def test_main_exit_one_when_gate_rejects(forge_home, capsys):
    rc = echo.main(["sky | green | The sky might be green", "--face", "UNKNOWN"])
    assert rc == 1
    captured = capsys.readouterr()
    # Either on stdout or stderr, the rejection should be visible
    combined = (captured.out + captured.err).lower()
    assert "reject" in combined or "contradict" in combined or "keystone" in combined


def test_main_usage_error_no_face(forge_home, capsys):
    rc = echo.main(["sky | blue | The sky is blue"])
    assert rc == 2
    captured = capsys.readouterr()
    assert "--face" in captured.err


def test_main_usage_error_bad_face(forge_home, capsys):
    rc = echo.main(["sky | blue | The sky is blue", "--face", "MAGIC"])
    assert rc == 2
    captured = capsys.readouterr()
    assert "face" in captured.err.lower()


def test_read_only_discipline(forge_home):
    """The Echo must not modify the database."""
    db_path = str(forge_home / "forge.db")
    before = os.path.getsize(db_path)
    with open(db_path, "rb") as f:
        before_bytes = f.read()
    hyp = {"subject": "sun", "object": "star", "text": "The sun is a star", "face": "FACT"}
    echo.echo(db_path, hyp)
    with open(db_path, "rb") as f:
        after_bytes = f.read()
    assert before_bytes == after_bytes
