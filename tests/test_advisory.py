# SPDX-License-Identifier: Apache-2.0
"""Advisory CLI: one contract result for every trial, citing health.json."""

import copy
import hashlib
import json
from pathlib import Path
import re
import shutil

import pytest

from test_cli import run_cli
from test_evaluate import edit
from test_implementation_descriptor import descriptor, errors

FIXTURES = Path(__file__).parent / "fixtures"
ORIGINAL = FIXTURES / "original-recording"
PURPOSE = (
    "Recorded simulator posture and base height, separate from robot telemetry. "
    "Optional advisory observations; no effect on grade, Scenario or Run Integrity."
)
PLACEHOLDER = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")
HALLWAYS = [
    (
        ORIGINAL / "evidence" / "manifest.json",
        ORIGINAL / "media",
        (
            "Simulator: 614 recorded samples. "
            "Minimum recorded base height (world): 0.74637 m at 4.44 s. "
            "Robot health assessment unavailable: "
            "robot stream not declared by this media version."
        ),
    ),
    (
        FIXTURES / "historical-hallway" / "manifest.json",
        FIXTURES / "historical-hallway",
        (
            "Simulator: 481 recorded samples. "
            "Minimum recorded base height (world): 0.70652 m at 2.9 s. "
            "Robot health assessment unavailable: "
            "robot stream not declared by this media version."
        ),
    ),
]


def pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise AssertionError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def parse(path):
    return json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=pairs,
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
    )


def fill(text, values):
    def replace(match):
        name = match.group(1)
        if name not in values:
            raise AssertionError(f"placeholder {{{name}}} is not a provided input")
        return values[name]

    return PLACEHOLDER.sub(replace, text)


def expand(arguments, values):
    expanded = []
    for item in arguments:
        if isinstance(item, str):
            expanded.append(fill(item, values))
            continue
        if item["if"] not in values:
            continue
        expanded.extend(fill(part, values) for part in item["then"])
    return expanded


def run_advisory(tmp_path, manifest, result, media=None, extra=()):
    values = {"evidence_manifest": str(manifest), "result": str(result)}
    if media is not None:
        values["media_dir"] = str(media)
    argv = [*expand(descriptor()["arguments"], values), *extra]
    return run_cli(tmp_path, *argv)


def schema_errors(document):
    found = errors("evaluator-result.schema.json", document)
    return [f"{'/'.join(map(str, error.path))}: {error.message}" for error in found]


def assert_unique_trials(document):
    indexes = [trial["index"] for trial in document["advisory"]["trials"]]
    assert indexes
    assert len(indexes) == len(set(indexes))


def test_advisory_result_matches_v1_10_schema(tmp_path):
    for manifest, media, _expected in HALLWAYS:
        result = tmp_path / manifest.parent.name / "result.json"
        completed = run_advisory(tmp_path, manifest, result, media)
        assert completed.returncode == 0, completed.stderr
        document = parse(result)
        assert schema_errors(document) == []
        assert_unique_trials(document)
        assert document["format"] == "livingproof-evaluator-result/1.3.0"
        assert document["evaluator"]["id"] == "livingproof-health"
        assert document["evaluator"]["kind"] == "advisory"
        assert document["descriptor"]["tier"] == "observation"
        health = parse(result.parent / "health.json")
        assert [trial["index"] for trial in document["advisory"]["trials"]] == [
            report["trial"]["index"] for report in health["trials"]
        ]


def test_card_text_matches_the_action(tmp_path):
    for manifest, media, expected in HALLWAYS:
        result = tmp_path / manifest.parent.name / "card.json"
        completed = run_advisory(tmp_path, manifest, result, media)
        assert completed.returncode == 0, completed.stderr
        document = parse(result)
        assert document["descriptor"]["title"] == "Health"
        assert document["evaluator"]["display_name"] == "Health"
        assert document["descriptor"]["purpose"] == PURPOSE
        assert document["descriptor"]["version"] == document["evaluator"]["version"]
        assert document["advisory"]["details"] == expected
        assert expected in document["advisory"]["summary"]
        assert "Source " not in document["advisory"]["details"]
        assert "provenance" not in document["advisory"]["details"]


def test_details_file_sha256_is_the_health_json_digest(tmp_path):
    result = tmp_path / "result.json"
    manifest = ORIGINAL / "evidence" / "manifest.json"
    completed = run_advisory(tmp_path, manifest, result, ORIGINAL / "media")
    assert completed.returncode == 0, completed.stderr
    document = parse(result)
    health = result.parent / "health.json"
    assert document["advisory"]["details_file"] == {
        "uri": "health.json",
        "sha256": hashlib.sha256(health.read_bytes()).hexdigest(),
    }
    again = tmp_path / "again" / "result.json"
    repeated = run_advisory(tmp_path, manifest, again, ORIGINAL / "media")
    assert repeated.returncode == 0, repeated.stderr
    assert (again.parent / "health.json").read_bytes() == health.read_bytes()


