# SPDX-License-Identifier: Apache-2.0
"""Authentic retained metadata, explicitly synthetic boundary samples."""

import copy
import hashlib
import json
from pathlib import Path
import shutil

import pytest

from livingproof_evaluator_health import criterion
from test_criterion import sample


@pytest.fixture
def go1(tmp_path):
    root = tmp_path / "evidence"
    shutil.copytree(Path(__file__).parent / "fixtures/go1-criterion", root)
    manifest = json.loads((root / "manifest.json").read_bytes())
    report = {
        "evidence_manifest_sha256": hashlib.sha256(
            (root / "manifest.json").read_bytes()
        ).hexdigest(),
        "run_manifest_sha256": hashlib.sha256(
            (root / "run-manifest.json").read_bytes()
        ).hexdigest(),
        "trial": {"run_id": manifest["run_id"], "configuration": "playground", "index": 1},
        "simulator": {"snapshots": [sample(0.278, 0), sample(0.28, 1)]},
    }
    return root / "manifest.json", report


@pytest.mark.parametrize(
    "height,word", [(0.179, "below"), (0.18, "at or above"), (0.181, "at or above")]
)
def test_go1_strict_configured_boundary(go1, height, word):
    path, report = go1
    report["simulator"]["snapshots"] = [sample(0.278, 0), sample(height, 1), sample(0.278, 2)]
    before = copy.deepcopy(report)
    result = criterion.text_for(path, report)
    assert f"{word} 0.18 m" in result[0]
    assert "playground 1.0.0" in result[1]
    assert "livingproof-unitree-go1@v2.3.5" in result[1]
    assert "fe48f8bda30aa0a65bd01b06107fc76874195f35" not in result[1]
    assert "0.5 m" not in result[1]
    assert criterion.text_for(path, report) == result
    assert before == report


@pytest.mark.parametrize(
    "fault", ["robot", "runner", "profile", "resolved", "g1-runner", "missing"]
)
def test_unknown_go1_provenance_is_not_absent(go1, fault):
    path, report = go1
    manifest = json.loads(path.read_bytes())
    runpath = path.parent / "run-manifest.json"
    run = json.loads(runpath.read_bytes())
    if fault == "robot":
        run["robot"]["commit"] = "a" * 40
    elif fault in {"runner", "g1-runner"}:
        value = "a" * 40 if fault == "runner" else criterion.SOURCES[0][2]
        run["simulator"]["adapter_commit"] = value
        manifest["lock"]["content"]["releases"]["runner"]["commit"] = value
    elif fault == "profile":
        manifest["configuration"]["profile"]["locomotion"]["fall_base_height"]["value"] = 0.5
    elif fault == "resolved":
        run["parameters"]["fall_height"] = 0.5
    else:
        del manifest["lock"]
    path.write_text(json.dumps(manifest))
    runpath.write_text(json.dumps(run))
    report["evidence_manifest_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    report["run_manifest_sha256"] = hashlib.sha256(runpath.read_bytes()).hexdigest()
    summary, detail = criterion.text_for(path, report)
    assert "unevaluated" in summary and "not establish an absent criterion" in detail


def test_go1_missing_samples_is_unevaluated(go1):
    path, report = go1
    report["simulator"]["snapshots"] = []
    assert "unevaluated against 0.18 m" in criterion.text_for(path, report)[0]
