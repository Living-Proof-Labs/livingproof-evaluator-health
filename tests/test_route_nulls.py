# SPDX-License-Identifier: Apache-2.0
"""Synthetic route variants; never rewrite the retained original fixture."""

import hashlib
import json
import shutil

import pytest

from test_evaluate import FIXTURE, edit, invoke


def route_variant(tmp_path, entered):
    root = tmp_path / "route-variant"
    shutil.copytree(FIXTURE, root)
    observation = root / "evidence/trials/trial-01.json"

    def change(doc):
        doc["end"] = "time_limit"
        doc["exit_time"] = None
        doc["left_world"] = None
        doc["places_entered"]["corner"] = entered
        # The producer also writes null when no wall geometry is alongside it.
        doc["trace"]["samples"][0][5] = None

    edit(observation, change)
    digest = hashlib.sha256(observation.read_bytes()).hexdigest()
    edit(root / "evidence/manifest.json", lambda d: d["trials"]["results"][0].update(sha256=digest))
    edit(root / "media/media.json", lambda d: d["trials"][0].update(observation_sha256=digest))
    return root, digest


@pytest.mark.parametrize("entered", [None, 0, 3.88])
def test_installed_cli_accepts_unvisited_or_timestamped_place(tmp_path, entered):
    root, digest = route_variant(tmp_path, entered)
    observation = root / "evidence/trials/trial-01.json"
    before = observation.read_bytes()
    result = invoke(tmp_path, root)
    assert result.returncode == 0, result.stderr
    report = json.loads((tmp_path / "health.json").read_text())
    assert report["trial"]["observation_sha256"] == digest
    assert report["simulator"]["sample_count"] == 614
    assert report["simulator"]["minimum_recorded_base_height_by_frame"] == {
        "world": {"height_m": 0.74637, "time_ns": "4440000000"}
    }
    assert observation.read_bytes() == before


@pytest.mark.parametrize("entered", [-1, True, "3.88", [], {}, float("nan"), float("inf")])
def test_installed_cli_rejects_malformed_place_time(tmp_path, entered):
    root, _ = route_variant(tmp_path, entered)
    result = invoke(tmp_path, root)
    assert result.returncode == 2, result.stderr
    assert not (tmp_path / "health.json").exists()


def test_unvisited_place_does_not_relax_hash_binding(tmp_path):
    root, _ = route_variant(tmp_path, None)
    edit(root / "media/media.json", lambda d: d["trials"][0].update(observation_sha256="0" * 64))
    result = invoke(tmp_path, root)
    assert result.returncode == 2 and "observation mismatch" in result.stderr
    assert not (tmp_path / "health.json").exists()
