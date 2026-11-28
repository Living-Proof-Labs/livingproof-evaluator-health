# SPDX-License-Identifier: Apache-2.0
"""Advisory CLI: one contract result for every trial, citing health.json."""

import copy
import hashlib
import json
from pathlib import Path
import re
import shutil

import pytest

from livingproof_evaluator_health.__main__ import main
from livingproof_evaluator_health.advisory import (
    DETAILS_LIMIT,
    SUMMARY_LIMIT,
    _ADVISORY_TEXT,
    _bound,
    _cover,
    _first_few,
    _guaranteed,
    _summary_primary,
)
from test_cli import run_cli
from test_evaluate import DATA_END, FOOTER, HEADER, edit, envelope
from test_implementation_descriptor import SCHEMA_DIR, descriptor, errors

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
        assert document["advisory"]["details"].startswith(expected)
        assert "check unevaluated" in document["advisory"]["details"]
        assert "criterion provenance unavailable" in document["advisory"]["summary"]
        assert "Source " not in document["advisory"]["details"]


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
        assert "criterion provenance unavailable" in document["advisory"]["summary"]
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


def advisory_contract():
    schema = json.loads((SCHEMA_DIR / "evaluator-result.schema.json").read_text(encoding="utf-8"))
    props = schema["$defs"]["advisory"]["properties"]
    return (
        props["summary"]["maxLength"],
        props["details"]["maxLength"],
        schema["$defs"]["advisory_text"]["pattern"],
    )


def test_text_limits_come_from_the_vendored_schema():
    summary_limit, details_limit, pattern = advisory_contract()
    assert SUMMARY_LIMIT == summary_limit
    assert DETAILS_LIMIT == details_limit
    assert _ADVISORY_TEXT.pattern == pattern


