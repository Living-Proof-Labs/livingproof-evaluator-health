# SPDX-License-Identifier: Apache-2.0
"""Offline, exact-source criterion resolution. Never infer a rule from its name."""

import hashlib
from importlib.resources import files
import json
import math

from livingproof_health.assessment import assess_base_height
from livingproof_health.snapshots import Replay, snapshot_from_wire

from .evaluate import document

SPEC_COMMIT = "57317e617014a6df97bb7fba9d92a890af8d42e5"
PARAMETERS_PATH = "specs/scenarios/walk-hallway/parameters.json"
PARAMETERS_SHA = "9226aa6bc0e577863bdc210514e7e7c3a7edc32f49c4f7b46aa7249837f08b3d"
CONFIG_SHA = "8baf584eb025fa4408aad20a81521b73bc068a3a7e613dfeeb8f03d24eb02b5e"
ROBOT_COMMIT = "d554c8243a12849dc7fe8acc1921bb3d4e5239a7"


# Each supported combination is reviewed as a whole; do not mix profile/runner pins.
SOURCES = (
    (
        "livingproof-unitree-g1",
        ROBOT_COMMIT,
        "727d8706598e8ac706324ca87edd0973fdbb3485",
        "stock.json",
        CONFIG_SHA,
    ),
    (
        "livingproof-unitree-go1",
        "fe48f8bda30aa0a65bd01b06107fc76874195f35",
        "988a57bdb54654aac57aa4de0574d62914074fd0",
        "playground.json",
        "07bcbab38570ddb1c76c8508916298f2dc633be1543a78af7971bec338d6f930",
    ),
)


def source_for(run):
    matches = [
        s
        for s in SOURCES
        if run["robot"]["repo"] == "https://github.com/Living-Proof-Labs/" + s[0]
        and run["robot"]["commit"] == s[1]
        and run["simulator"]["adapter_commit"] == s[2]
    ]
    require(len(matches) == 1)
    return matches[0]


def packaged(name, expected):
    raw = files("livingproof_evaluator_health").joinpath("criteria", name).read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError("Packaged criterion source digest mismatch")
    return json.loads(raw)


def require(value):
    if not value:
        raise ValueError("Criterion source or configuration binding is unavailable or inconsistent")


def rule(parameters, profile):
    """Interpret only an explicit supported measurement/limit declaration."""
    checks = parameters.get("checks")
    require(
        isinstance(checks, list)
        and all(isinstance(c, dict) and isinstance(c.get("measure"), str) for c in checks)
    )
    matches = [c for c in checks if isinstance(c, dict) and c.get("measure") == "min-base-height"]
    if not matches:
        return None
    require(len(matches) == 1 and matches[0].get("fail_when") == "less-than-limit")
    limit = parameters["limits"][matches[0]["limit"]]
    require(limit["unit"] == "m" and limit["expression"] == {"input": "fall_base_height"})
    source = parameters["inputs"]["fall_base_height"]
    require(
        source["source"] == "configuration-profile"
        and source["unit"] == "m"
        and source["path"] == "locomotion.fall_base_height"
    )
    quantity = profile["locomotion"]["fall_base_height"]
    value = quantity["value"]
    require(quantity["unit"] == "m" and type(value) in (int, float) and math.isfinite(value))
    return value


