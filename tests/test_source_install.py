# SPDX-License-Identifier: Apache-2.0
"""Run the documented released-source install verbatim, not a wheel approximation."""

import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def test_documented_released_source_install_and_replay(tmp_path):
    guide = (ROOT / "docs/guide.md").read_text()
    example = guide.split("<!-- released-source-install:start -->", 1)[1].split(
        "<!-- released-source-install:end -->", 1
    )[0]
    script = example.strip().removeprefix("```sh\n").removesuffix("```")
    fixture = ROOT / "tests/fixtures/original-recording"
    env = {
        **os.environ,
        "HEALTH_EVIDENCE": str(fixture / "evidence"),
        "HEALTH_MEDIA": str(fixture / "media"),
    }
    # These variables select only the caller's input directories. The release
    # URL, venv, installation and CLI commands come unchanged from the manual.
    result = subprocess.run(
        ["bash", "-eu", "-c", script],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "livingproof-evaluator-health 1.1.0" in result.stdout.splitlines()
    data = (tmp_path / "health.json").read_bytes()
    report = json.loads(data)
    assert report["evaluator_version"] == "1.1.0"
    assert report["health_version"] == "1.0.5"
    assert report["simulator"]["sample_count"] == 614
    assert report["simulator"]["minimum_recorded_base_height_by_frame"] == {
        "world": {"height_m": 0.74637, "time_ns": "4440000000"}
    }
    assert report["robot"]["status"] == "robot stream not declared by this media version"
    repeat = subprocess.run(
        [
            str(tmp_path / ".health-env/bin/python"),
            "-m",
            "livingproof_evaluator_health",
            "--evidence",
            env["HEALTH_EVIDENCE"],
            "--media",
            env["HEALTH_MEDIA"],
            "--trial",
            "1",
            "--output",
            "repeat.json",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert repeat.returncode == 0, repeat.stderr
    assert data == (tmp_path / "repeat.json").read_bytes()
