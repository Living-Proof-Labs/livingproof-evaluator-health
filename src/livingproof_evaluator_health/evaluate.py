# SPDX-License-Identifier: Apache-2.0
"""Recorded observations only: no health policy, scores, or hardware inference."""

import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import re
import stat
import tempfile

from livingproof_health.bounds import Limits, records
from livingproof_health.recording import read_mcap
from livingproof_health.snapshots import snapshot_to_wire
from mcap.records import Channel, Message, Schema, Statistics

from .structure import validate_sections
from .observations import validate_observation

HEALTH_SHA256 = "d1ce13c2b68e31855ac81a83b478f174182bf0ab4894d917b7e0dd406ba2857c"
LIMITS = Limits()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read(path, maximum):
    require(stat.S_ISREG(path.stat().st_mode), f"Not a regular file: {path}")
    with path.open("rb") as stream:
        data = stream.read(maximum + 1)
    require(len(data) <= maximum, f"Input exceeds {maximum} bytes: {path}")
    return data


def pairs(items):
    result = {}
    for key, value in items:
        require(key not in result, f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def invalid_constant(value):
    raise ValueError(f"Non-finite JSON constant: {value}")


def document(path):
    data = read(path, 4 << 20)
    result = json.loads(data, object_pairs_hook=pairs, parse_constant=invalid_constant)
    require(isinstance(result, dict), f"Expected JSON object: {path}")
    return result, digest(data)


def object_at(value, key):
    result = value.get(key)
    require(isinstance(result, dict), f"Expected object: {key}")
    return result


def text(value):
    return isinstance(value, str) and bool(value.strip())


def sha(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def child(root, relative):
    require(text(relative), "Missing relative evidence path")
    p = Path(relative)
    require(not p.is_absolute() and ".." not in p.parts, "Unsafe evidence path")
    result = (root / p).resolve()
    require(result.is_relative_to(root.resolve()), "Evidence path escapes its directory")
    return result


def select(entries, index):
    require(isinstance(entries, list) and bool(entries), "Expected nonempty trials array")
    seen = set()
    for entry in entries:
        require(isinstance(entry, dict), "Invalid trial entry")
        value = entry.get("index")
        require(
            type(value) is int and value > 0 and value not in seen, "Invalid/duplicate trial index"
        )
        seen.add(value)
    matches = [entry for entry in entries if entry["index"] == index]
    require(len(matches) == 1, "Requested trial is not declared")
    return matches[0]


def inspect_mcap(path):
    """Use Health's bounded framing/CRC reader; validate channel references too."""
    validate_sections(path, LIMITS)
    schemas, channels, counts = {}, {}, {}
    statistics = None
    channel_counts = {}
    with records(path, LIMITS) as (entries, _):
        for record in entries:
            if isinstance(record, Schema):
                require(
                    record.id not in schemas or schemas[record.id] == record, "Conflicting schema"
                )
                schemas[record.id] = record
            elif isinstance(record, Channel):
                require(not record.schema_id or record.schema_id in schemas, "Unknown MCAP schema")
                require(
                    record.id not in channels or channels[record.id] == record,
                    "Conflicting channel",
                )
                channels[record.id] = record
            elif isinstance(record, Message):
                require(record.channel_id in channels, "Unknown MCAP channel")
                topic = channels[record.channel_id].topic
                counts[topic] = counts.get(topic, 0) + 1
                channel_counts[record.channel_id] = channel_counts.get(record.channel_id, 0) + 1
            elif isinstance(record, Statistics):
                require(statistics is None, "Duplicate MCAP Statistics")
                statistics = record
    if statistics is not None:
        require(statistics.message_count == sum(counts.values()), "MCAP message count mismatch")
        if statistics.channel_message_counts:
            require(
                {key: count for key, count in statistics.channel_message_counts.items() if count}
                == channel_counts,
                "MCAP channel message counts mismatch",
            )
    return dict(sorted(counts.items()))


def evaluate(evidence, media, index, disabled=False):
    require(version("livingproof-health") == "1.0.5", "Expected pinned Health 1.0.5")
    manifest, manifest_hash = document(evidence / "manifest.json")
    require(
        manifest.get("format") == "livingproof-hallway-evidence/2.0.0",
        "Unsupported evidence format",
    )
    run_id = manifest.get("run_id")
    configuration = object_at(manifest, "configuration").get("name")
    require(text(run_id) and text(configuration), "Missing run/configuration identity")
    trial = select(object_at(manifest, "trials").get("results"), index)
    require(sha(trial.get("sha256")), "Invalid observation SHA-256")
    observation_path = child(evidence, trial.get("path"))
    observation, observation_hash = document(observation_path)
    require(observation_hash == trial["sha256"], "Observation SHA-256 mismatch")
    validate_observation(observation)
    result = {
        "format": "livingproof-evaluator-health/1",
        "evaluator_version": version("livingproof-evaluator-health"),
        "health_version": version("livingproof-health"),
        "health_wheel_sha256": HEALTH_SHA256,
        "trial": {
            "run_id": run_id,
            "configuration": configuration,
            "index": index,
            "observation_sha256": observation_hash,
        },
        "evidence_manifest_sha256": manifest_hash,
        "scope": "Recorded samples only; no between-sample or physical robot health proof.",
        "simulator": {"status": "media disabled" if disabled else "media missing"},
        "robot": {"status": "media disabled" if disabled else "media missing"},
    }
    if media is None:
        return result
    media_doc, media_hash = document(media / "media.json")
    fmt = media_doc.get("format")
    require(
        fmt in {f"livingproof-hallway-media/{v}" for v in ("2.0.0", "2.1.0", "2.2.0")},
        "Unsupported media format",
    )
    require(
        media_doc.get("run_id") == run_id and media_doc.get("configuration") == configuration,
        "Media run/configuration identity mismatch",
    )
    selected = select(media_doc.get("trials"), index)
    require(
        selected.get("observation_sha256") == observation_hash, "Media trial observation mismatch"
    )
    result["media_manifest_sha256"] = media_hash
    result["media_format"] = fmt
    run, run_hash = document(evidence / "run-manifest.json")
    require(
        run.get("format") == "livingproof-run-manifest/0.1" and run.get("run_id") == run_id,
        "Run manifest identity mismatch",
    )
    require(
        object_at(run, "configuration").get("name") == configuration, "Run configuration mismatch"
    )
    producer = object_at(run, "simulator")
    require(
        all(text(producer.get(k)) for k in ("engine", "version", "adapter", "adapter_commit")),
        "Missing simulator provenance",
    )
    result["run_manifest_sha256"] = run_hash
    result["simulator_producer"] = producer
    # Freeze and authenticate every selected declared stream before any MCAP decoding.
    with tempfile.TemporaryDirectory(prefix="health-trial-") as temporary:
        verified = {}
        keys = ["mcap", "robot_mcap"] if fmt.endswith("2.2.0") else ["mcap"]
        require(
            fmt.endswith("2.2.0") or "robot_mcap" not in selected,
            "Robot stream requires media 2.2.0",
        )
        for key in keys:
            entry = object_at(selected, key)
            require(
                sha(entry.get("sha256"))
                and type(entry.get("bytes")) is int
                and 0 <= entry["bytes"] <= LIMITS.input_bytes,
                "Invalid media digest/size",
            )
            source = child(media, entry.get("path"))
            label = "simulator" if key == "mcap" else "robot"
            result[label] = {"source": dict(entry), "provenance": label}
            if not source.exists():
                result[label]["status"] = "declared media file missing"
                continue
            data = read(source, LIMITS.input_bytes)
            require(
                len(data) == entry["bytes"] and digest(data) == entry["sha256"],
                f"Media SHA-256/size mismatch: {key}",
            )
            frozen = Path(temporary) / key
            frozen.write_bytes(data)
            verified[label] = frozen
        if "robot_mcap" not in keys:
            result["robot"] = {"status": "robot stream not declared by this media version"}
        for label, path in verified.items():
            counts = inspect_mcap(path)
            result[label]["message_counts"] = counts
            if label == "robot":
                result[label]["status"] = (
                    "no robot health telemetry"
                    if not counts
                    else "robot messages present; health interpretation unsupported"
                )
                continue
            if not counts.get("/base_pose"):
                result[label]["status"] = "no recorded base pose"
                continue
            samples = [snapshot_to_wire(s) for s in read_mcap(path, limits=LIMITS)]
            result[label].update(
                status="recorded simulator observations",
                sample_count=len(samples),
                snapshots=samples,
            )
            minima = {}
            unavailable = 0
            for sample in samples:
                pose = sample["items"]["base_pose"]
                if pose is None:
                    unavailable += 1
                    continue
                frame = pose["frame_id"]
                height = pose["position"]["z"]
                if frame not in minima or height < minima[frame]["height_m"]:
                    minima[frame] = {"height_m": height, "time_ns": sample["time_ns"]}
            result[label]["minimum_recorded_base_height_by_frame"] = minima
            result[label]["unavailable_base_pose_samples"] = unavailable
    return result