def many_recording(root, count):
    evidence = root / "evidence"
    trials = evidence / "trials"
    mcap_dir = root / "media" / "mcap"
    trials.mkdir(parents=True)
    mcap_dir.mkdir(parents=True)
    observation = ORIGINAL / "evidence" / "trials" / "trial-01.json"
    shutil.copy(observation, trials / "trial-01.json")
    shutil.copy(ORIGINAL / "evidence" / "run-manifest.json", evidence / "run-manifest.json")
    digest = hashlib.sha256(observation.read_bytes()).hexdigest()
    manifest = json.loads((ORIGINAL / "evidence" / "manifest.json").read_text(encoding="utf-8"))
    manifest["trials"] = {
        "count": count,
        "results": [
            {"index": index, "path": "trials/trial-01.json", "sha256": digest}
            for index in range(1, count + 1)
        ],
    }
    (evidence / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    blob = envelope(HEADER, DATA_END, FOOTER)
    (mcap_dir / "trial.mcap").write_bytes(blob)
    media = json.loads((ORIGINAL / "media" / "media.json").read_text(encoding="utf-8"))
    media["trials"] = [
        {
            "index": index,
            "observation_sha256": digest,
            "mcap": {
                "path": "mcap/trial.mcap",
                "bytes": len(blob),
                "sha256": hashlib.sha256(blob).hexdigest(),
            },
        }
        for index in range(1, count + 1)
    ]
    (root / "media" / "media.json").write_text(json.dumps(media), encoding="utf-8")


@pytest.mark.parametrize("count", [5, 50, 1000])
def test_many_trials_fit_the_schema(tmp_path, count):
    summary_limit, details_limit, pattern = advisory_contract()
    compiled = re.compile(pattern)
    recording = tmp_path / f"recording-{count}"
    many_recording(recording, count)
    result = tmp_path / f"out-{count}" / "result.json"
    completed = run_advisory(
        tmp_path,
        recording / "evidence" / "manifest.json",
        result,
        recording / "media",
    )
    assert completed.returncode == 0, completed.stderr
    document = parse(result)
    health = parse(result.parent / "health.json")
    assert schema_errors(document) == []
    summary = document["advisory"]["summary"]
    details = document["advisory"]["details"]
    assert 1 <= len(summary) <= summary_limit
    assert 1 <= len(details) <= details_limit
    assert compiled.fullmatch(summary)
    assert compiled.fullmatch(details)
    expected = list(range(1, count + 1))
    assert [trial["index"] for trial in document["advisory"]["trials"]] == expected
    assert [report["trial"]["index"] for report in health["trials"]] == expected
    assert_unique_trials(document)


def _framed(index, frame):
    return {
        "trial": {"index": index, "observation_sha256": "a" * 64},
        "simulator": {
            "status": "recorded simulator observations",
            "sample_count": 2,
            "minimum_recorded_base_height_by_frame": {
                frame: {"height_m": 0.5, "time_ns": "1000000000"}
            },
        },
        "robot": {"status": "no robot health telemetry"},
    }


@pytest.mark.parametrize("frame", ["a<b>", "a\x01b"])
def test_frame_name_stays_plain(frame):
    _summary_limit, _details_limit, pattern = advisory_contract()
    compiled = re.compile(pattern)
    summary, details = _cover([_framed(1, frame)])
    for text in (summary, details):
        assert "<" not in text and ">" not in text
        assert "\x01" not in text
        assert "\n" not in text
        assert "0.5" in text
        assert compiled.fullmatch(text)


def _status(index, simulator, robot):
    return {
        "trial": {"index": index, "observation_sha256": "ab" * 32},
        "simulator": {"status": simulator},
        "robot": {"status": robot},
    }


def test_mixed_statuses_stay_in_separate_groups():
    reports = [
        _status(1, "alpha", "red"),
        _status(2, "alpha", "red"),
        _status(3, "beta", "blue"),
    ]
    text = _bound(_summary_primary(reports), 43, reports)
    assert text == "Trials 1, 2: alpha; red Trial 3: beta; blue"


def test_first_few_names_status_and_hidden_count():
    reports = [_status(index, f"sim{index}", "R" * 20) for index in range(1, 6)]
    text = _bound(_summary_primary(reports), 101, reports)
    assert text == (
        "Trial 1: sim1; RRRRRRRRRRRRRRRRRRRR "
        "Trial 2: sim2; RRRRRRRRRRRRRRRRRRRR "
        "… and 3 more; see health.json"
    )
    assert text.endswith("… and 3 more; see health.json")
    assert text.index("Trial 1: sim1;") < text.index("Trial 2: sim2;")
    assert "Trial 3:" not in text


def test_first_few_second_block_boundary():
    short = [_status(1, "a", "b"), _status(2, "c", "d"), _status(3, "e", "f")]
    # Two blocks plus the hidden-trial ending are 57 characters, one past 56.
    assert _first_few(short, 56) == "Trial 1: a; b … and 2 more; see health.json"
    longer = [
        _status(1, "a" * 10, "b" * 10),
        _status(2, "c" * 10, "d" * 10),
        _status(3, "e" * 10, "f" * 10),
    ]
    # Two blocks plus the ending are 93 characters; three blocks are 95.
    assert _first_few(longer, 93) == (
        "Trial 1: aaaaaaaaaa; bbbbbbbbbb "
        "Trial 2: cccccccccc; dddddddddd "
        "… and 1 more; see health.json"
    )
    assert len(_first_few(longer, 93)) == 93
    assert _first_few(longer, 92) == (
        "Trial 1: aaaaaaaaaa; bbbbbbbbbb … and 2 more; see health.json"
    )


def test_first_few_keeps_exact_limit_and_drops_one_over():
    reports = [_status(index, "S" * 30, "R" * 10) for index in range(1, 6)]
    kept = _first_few(reports, 81)
    dropped = _first_few(reports, 80)
    assert kept == (
        "Trial 1: SSSSSSSSSSSSSSSSSSSSSSSSSSSSSS; RRRRRRRRRR … and 4 more; see health.json"
    )
    assert len(kept) == 81
    assert dropped == "Trial 1: see health.json … and 4 more; see health.json"


def test_last_resort_stays_within_tiny_limits():
    reports = [_status(1, "alpha", "red"), _status(2, "alpha", "red")]
    assert _guaranteed(reports, 40) == "See health.json."
    assert len(_guaranteed(reports, 40)) <= 40
    assert _guaranteed(reports, 80) == ("Trial 1: see health.json … and 1 more; see health.json")
    assert len(_guaranteed(reports, 80)) <= 80


def test_long_status_is_shortened_on_the_cli(tmp_path, monkeypatch):
    status = "S" * 3000

    def fake_evaluate(evidence, media, index, disabled=False):
        report = _status(index, "recorded-run", status)
        report["evidence_manifest_sha256"] = "b" * 64
        report["media_manifest_sha256"] = "c" * 64
        return report

    monkeypatch.setattr("livingproof_evaluator_health.advisory.evaluate", fake_evaluate)
    result = tmp_path / "result.json"
    code = main(
        [
            str(ORIGINAL / "evidence" / "manifest.json"),
            "--media",
            str(ORIGINAL / "media"),
            "--out",
            str(result),
        ]
    )
    assert code == 0
    document = parse(result)
    assert schema_errors(document) == []
    summary_limit, details_limit, _pattern = advisory_contract()
    summary = document["advisory"]["summary"]
    details = document["advisory"]["details"]
    assert summary == "Trial 1: see health.json"
    assert details == "Trial 1: see health.json"
    assert len(summary) <= summary_limit
    assert len(details) <= details_limit
    assert status not in summary and status not in details


def test_zwj_in_a_frame_name_survives():
    frame = "wo\u200drld"
    summary, details = _cover([_framed(1, frame)])
    assert "\u200d" in summary and "\u200d" in details
    assert _ADVISORY_TEXT.fullmatch(summary)
    assert _ADVISORY_TEXT.fullmatch(details)