def test_health_json_keeps_per_trial_documents(tmp_path):
    result = tmp_path / "result.json"
    manifest = ORIGINAL / "evidence" / "manifest.json"
    completed = run_advisory(tmp_path, manifest, result, ORIGINAL / "media")
    assert completed.returncode == 0, completed.stderr
    health = parse(result.parent / "health.json")
    assert health["format"] == "livingproof-evaluator-health/1"
    assert set(health) == {"format", "trials"}
    legacy = tmp_path / "legacy.json"
    per_trial = run_cli(
        tmp_path,
        "--evidence",
        str(ORIGINAL / "evidence"),
        "--media",
        str(ORIGINAL / "media"),
        "--trial",
        "1",
        "--output",
        str(legacy),
    )
    assert per_trial.returncode == 0, per_trial.stderr
    assert health["trials"] == [json.loads(legacy.read_text(encoding="utf-8"))]


def test_every_trial_is_in_the_advisory_result(tmp_path):
    recording = tmp_path / "recording"
    shutil.copytree(ORIGINAL, recording)

    def add_evidence(doc):
        trial = copy.deepcopy(doc["trials"]["results"][0])
        trial["index"] = 2
        doc["trials"]["results"].append(trial)
        doc["trials"]["count"] = 2

    def add_media(doc):
        trial = copy.deepcopy(doc["trials"][0])
        trial["index"] = 2
        doc["trials"].append(trial)

    edit(recording / "evidence" / "manifest.json", add_evidence)
    edit(recording / "media" / "media.json", add_media)
    result = tmp_path / "out" / "result.json"
    completed = run_advisory(
        tmp_path,
        recording / "evidence" / "manifest.json",
        result,
        recording / "media",
    )
    assert completed.returncode == 0, completed.stderr
    document = parse(result)
    health = parse(result.parent / "health.json")
    assert [trial["index"] for trial in document["advisory"]["trials"]] == [1, 2]
    assert [report["trial"]["index"] for report in health["trials"]] == [1, 2]
    assert_unique_trials(document)
    for report in health["trials"]:
        index = report["trial"]["index"]
        token = f"{report['simulator']['sample_count']} recorded samples"
        assert f"Trial {index}" in document["advisory"]["summary"]
        assert f"Trial {index}" in document["advisory"]["details"]
        assert token in document["advisory"]["summary"]
        assert token in document["advisory"]["details"]
        legacy = tmp_path / f"legacy-{index}.json"
        per_trial = run_cli(
            tmp_path,
            "--evidence",
            str(recording / "evidence"),
            "--media",
            str(recording / "media"),
            "--trial",
            str(index),
            "--output",
            str(legacy),
        )
        assert per_trial.returncode == 0, per_trial.stderr
        assert report == json.loads(legacy.read_text(encoding="utf-8"))


def test_advisory_mode_rejects_trial_flag(tmp_path):
    result = tmp_path / "result.json"
    completed = run_cli(
        tmp_path,
        str(ORIGINAL / "evidence" / "manifest.json"),
        "--media",
        str(ORIGINAL / "media"),
        "--trial",
        "1",
        "--out",
        str(result),
    )
    assert completed.returncode == 2
    assert not result.exists()
    assert not (tmp_path / "health.json").exists()


def test_advisory_refusal_leaves_no_files(tmp_path):
    recording = tmp_path / "recording"
    shutil.copytree(ORIGINAL, recording)
    edit(
        recording / "evidence" / "manifest.json",
        lambda doc: doc["trials"]["results"][0].update(sha256="0" * 64),
    )
    result = tmp_path / "out" / "result.json"
    completed = run_advisory(
        tmp_path,
        recording / "evidence" / "manifest.json",
        result,
        recording / "media",
    )
    assert completed.returncode == 2
    assert "SHA-256" in completed.stderr
    assert not result.exists()
    assert not (result.parent / "health.json").exists()


@pytest.mark.parametrize(
    ("flag", "reason"),
    [
        ((), "Health was not run: media missing."),
        (("--media-disabled",), "Health was not run: media disabled."),
    ],
)
def test_no_media_is_refused(tmp_path, flag, reason):
    result = tmp_path / "out" / "result.json"
    completed = run_advisory(
        tmp_path,
        ORIGINAL / "evidence" / "manifest.json",
        result,
        extra=flag,
    )
    assert completed.returncode == 2
    assert completed.returncode != 0
    assert completed.stderr.splitlines() == [reason]
    assert not completed.stdout
    assert not result.exists()
    assert not (result.parent / "health.json").exists()
    if result.parent.exists():
        assert list(result.parent.iterdir()) == []
