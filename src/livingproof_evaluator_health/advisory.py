# SPDX-License-Identifier: Apache-2.0
"""One advisory result for every trial in an evidence manifest.

The details file next to that result is health.json. Its format stays
livingproof-evaluator-health/1. The file is an object with that format and a
trials array, in manifest order. Each element is the per-trial document the
--evidence/--trial/--output command writes.
"""

from datetime import UTC, datetime
import json
from pathlib import Path
import re

from .evaluate import child, digest, document, evaluate, object_at, require, sha
from .identity import (
    DISPLAY_NAME,
    EVALUATOR_ID,
    EXECUTION,
    ICON,
    KIND,
    PUBLISHER,
    PURPOSE,
    RESULT_FORMAT,
    TIER,
    package_version,
)

# livingproof-evaluator v1.10.0 evaluator-result.schema.json:
# advisory.summary maxLength, advisory.details maxLength, and advisory_text.
SUMMARY_LIMIT = 400
DETAILS_LIMIT = 2000
_ADVISORY_TEXT = re.compile(
    "^(?=.*[^\\s\\u200C\\u200D])"
    "[^<>\\u0000-\\u001F\\u007F-\\u009F\\u180E\\u200B\\u200E\\u200F"
    "\\u2028-\\u202E\\u2060-\\u2064\\u2066-\\u2069\\uD800-\\uDFFF\\uFEFF]*"
    "(?!\\n)$"
)
_MORE = " … and {count} more; see health.json"
# Characters the advisory_text pattern rejects inside a sentence. ZWJ, ZWNJ,
# and NBSP are allowed by that pattern and are not in this set.
_FORBIDDEN = re.compile(
    "["
    "<>"
    "\u0000-\u001f"
    "\u007f-\u009f"
    "\u180e"
    "\u200b"
    "\u200e\u200f"
    "\u2028-\u202e"
    "\u2060-\u2064"
    "\u2066-\u2069"
    "\ud800-\udfff"
    "\ufeff"
    "]"
)


def action_details(report):
    """Sentences previously built in verification-reports-action.

    Source tag, commit, and provenance are not known here, so that action-only
    sentence is not included.
    """
    parts = []
    simulator = report["simulator"]
    if simulator.get("status") == "recorded simulator observations":
        parts.append(f"Simulator: {simulator['sample_count']} recorded samples.")
        minima = simulator.get("minimum_recorded_base_height_by_frame") or {}
        for frame, minimum in sorted(minima.items()):
            seconds = int(minimum["time_ns"]) / 1_000_000_000
            parts.append(
                f"Minimum recorded base height ({frame}): {minimum['height_m']:g} m "
                f"at {seconds:g} s."
            )
    else:
        parts.append("Simulator base-height measurements unavailable.")
    robot_status = report["robot"]["status"]
    if robot_status == "no robot health telemetry":
        parts.append(
            "No robot health telemetry. The robot stream is valid and empty; "
            "this is not a healthy verdict."
        )
    else:
        parts.append(f"Robot health assessment unavailable: {robot_status}.")
    if report.get("_height_details"):
        parts.append(report["_height_details"])
    return " ".join(parts)


def _plain_text(value):
    """Drop characters the advisory text pattern rejects, keeping the sentence."""
    cleaned = _FORBIDDEN.sub("", value)
    if _ADVISORY_TEXT.fullmatch(cleaned):
        return cleaned
    return "See health.json."


def _summary_primary(reports):
    return " ".join(
        f"Trial {report['trial']['index']}: "
        + (
            report["_height_summary"] + " " + _short(report)
            if "_height_summary" in report
            else action_details(report)
        )
        for report in reports
    )


def _details_primary(reports):
    if len(reports) == 1:
        return action_details(reports[0])
    return " ".join(f"Trial {r['trial']['index']}: {action_details(r)}" for r in reports)