def resolve(manifest_path, report):
    manifest, digest = document(manifest_path)
    require(digest == report["evidence_manifest_sha256"])
    lock = manifest["lock"]["content"]
    specs = lock["releases"]["specs"]
    require(
        specs["repository"] == "Living-Proof-Labs/robot-capability-specs"
        and specs["commit"] == SPEC_COMMIT
        and specs["tag"] == "v2.3.0"
    )
    require(
        manifest["sources"]["parameters"] == {"path": PARAMETERS_PATH, "sha256": PARAMETERS_SHA}
    )
    require(
        lock["sources"]["parameters"] == manifest["sources"]["parameters"]
        and specs["files"][PARAMETERS_PATH] == PARAMETERS_SHA
    )
    parameters = packaged("parameters.json", PARAMETERS_SHA)
    scenario = parameters["scenario"]
    require(lock["scenario"] == f"{scenario['id']}@{scenario['revision']}")
    run, run_hash = document(manifest_path.parent / "run-manifest.json")
    require(run_hash == report.get("run_manifest_sha256"))
    trial = report["trial"]
    require(
        manifest["run_id"] == run["run_id"] == trial["run_id"]
        and run["scenario"] == lock["scenario"]
        and run["specification"] == {"tag": specs["tag"], "commit": SPEC_COMMIT}
    )
    _, robot_commit, runner_commit, profile_file, config_sha = source_for(run)
    runner = lock["releases"]["runner"]
    require(
        runner["repository"] == "Living-Proof-Labs/livingproof-sim-mujoco"
        and runner["commit"] == runner_commit
        and run["simulator"]["adapter"] == "livingproof-sim-mujoco"
        and run["simulator"]["engine"] == "mujoco"
        and run["simulator"]["adapter_commit"] == runner["commit"]
    )
    selected = manifest["configuration"]
    matches = [c for c in lock["configurations"] if c.get("name") == trial["configuration"]]
    require(len(matches) == 1)
    pin = matches[0]
    require(pin["path"] == "configurations/" + profile_file and pin["sha256"] == config_sha)
    profile = packaged(profile_file, config_sha)
    require(
        run["robot"]["commit"] == robot_commit
        and manifest["robot"]["id"] == profile["robot"] == run["robot"]["id"]
    )
    for key in ("name", "version"):
        require(selected[key] == profile[key] == pin[key] == run["configuration"][key])
    require(
        selected["sha256"] == config_sha == run["configuration"]["sha256"]
        and json.dumps(selected["profile"], sort_keys=True, allow_nan=False)
        == json.dumps(profile, sort_keys=True, allow_nan=False)
    )
    minimum = rule(parameters, profile)
    if minimum is not None:
        resolved = run["parameters"]["fall_height"]
        require(type(resolved) in (int, float) and math.isfinite(resolved) and resolved == minimum)
    return minimum


def text_for(manifest_path, report):
    """Presentation only; never modify the original recording/result document."""
    try:
        minimum = resolve(manifest_path, report)
    except (KeyError, TypeError, ValueError, OSError):
        return (
            "Recorded base-height check unevaluated: criterion provenance unavailable.",
            "Recorded base-height check unevaluated: the exact scenario/configuration source "
            "could not be verified offline. This does not establish an absent criterion.",
        )
    if minimum is None:
        return (
            "Recorded base-height check not applicable: scenario declares no such rule.",
            "The verified scenario declares no sampled base-height criterion.",
        )
    samples = report["simulator"].get("snapshots", [])
    replay = Replay(snapshot_from_wire(s) for s in samples)
    assessed = assess_base_height(replay, minimum_m=minimum, frame_id="world")
    state = {
        "PASS": "at or above",
        "FAIL": "below",
        "INSUFFICIENT_EVIDENCE": "unevaluated against",
    }[assessed["status"]]
    coverage = (
        f"{assessed['sample_count'] - assessed['unavailable_count']} matching samples; "
        f"{assessed['unavailable_count']} unavailable"
    )
    interval = (
        f" from {min(int(s['time_ns']) for s in samples) / 1e9:g} to {max(int(s['time_ns']) for s in samples) / 1e9:g} s"
        if samples
        else ""
    )
    summary = f"Recorded base height {state} {minimum:g} m (world; sampled only)."
    run, _ = document(manifest_path.parent / "run-manifest.json")
    _, robot_commit, _, profile_file, config_sha = source_for(run)
    profile = packaged(profile_file, config_sha)
    details = (
        f"{summary} Coverage: {coverage}{interval}. "
        f"Criterion: robot-capability-specs@{SPEC_COMMIT}, {PARAMETERS_PATH}, SHA256 {PARAMETERS_SHA}; "
        f"configuration {profile['name']} {profile['version']} at {robot_commit}, SHA256 {config_sha}. "
        "Equality is not below. Orientation and whole-trial uprightness are not evaluated."
    )
    return summary, details
