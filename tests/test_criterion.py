# SPDX-License-Identifier: Apache-2.0
"""Pinned real source metadata with explicit synthetic samples and mutations."""

import copy
import hashlib
import json
from pathlib import Path
import shutil

import pytest

from livingproof_evaluator_health import criterion

FIXTURE = Path(__file__).parent / "fixtures/height-criterion"


def sample(height, time, frame="world"):
    pose = None if height is None else {"frame_id": frame, "unit": "m", "position": {"z": height}}
    return {"time_ns": str(time), "items": {"base_pose": pose}}


@pytest.fixture
def bound(tmp_path):
    root = tmp_path / "evidence"
    shutil.copytree(FIXTURE, root)
    m = json.loads((root / "manifest.json").read_bytes())
    report = {
        "evidence_manifest_sha256": hashlib.sha256(
            (root / "manifest.json").read_bytes()
        ).hexdigest(),
        "run_manifest_sha256": hashlib.sha256(
            (root / "run-manifest.json").read_bytes()
        ).hexdigest(),
        "trial": {"run_id": m["run_id"], "configuration": "stock", "index": 1},
        "simulator": {"snapshots": [sample(0.75, 0), sample(0.74, 1000000000)]},
    }
    return root / "manifest.json", report


@pytest.mark.parametrize(
    "height,word", [(0.49, "below"), (0.5, "at or above"), (0.51, "at or above")]
)
def test_boundaries_from_actual_pinned_configuration(bound, height, word):
    path, report = bound
    report["simulator"]["snapshots"] = [sample(0.75, 0), sample(height, 1000000000)]
    before = copy.deepcopy(report)
    summary, detail = criterion.text_for(path, report)
    assert f"{word} 0.5 m" in summary
    assert "2 matching samples; 0 unavailable from 0 to 1 s" in detail
    assert criterion.PARAMETERS_SHA in detail and criterion.CONFIG_SHA in detail
    assert report == before


def test_interior_dip_and_missing_cannot_erase_violation(bound):
    path, report = bound
    report["simulator"]["snapshots"] = [
        sample(0.75, 0),
        sample(0.4, 1),
        sample(None, 2),
        sample(0.75, 3),
    ]
    summary, detail = criterion.text_for(path, report)
    assert "below 0.5 m" in summary
    assert "3 matching samples; 1 unavailable" in detail


@pytest.mark.parametrize(
    "samples",
    [
        [],
        [sample(0.8, 0)],
        [sample(None, 0), sample(0.8, 1)],
        [sample(0.8, 0, "other"), sample(0.8, 1, "other")],
    ],
)
def test_insufficient_matching_observations(bound, samples):
    path, report = bound
    report["simulator"]["snapshots"] = samples
    assert "unevaluated against 0.5 m" in criterion.text_for(path, report)[0]


def test_verified_absence_is_distinct_from_missing_source(bound, monkeypatch):
    params = criterion.packaged("parameters.json", criterion.PARAMETERS_SHA)
    profile = criterion.packaged("stock.json", criterion.CONFIG_SHA)
    params["checks"] = [c for c in params["checks"] if c["measure"] != "min-base-height"]
    assert criterion.rule(params, profile) is None
    with pytest.raises(ValueError):
        criterion.rule({}, profile)
    path, report = bound
    monkeypatch.setattr(criterion, "resolve", lambda *a: None)
    assert "not applicable" in criterion.text_for(path, report)[0]


@pytest.mark.parametrize(
    "fault",
    [
        "parameter-sha",
        "spec-commit",
        "config",
        "resolved",
        "run",
        "duplicate-config",
        "profile-type",
        "missing",
    ],
)
def test_unverified_never_means_absent(bound, fault):
    path, report = bound
    m = json.loads(path.read_bytes())
    runpath = path.parent / "run-manifest.json"
    r = json.loads(runpath.read_bytes())
    if fault == "parameter-sha":
        m["sources"]["parameters"]["sha256"] = "0" * 64
    if fault == "spec-commit":
        m["lock"]["content"]["releases"]["specs"]["commit"] = "0" * 40
    if fault == "config":
        m["configuration"]["profile"]["locomotion"]["fall_base_height"]["value"] = 0.9
    if fault == "profile-type":
        m["configuration"]["profile"]["settings"]["deploy"]["arm_waist_target"][0] = False
    if fault == "resolved":
        r["parameters"]["fall_height"] = 0.9
    if fault == "run":
        r["run_id"] = "other"
    if fault == "duplicate-config":
        m["lock"]["content"]["configurations"].append(m["lock"]["content"]["configurations"][0])
    if fault == "missing":
        m.pop("sources")
    path.write_text(json.dumps(m))
    runpath.write_text(json.dumps(r))
    report["evidence_manifest_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    report["run_manifest_sha256"] = hashlib.sha256(runpath.read_bytes()).hexdigest()
    summary, _ = criterion.text_for(path, report)
    assert "unevaluated" in summary and "not applicable" not in summary


def test_packaged_bytes_require_exact_digest():
    with pytest.raises(ValueError, match="digest mismatch"):
        criterion.packaged("parameters.json", "0" * 64)


def test_genuine_g1_descriptor_cli_preserves_replay(tmp_path):
    from test_advisory import parse, run_advisory, schema_errors
    from test_cli import run_cli

    before = {str(p): p.read_bytes() for p in FIXTURE.rglob("*") if p.is_file()}
    result = tmp_path / "advisory/result.json"
    completed = run_advisory(tmp_path, FIXTURE / "manifest.json", result, FIXTURE / "mcap")
    assert completed.returncode == 0, completed.stderr
    doc = parse(result)
    assert schema_errors(doc) == []
    assert "at or above 0.5 m" in doc["advisory"]["summary"]
    assert "0.74814 m at 8.46 s" in doc["advisory"]["details"]
    assert "574 matching samples; 0 unavailable from 0 to 11.46 s" in doc["advisory"]["details"]
    assert "No robot health telemetry" in doc["advisory"]["details"]
    legacy = tmp_path / "per-trial.json"
    completed = run_cli(
        tmp_path,
        "--evidence",
        str(FIXTURE),
        "--media",
        str(FIXTURE / "mcap"),
        "--trial",
        "1",
        "--output",
        str(legacy),
    )
    assert completed.returncode == 0, completed.stderr
    assert parse(result.parent / "health.json")["trials"][0] == parse(legacy)
    assert before == {str(p): p.read_bytes() for p in FIXTURE.rglob("*") if p.is_file()}


def test_criterion_release_labels_preserve_machine_provenance(bound):
    path, report = bound
    before = path.read_bytes()
    text = criterion.text_for(path, report)[1]
    assert "robot-capability-specs@v2.3.0" in text
    assert "livingproof-unitree-g1@v2.3.34" in text
    assert criterion.SPEC_COMMIT not in text and criterion.ROBOT_COMMIT not in text
    assert path.read_bytes() == before


def test_unknown_release_label_uses_actual_file_digest():
    commit, digest = "a" * 40, "b" * 64
    text = criterion.source_label("unreleased-source", commit, digest)
    assert text == f"unreleased-source source file SHA-256 {digest}"
    assert commit not in text
