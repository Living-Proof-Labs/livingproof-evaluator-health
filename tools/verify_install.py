# SPDX-License-Identifier: Apache-2.0
"""Build and exercise a clean wheel install outside the checkout; never publish."""

import hashlib
import json
from pathlib import Path
import subprocess
import shutil
import struct
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
    # Exercise mandatory DataEnd through the actual clean-installed wheel too.
    recorded = root / "recording"
    shutil.copytree(fixture, recorded)
    media_path = recorded / "media/media.json"
    media = json.loads(media_path.read_text())
    media["format"] = "livingproof-hallway-media/2.2.0"

    def record(opcode, body):
        return struct.pack("<BQ", opcode, len(body)) + body

    magic = b"\x89MCAP0\r\n"
    for valid in (False, True):
        content = (
            magic
            + record(1, bytes(8))
            + (record(15, bytes(4)) if valid else b"")
            + record(2, bytes(20))
            + magic
        )
        robot = recorded / "media/mcap/robot.mcap"
        robot.write_bytes(content)
        media["trials"][0]["robot_mcap"] = {
            "path": "mcap/robot.mcap",
            "bytes": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
        }
        media_path.write_text(json.dumps(media))
        target = root / ("valid-empty.json" if valid else "malformed.json")
        checked = subprocess.run(
            [
                *cli,
                "--evidence",
                str(recorded / "evidence"),
                "--media",
                str(recorded / "media"),
                "--trial",
                "1",
                "--output",
                str(target),
            ],
            cwd=root,
            capture_output=True,
            text=True,
        )
        if valid:
            assert checked.returncode == 0, checked.stderr
            assert json.loads(target.read_text())["robot"]["status"] == "no robot health telemetry"
        else:
            assert checked.returncode == 2 and "DataEnd" in checked.stderr, checked.stderr
            assert not target.exists()
    hallway = ROOT / "tests/fixtures/historical-hallway"
    for name in ("hallway.json", "hallway-repeat.json"):
        run(
            *cli,
            "--evidence",
            str(hallway),
            "--media",
            str(hallway),
            "--trial",
            "1",
            "--output",
            name,
            cwd=root,
        )
    hallway_data = (root / "hallway.json").read_bytes()
    assert hallway_data == (root / "hallway-repeat.json").read_bytes()
    hallway_result = json.loads(hallway_data)
    assert hallway_result["simulator"]["sample_count"] == 481
    assert hallway_result["simulator"]["minimum_recorded_base_height_by_frame"] == {
        "world": {"height_m": 0.70652, "time_ns": "2900000000"}
    }
    # Producer route through-places remain null until visited. Synthetic variant
    # of the retained route fixture, with both hash bindings updated explicitly.
    unvisited = root / "unvisited-route"
    shutil.copytree(fixture, unvisited)
    observation_path = unvisited / "evidence/trials/trial-01.json"
    observation = json.loads(observation_path.read_text())
    observation.update(end="time_limit", exit_time=None)
    observation["places_entered"]["corner"] = None
    observation_path.write_text(json.dumps(observation))
    observation_hash = hashlib.sha256(observation_path.read_bytes()).hexdigest()
    for relative in ("evidence/manifest.json", "media/media.json"):
        target = unvisited / relative
        doc = json.loads(target.read_text())
        if relative.startswith("evidence"):
            doc["trials"]["results"][0]["sha256"] = observation_hash
        else:
            doc["trials"][0]["observation_sha256"] = observation_hash
        target.write_text(json.dumps(doc))
    run(
        *cli,
        "--evidence",
        str(unvisited / "evidence"),
        "--media",
        str(unvisited / "media"),
        "--trial",
        "1",
        "--output",
        "unvisited-health.json",
        cwd=root,
    )
    unvisited_result = json.loads((root / "unvisited-health.json").read_text())
    assert unvisited_result["trial"]["observation_sha256"] == observation_hash
    assert unvisited_result["simulator"]["sample_count"] == 614
    summary = {
        "installed": installed,
        "health_version": result["health_version"],
        "wheel_sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
        "result_sha256": hashlib.sha256(data).hexdigest(),
        "sample_count": 614,
        "minimum_height_m": 0.74637,
        "time_ns": "4440000000",
        "repeat_identical": True,
        "missing_data_end_refused": True,
        "valid_empty_robot_verified": True,
        "historical_hallway_sample_count": 481,
        "historical_hallway_repeat_identical": True,
        "unvisited_route_place_verified": True,
        "hosted_stock_baseline_replayed": False,
        "scope": "candidate clean install; not a released artifact",
    }
    (ROOT / "artifacts").mkdir(exist_ok=True)
    (ROOT / "artifacts/install-evidence.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, sort_keys=True))