def _short(report):
    return f"{report['simulator']['status']}; {report['robot']['status']}"


def _grouped(reports, body):
    groups = []
    for report in reports:
        text = body(report)
        if groups and groups[-1][0] == text:
            groups[-1][1].append(report["trial"]["index"])
        else:
            groups.append((text, [report["trial"]["index"]]))
    parts = []
    for text, indexes in groups:
        noun = "Trial" if len(indexes) == 1 else "Trials"
        listed = ", ".join(str(index) for index in indexes)
        parts.append(f"{noun} {listed}: {text}")
    return " ".join(parts)


def _guaranteed(reports, limit):
    first = reports[0]["trial"]["index"]
    hidden = len(reports) - 1
    text = f"Trial {first}: see health.json"
    if hidden:
        text += _MORE.format(count=hidden)
    text = _plain_text(text)
    if 1 <= len(text) <= limit:
        return text
    # "See health.json." is 16 characters. The schema limits are 400 and 2000,
    # so this fallback is never sliced.
    return "See health.json."


def _first_few(reports, limit):
    chosen = []
    for offset, report in enumerate(reports):
        hidden = len(reports) - offset - 1
        block = f"Trial {report['trial']['index']}: {_short(report)}"
        suffix = _MORE.format(count=hidden) if hidden else ""
        candidate = _plain_text((" ".join([*chosen, block]) + suffix).strip())
        if 1 <= len(candidate) <= limit:
            chosen.append(block)
            continue
        hidden = len(reports) - len(chosen)
        if chosen and hidden:
            text = _plain_text((" ".join(chosen) + _MORE.format(count=hidden)).strip())
            if 1 <= len(text) <= limit:
                return text
        return _guaranteed(reports, limit)
    text = _plain_text(" ".join(chosen))
    if 1 <= len(text) <= limit:
        return text
    return _guaranteed(reports, limit)


def _bound(primary, limit, reports):
    text = _plain_text(primary)
    if 1 <= len(text) <= limit:
        return text
    for body in (action_details, _short):
        text = _plain_text(_grouped(reports, body))
        if 1 <= len(text) <= limit:
            return text
    return _first_few(reports, limit)


def _fit_summary(reports):
    return _bound(_summary_primary(reports), SUMMARY_LIMIT, reports)


def _fit_details(reports):
    return _bound(_details_primary(reports), DETAILS_LIMIT, reports)


def _cover(reports):
    return _fit_summary(reports), _fit_details(reports)


def _root(evidence, media):
    evidence_root = evidence.resolve().parent
    if media is None:
        return evidence_root
    media_root = media.resolve()
    if media_root.is_relative_to(evidence_root):
        return evidence_root
    if evidence.resolve().is_relative_to(media_root.parent):
        return media_root.parent
    return evidence_root


def _uri(path, root):
    try:
        uri = path.resolve().relative_to(root).as_posix()
    except ValueError:
        uri = path.name
    require(bool(uri) and ".." not in Path(uri).parts, "Unsafe result input path")
    return uri


def _cite(role, path, root, digest_hex):
    return {"role": role, "uri": _uri(path, root), "sha256": digest_hex}


def _stream(role, section, media, root):
    source = section.get("source")
    if not isinstance(source, dict) or section.get("status") == "declared media file missing":
        return None
    if not sha(source.get("sha256")):
        return None
    path = child(media, source.get("path"))
    if not path.is_file():
        return None
    return _cite(role, path, root, source["sha256"])


def collect(manifest_path, media, disabled):
    require(
        manifest_path.name == "manifest.json",
        "Evidence manifest path must be named manifest.json",
    )
    manifest, _ = document(manifest_path)
    require(
        manifest.get("format") == "livingproof-hallway-evidence/2.0.0",
        "Unsupported evidence format",
    )
    entries = object_at(manifest, "trials").get("results")
    require(isinstance(entries, list) and entries, "Expected nonempty trials array")
    evidence = manifest_path.parent
    reports = []
    for entry in entries:
        require(isinstance(entry, dict), "Invalid trial entry")
        index = entry.get("index")
        report = evaluate(evidence, media, index, disabled)
        require(report["trial"]["index"] == index, "Trial index mismatch")
        reports.append(report)
    return reports


