# SPDX-License-Identifier: Apache-2.0
"""livingproof-evaluator.json against the vendored v1.10.0 implementation schema.

The schema copies next to pin.json are livingproof-evaluator's. pin.json is the pin.
"""

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import urllib.request

import pytest
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[1]
DESCRIPTOR = ROOT / "livingproof-evaluator.json"
SCHEMA_DIR = ROOT / "tests" / "fixtures" / "evaluator-schema"
PIN = SCHEMA_DIR / "pin.json"
README = ROOT / "README.md"
DESCRIPTOR_LINE = "Living-Proof-Labs/livingproof-evaluator-health@<tag>/livingproof-evaluator.json"
TAG = re.compile(r"^v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
COMMIT = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
PLACEHOLDER = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")
FIXED = {"evidence_manifest", "media_dir", "result"}


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def descriptor():
    return load(DESCRIPTOR)


def pin():
    return load(PIN)


def registry():
    resources = []
    for path in sorted(SCHEMA_DIR.rglob("*.schema.json")):
        contents = json.loads(path.read_text(encoding="utf-8"))
        resources.append((contents["$id"], Resource.from_contents(contents)))
    return Registry().with_resources(resources)


def validator(name):
    schema = json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))
    return Draft202012Validator(schema, registry=registry())


def errors(name, instance):
    return list(validator(name).iter_errors(instance))


def test_descriptor_fields():
    document = descriptor()
    assert document["format"] == "livingproof-evaluator-implementation/1"
    assert document["id"] == "livingproof-health"
    assert document["kind"] == "advisory"
    assert document["grading"] == "none"
    assert document["result"] == "livingproof-evaluator-result/1.3.0"
    assert document["package"] == {"name": "livingproof-evaluator-health"}
    assert document["runtime"] == {"python": "3.12"}
    assert document["entrypoint"] == {"module": "livingproof_evaluator_health"}
    assert document["exit_codes"] == {"0": "result", "2": "refused"}


def test_arguments_use_only_fixed_placeholders():
    arguments = descriptor()["arguments"]
    assert arguments == [
        "{evidence_manifest}",
        {"if": "media_dir", "then": ["--media", "{media_dir}"]},
        "--out",
        "{result}",
    ]
    top_level = set()
    conditional = {}
    for item in arguments:
        if isinstance(item, str):
            top_level.update(PLACEHOLDER.findall(item))
            continue
        assert set(item) == {"if", "then"}
        found = set()
        for part in item["then"]:
            found.update(PLACEHOLDER.findall(part))
        conditional[item["if"]] = found
    assert top_level <= {"evidence_manifest", "result"}
    assert "evidence_manifest" in top_level and "result" in top_level
    assert "media_dir" not in top_level
    assert conditional == {"media_dir": {"media_dir"}}
    used = top_level | set().union(*conditional.values())
    assert used <= FIXED


def test_descriptor_matches_vendored_schema():
    assert errors("implementation.schema.json", descriptor()) == []
    extra = {**descriptor(), "note": "not in the schema"}
    assert errors("implementation.schema.json", extra)


def test_vendored_schema_hashes_match_pin():
    recorded = pin()
    assert recorded["repository"] == "Living-Proof-Labs/livingproof-evaluator"
    assert TAG.fullmatch(recorded["tag"])
    assert COMMIT.fullmatch(recorded["commit"])
    pinned = set()
    for rel, digest in recorded["files"].items():
        assert SHA256.fullmatch(digest)
        assert rel.startswith("schema/")
        fixture = SCHEMA_DIR / Path(rel).relative_to("schema")
        assert hashlib.sha256(fixture.read_bytes()).hexdigest() == digest
        pinned.add(fixture.resolve())
    present = {path.resolve() for path in SCHEMA_DIR.rglob("*.schema.json")}
    assert present == pinned


def _in_ci():
    for name in ("CI", "GITHUB_ACTIONS"):
        if os.environ.get(name, "").strip().lower() in {"1", "true", "yes"}:
            return True
    return False


def test_pin_matches_the_release():
    if os.environ.get("LIVINGPROOF_OFFLINE") == "1":
        if _in_ci():
            pytest.fail("LIVINGPROOF_OFFLINE=1 must not skip the release pin check in CI")
        pytest.skip("LIVINGPROOF_OFFLINE=1")

    recorded = pin()
    remote = f"https://github.com/{recorded['repository']}.git"
    ref = f"refs/tags/{recorded['tag']}"
    peeled_ref = f"{ref}^{{}}"
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    completed = subprocess.run(
        ["git", "ls-remote", "--tags", remote, ref, peeled_ref],
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
        env=env,
    )
    by_name = {}
    for line in completed.stdout.splitlines():
        if not line.strip():
            continue
        sha, name = line.split("\t", 1)
        by_name[name] = sha
    if peeled_ref in by_name:
        peeled = by_name[peeled_ref]
    elif list(by_name) == [ref]:
        peeled = by_name[ref]
    else:
        raise AssertionError(completed.stdout)
    assert peeled == recorded["commit"]

    for rel, digest in recorded["files"].items():
        url = (
            f"https://raw.githubusercontent.com/{recorded['repository']}/{recorded['commit']}/{rel}"
        )
        with urllib.request.urlopen(url, timeout=60) as response:
            body = response.read()
        assert hashlib.sha256(body).hexdigest() == digest


def test_readme_names_the_descriptor_line():
    text = README.read_text(encoding="utf-8")
    matches = [line for line in text.splitlines() if DESCRIPTOR_LINE in line]
    assert matches
    assert "livingproof-evaluator.json" in matches[0]
