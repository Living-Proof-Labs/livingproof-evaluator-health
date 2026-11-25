# SPDX-License-Identifier: Apache-2.0
"""Build and exercise a clean wheel install outside the checkout; never publish."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
WHEEL = ROOT / "vendor/livingproof_health-1.0.5-py3-none-any.whl"
assert hashlib.sha256(WHEEL.read_bytes()).hexdigest() == (
    "d1ce13c2b68e31855ac81a83b478f174182bf0ab4894d917b7e0dd406ba2857c"
)


def run(*args, cwd=ROOT):
    return subprocess.check_output(args, cwd=cwd, text=True).strip()


with tempfile.TemporaryDirectory(prefix="health-install-") as directory:
    root = Path(directory)
    run("uv", "build", "--wheel", "--out-dir", str(root / "dist"))
    run("uv", "venv", "--python", sys.executable, str(root / "env"))
    python = str(root / "env/bin/python")
    wheel = next((root / "dist").glob("*.whl"))
    run("uv", "pip", "install", "--python", python, str(wheel), str(WHEEL), cwd=root)
    cli = (python, "-m", "livingproof_evaluator_health")
    installed = run(*cli, "--version", cwd=root)
    assert installed == run(sys.executable, "-m", "livingproof_evaluator_health", "--version")
    assert "--evidence" in run(*cli, "--help", cwd=root)
    fixture = ROOT / "tests/fixtures/original-recording"
    for name in ("health.json", "repeat.json"):
        run(
            *cli,
            "--evidence",
            str(fixture / "evidence"),
            "--media",
            str(fixture / "media"),
            "--trial",
            "1",
            "--output",
            name,
            cwd=root,
        )
    data = (root / "health.json").read_bytes()
    assert data == (root / "repeat.json").read_bytes()
    result = json.loads(data)
    assert result["simulator"]["sample_count"] == 614
    assert result["simulator"]["minimum_recorded_base_height_by_frame"] == {
        "world": {"height_m": 0.74637, "time_ns": "4440000000"}
    }
    summary = {
        "installed": installed,
        "health_version": result["health_version"],
        "wheel_sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
        "result_sha256": hashlib.sha256(data).hexdigest(),
        "sample_count": 614,
        "minimum_height_m": 0.74637,
        "time_ns": "4440000000",
        "repeat_identical": True,
        "scope": "candidate clean install; not a released artifact",
    }
    (ROOT / "artifacts").mkdir(exist_ok=True)
    (ROOT / "artifacts/install-evidence.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, sort_keys=True))