def _inputs(manifest_path, media, reports):
    evidence = manifest_path.parent
    root = _root(evidence, media)
    inputs = [
        _cite(
            "evidence-manifest",
            manifest_path,
            root,
            reports[0]["evidence_manifest_sha256"],
        )
    ]
    manifest, _ = document(manifest_path)
    entries = object_at(manifest, "trials").get("results")
    for entry, report in zip(entries, reports, strict=True):
        inputs.append(
            _cite(
                "observation",
                child(evidence, entry.get("path")),
                root,
                report["trial"]["observation_sha256"],
            )
        )
    if media is None:
        return inputs
    inputs.append(
        _cite(
            "media-manifest",
            media / "media.json",
            root,
            reports[0]["media_manifest_sha256"],
        )
    )
    for report in reports:
        recording = _stream("recording", report["simulator"], media, root)
        if recording is not None:
            inputs.append(recording)
        robot = _stream("robot-recording", report["robot"], media, root)
        if robot is not None:
            inputs.append(robot)
    return inputs


def health_document(reports):
    return {"format": "livingproof-evaluator-health/1", "trials": reports}


def result_document(reports, inputs, summary, details, health_sha, started, completed):
    version = package_version()
    return {
        "format": RESULT_FORMAT,
        "evaluator": {
            "id": EVALUATOR_ID,
            "version": version,
            "kind": KIND,
            "execution": EXECUTION,
            "display_name": DISPLAY_NAME,
            "publisher": PUBLISHER,
            "icon": ICON,
        },
        "inputs": inputs,
        "timestamps": {
            "started_at": started.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "completed_at": completed.strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        "descriptor": {
            "title": DISPLAY_NAME,
            "purpose": PURPOSE,
            "version": version,
            "tier": TIER,
            "icon": ICON,
            "icon_accessible_name": DISPLAY_NAME,
        },
        "advisory": {
            "summary": summary,
            "details": details,
            "details_file": {"uri": "health.json", "sha256": health_sha},
            "trials": [
                {
                    "index": report["trial"]["index"],
                    "observation_sha256": report["trial"]["observation_sha256"],
                }
                for report in reports
            ],
        },
    }


def dump(document):
    text = json.dumps(document, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return text.encode("utf-8") + b"\n"


def _occupied(path):
    try:
        path.lstat()
    except FileNotFoundError:
        return False
    return True


def _create(path, data):
    with path.open("xb") as stream:
        stream.write(data)


def write_advisory(manifest_path, media, output, disabled=False):
    started = datetime.now(UTC)
    reports = collect(manifest_path, media, disabled)
    health_bytes = dump(health_document(reports))
    from .criterion import text_for

    presented = []
    for report in reports:
        height_summary, height_details = text_for(manifest_path, report)
        presented.append(
            dict(report, _height_summary=height_summary, _height_details=height_details)
        )
    summary, details = _cover(presented)
    completed = datetime.now(UTC)
    result = result_document(
        reports,
        _inputs(manifest_path, media, reports),
        summary,
        details,
        digest(health_bytes),
        started,
        completed,
    )
    result_bytes = dump(result)
    details_path = output.parent / "health.json"
    require(
        details_path.resolve() != output.resolve(),
        "The result path cannot be named health.json",
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    if _occupied(output) or _occupied(details_path):
        occupied = output if _occupied(output) else details_path
        raise FileExistsError(f"Refusing to overwrite {occupied}")
    _create(details_path, health_bytes)
    try:
        _create(output, result_bytes)
    except Exception:
        details_path.unlink(missing_ok=True)
        raise
