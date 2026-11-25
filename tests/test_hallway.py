# SPDX-License-Identifier: Apache-2.0
"""Historical retained bytes + explicitly synthetic manifest wrappers, not baseline #27."""

import hashlib
import json
from pathlib import Path
import shutil

from mcap.writer import Writer
import pytest

from test_cli import run_cli
from test_evaluate import edit

FIXTURE = Path(__file__).parent / "fixtures/historical-hallway"


@pytest.fixture
def hallway(tmp_path):
    root = tmp_path / "hallway"
    shutil.copytree(FIXTURE, root)
    return root


def invoke(tmp_path, hallway, name="health.json"):
    return run_cli(
        tmp_path,
        "--evidence",
        str(hallway),
        "--media",
        str(hallway),
        "--trial",
        "1",
        "--output",
        str(tmp_path / name),
    )


def relink(hallway):
    digest = hashlib.sha256((hallway / "observation-trial-01.json").read_bytes()).hexdigest()
    edit(hallway / "manifest.json", lambda d: d["trials"]["results"][0].update(sha256=digest))
    edit(hallway / "media.json", lambda d: d["trials"][0].update(observation_sha256=digest))


def test_historical_hallway_cli_preserves_bytes_and_repeats(tmp_path, hallway):
    original = {p.name: p.read_bytes() for p in hallway.iterdir() if p.is_file()}
    for output in ("health.json", "again.json"):
        result = invoke(tmp_path, hallway, output)
        assert result.returncode == 0, result.stderr
    assert (tmp_path / "health.json").read_bytes() == (tmp_path / "again.json").read_bytes()
    result = json.loads((tmp_path / "health.json").read_text())
    assert result["trial"]["configuration"] == "playground"
    assert result["trial"]["index"] == 1
    assert result["trial"]["run_id"] == "test-wrapper-historical-g1-playground"
    assert (
        result["trial"]["observation_sha256"]
        == hashlib.sha256(original["observation-trial-01.json"]).hexdigest()
    )
    assert (
        result["simulator"]["source"]["sha256"]
        == hashlib.sha256(original["trial-01.mcap"]).hexdigest()
    )
    assert result["simulator"]["sample_count"] == 481
    assert result["simulator"]["minimum_recorded_base_height_by_frame"] == {
        "world": {"height_m": 0.70652, "time_ns": "2900000000"}
    }
    assert original == {p.name: p.read_bytes() for p in hallway.iterdir() if p.is_file()}


def test_hallway_valid_empty_robot_remains_separate(tmp_path, hallway):
    robot = hallway / "robot.mcap"
    with robot.open("wb") as stream:
        writer = Writer(stream)
        writer.start()
        writer.finish()

    def update(doc):
        doc["format"] = "livingproof-hallway-media/2.2.0"
        doc["trials"][0]["robot_mcap"] = {
            "path": robot.name,
            "bytes": robot.stat().st_size,
            "sha256": hashlib.sha256(robot.read_bytes()).hexdigest(),
        }

    edit(hallway / "media.json", update)
    result = invoke(tmp_path, hallway)
    assert result.returncode == 0, result.stderr
    report = json.loads((tmp_path / "health.json").read_text())
    assert report["robot"]["status"] == "no robot health telemetry"
    assert "snapshots" not in report["robot"]
    assert report["simulator"]["sample_count"] == 481


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d.update(format="livingproof-hallway-observation/3.0.0"),
        lambda d: d.update(format="livingproof-route-observation/0.1.0"),
        lambda d: d.pop("left_hallway"),
        lambda d: d.update(max_abs_lateral="invalid"),
        lambda d: d.update(duration_s=True),
        lambda d: d["trace"].update(columns=["x", "y"]),
        lambda d: d["trace"]["samples"][0].pop(),
        lambda d: d["trace"]["samples"][0].__setitem__(3, "not a number"),
        lambda d: d["trace"]["samples"][0].__setitem__(0, -1),
        lambda d: d.update(wall_contacts=[{"wall": "left"}]),
        lambda d: d.update(trace=None),
    ],
)
def test_hash_matched_malformed_hallway_is_rejected(tmp_path, hallway, mutate):
    edit(hallway / "observation-trial-01.json", mutate)
    relink(hallway)  # Reject the shape even when the new hashes agree.
    result = invoke(tmp_path, hallway)
    assert result.returncode == 2, result.stderr
    assert not (tmp_path / "health.json").exists()


@pytest.mark.parametrize(
    "file,mutate",
    [
        ("media.json", lambda d: d.update(run_id="wrong")),
        ("media.json", lambda d: d.update(configuration="stock")),
        ("media.json", lambda d: d["trials"][0].update(index=2)),
        ("media.json", lambda d: d["trials"][0].update(observation_sha256="0" * 64)),
        ("media.json", lambda d: d["trials"][0]["mcap"].update(sha256="0" * 64)),
        ("manifest.json", lambda d: d["trials"]["results"][0].update(sha256="0" * 64)),
        (
            "manifest.json",
            lambda d: d["trials"]["results"].append(d["trials"]["results"][0].copy()),
        ),
        ("run-manifest.json", lambda d: d.update(run_id="wrong")),
        ("run-manifest.json", lambda d: d["configuration"].update(name="stock")),
    ],
)
def test_hallway_trial_and_hash_binding_refusals(tmp_path, hallway, file, mutate):
    edit(hallway / file, mutate)
    result = invoke(tmp_path, hallway)
    assert result.returncode == 2, result.stderr
    assert not (tmp_path / "health.json").exists()


def test_upstream_historical_bytes_unchanged():
    provenance = json.loads((FIXTURE / "PROVENANCE.json").read_text())
    for name, digest in provenance["sha256"].items():
        assert hashlib.sha256((FIXTURE / name).read_bytes()).hexdigest() == digest


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d.update(format="livingproof-hallway-observation/2.0.0"),
        lambda d: d.pop("places"),
        lambda d: d["trace"]["samples"][0].__setitem__(1, True),
    ],
)
def test_route_adapter_stays_separate_and_strict(tmp_path, mutate):
    from test_evaluate import FIXTURE as route_fixture

    root = tmp_path / "route"
    shutil.copytree(route_fixture, root)
    path = root / "evidence/trials/trial-01.json"
    edit(path, mutate)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    edit(root / "evidence/manifest.json", lambda d: d["trials"]["results"][0].update(sha256=digest))
    edit(root / "media/media.json", lambda d: d["trials"][0].update(observation_sha256=digest))
    result = run_cli(
        tmp_path,
        "--evidence",
        str(root / "evidence"),
        "--media",
        str(root / "media"),
        "--trial",
        "1",
        "--output",
        str(tmp_path / "health.json"),
    )
    assert result.returncode == 2, result.stderr
    assert not (tmp_path / "health.json").exists()
