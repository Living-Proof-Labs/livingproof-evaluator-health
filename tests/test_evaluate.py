# SPDX-License-Identifier: Apache-2.0
"""User-facing subprocess evidence, including refusals before any decoding."""

import hashlib
import json
from pathlib import Path
import shutil

import pytest
from mcap.writer import Writer

from test_cli import run_cli

FIXTURE = Path(__file__).parent / "fixtures" / "original-recording"


@pytest.fixture
def recording(tmp_path):
    target = tmp_path / "recording"
    shutil.copytree(FIXTURE, target)
    return target


def invoke(tmp_path, recording, output="health.json", media=True, *extra):
    args = [
        "--evidence",
        str(recording / "evidence"),
        "--trial",
        "1",
        "--output",
        str(tmp_path / output),
    ]
    if media:
        args += ["--media", str(recording / "media")]
    return run_cli(tmp_path, *args, *extra)


def edit(path, change):
    doc = json.loads(path.read_text())
    change(doc)
    path.write_text(json.dumps(doc))


def robot(recording, data=None):
    path = recording / "media/mcap/trial-01.robot.mcap"
    if data is None:
        with path.open("wb") as stream:
            writer = Writer(stream)
            writer.start()
            writer.finish()
    else:
        path.write_bytes(data)
    entry = {
        "path": "mcap/trial-01.robot.mcap",
        "bytes": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }

    def update(doc):
        doc["format"] = "livingproof-hallway-media/2.2.0"
        doc["trials"][0]["robot_mcap"] = entry

    edit(recording / "media/media.json", update)


def test_original_is_deterministic_through_cli(tmp_path, recording):
    for output in ["health.json", "again.json"]:
        result = invoke(tmp_path, recording, output)
        assert result.returncode == 0, result.stderr
    assert (tmp_path / "health.json").read_bytes() == (tmp_path / "again.json").read_bytes()
    doc = json.loads((tmp_path / "health.json").read_text())
    sim = doc["simulator"]
    assert sim["provenance"] == "simulator"
    assert sim["sample_count"] == 614
    assert sim["minimum_recorded_base_height_by_frame"] == {
        "world": {"height_m": 0.74637, "time_ns": "4440000000"}
    }
    assert (
        sim["source"]["sha256"]
        == "0acbf1037b64f4b3aceaac6a1fcd83fd5b8599943a10c2815a8e09ac636bbef4"
    )
    assert doc["health_version"] == "1.0.5"
    assert doc["robot"]["status"] == "robot stream not declared by this media version"
    assert "healthy" not in (tmp_path / "health.json").read_text()
    refused = invoke(tmp_path, recording)
    assert refused.returncode == 2  # no overwrite of an earlier result


def test_empty_robot_is_not_simulator_truth(tmp_path, recording):
    robot(recording)
    result = invoke(tmp_path, recording)
    assert result.returncode == 0, result.stderr
    doc = json.loads((tmp_path / "health.json").read_text())
    assert doc["robot"]["status"] == "no robot health telemetry"
    assert doc["robot"]["message_counts"] == {}
    assert "snapshots" not in doc["robot"]
    assert doc["simulator"]["sample_count"] == 614


@pytest.mark.parametrize("disabled", [False, True])
def test_missing_and_disabled_are_explicit(tmp_path, recording, disabled):
    result = invoke(
        tmp_path, recording, "health.json", False, *(["--media-disabled"] if disabled else [])
    )
    assert result.returncode == 0, result.stderr
    doc = json.loads((tmp_path / "health.json").read_text())
    assert doc["robot"]["status"] == ("media disabled" if disabled else "media missing")
    assert "snapshots" not in doc["simulator"]


def test_declared_missing_stream_is_explicit(tmp_path, recording):
    robot(recording)
    (recording / "media/mcap/trial-01.robot.mcap").unlink()
    result = invoke(tmp_path, recording)
    assert result.returncode == 0, result.stderr
    doc = json.loads((tmp_path / "health.json").read_text())
    assert doc["robot"]["status"] == "declared media file missing"


@pytest.mark.parametrize("data", [b"", b"not an MCAP", b"\x89MCAP0\r\n"])
def test_hash_matching_malformed_robot_is_rejected(tmp_path, recording, data):
    robot(recording, data)
    result = invoke(tmp_path, recording)
    assert result.returncode == 2, result.stderr
    assert not (tmp_path / "health.json").exists()


@pytest.mark.parametrize(
    "change",
    [
        lambda d: d.update(format="livingproof-hallway-media/9.0.0"),
        lambda d: d.update(run_id="different-run"),
        lambda d: d.update(configuration="different-config"),
        lambda d: d["trials"][0].update(index=2),
        lambda d: d["trials"].append(d["trials"][0].copy()),
        lambda d: d["trials"][0].update(observation_sha256="0" * 64),
        lambda d: d["trials"][0]["mcap"].update(sha256="0" * 64),
        lambda d: d["trials"][0]["mcap"].update(bytes=1),
        lambda d: d["trials"][0]["mcap"].update(path="../../outside"),
        lambda d: d["trials"][0]["mcap"].update(bytes=True),
        lambda d: d.update(format="livingproof-hallway-media/2.2.0"),
    ],
)
def test_bad_media_never_produces_result(tmp_path, recording, change):
    edit(recording / "media/media.json", change)
    result = invoke(tmp_path, recording)
    assert result.returncode == 2, result.stderr
    assert not (tmp_path / "health.json").exists()


def test_observation_hash_is_checked(tmp_path, recording):
    path = recording / "evidence/trials/trial-01.json"
    path.write_bytes(path.read_bytes() + b" ")
    result = invoke(tmp_path, recording)
    assert result.returncode == 2 and "Observation SHA-256 mismatch" in result.stderr
    assert not (tmp_path / "health.json").exists()


def test_all_selected_hashes_checked_before_decode(recording, monkeypatch):
    from livingproof_evaluator_health import evaluate as module

    robot(recording)
    edit(
        recording / "media/media.json",
        lambda d: d["trials"][0]["robot_mcap"].update(sha256="0" * 64),
    )

    def forbidden(*args):
        pytest.fail("Decoded before validating all selected media hashes")

    monkeypatch.setattr(module, "inspect_mcap", forbidden)
    with pytest.raises(ValueError, match="mismatch"):
        module.evaluate(recording / "evidence", recording / "media", 1)


def test_pinned_wheel_and_original_provenance():
    wheel = Path(__file__).parents[1] / "vendor/livingproof_health-1.0.5-py3-none-any.whl"
    assert hashlib.sha256(wheel.read_bytes()).hexdigest() == (
        "d1ce13c2b68e31855ac81a83b478f174182bf0ab4894d917b7e0dd406ba2857c"
    )
    provenance = json.loads((FIXTURE / "provenance.json").read_text())
    for relative, expected in provenance["files"].items():
        data = (FIXTURE / relative).read_bytes()
        assert hashlib.sha256(data).hexdigest() == expected["sha256"]
        assert len(data) == expected["bytes"]


def test_nonempty_robot_is_not_interpreted_as_simulator(tmp_path, recording):
    robot(recording, (recording / "media/mcap/trial-01.mcap").read_bytes())
    result = invoke(tmp_path, recording)
    assert result.returncode == 0, result.stderr
    doc = json.loads((tmp_path / "health.json").read_text())
    assert doc["robot"]["status"] == "robot messages present; health interpretation unsupported"
    assert "snapshots" not in doc["robot"]
    assert doc["robot"]["provenance"] == "robot"


@pytest.mark.parametrize("text", ['{"run_id":"a","run_id":"b"}', '{"run_id":NaN}', "[]"])
def test_malformed_manifest_refused(tmp_path, recording, text):
    (recording / "evidence/manifest.json").write_text(text)
    result = invoke(tmp_path, recording)
    assert result.returncode == 2
    assert not (tmp_path / "health.json").exists()


def test_symlink_escape_refused(tmp_path, recording):
    path = recording / "media/mcap/trial-01.mcap"
    external = tmp_path / "external.mcap"
    external.write_bytes(path.read_bytes())
    path.unlink()
    path.symlink_to(external)
    result = invoke(tmp_path, recording)
    assert result.returncode == 2 and "escapes" in result.stderr
    assert not (tmp_path / "health.json").exists()


def envelope(*records):
    import struct

    magic = b"\x89MCAP0\r\n"
    return (
        magic + b"".join(struct.pack("<BQ", op, len(body)) + body for op, body in records) + magic
    )


HEADER = (1, bytes(8))  # Empty profile and library strings.
DATA_END = (15, bytes(4))  # CRC omitted as permitted by MCAP.
FOOTER = (2, bytes(20))  # No optional summary or offsets.


@pytest.mark.parametrize(
    "records,reason",
    [
        ([HEADER, FOOTER], "DataEnd"),
        ([HEADER, HEADER, DATA_END, FOOTER], "Header"),
        ([HEADER, DATA_END, DATA_END, FOOTER], "DataEnd"),
        ([HEADER, (15, bytes(5)), FOOTER], "DataEnd"),
        ([HEADER, DATA_END, (5, bytes(22)), FOOTER], "wrong section"),
        ([HEADER, DATA_END, (6, bytes(40)), FOOTER], "wrong section"),
        ([HEADER, (11, bytes(46)), DATA_END, FOOTER], "before DataEnd"),
        ([HEADER, DATA_END, (14, bytes(17)), (3, bytes(14)), FOOTER], "wrong section"),
        ([HEADER, DATA_END, (3, bytes(14)), (4, bytes(16)), (3, bytes(14)), FOOTER], "grouped"),
        ([HEADER, DATA_END, (2, bytes(21))], "Footer length"),
        ([HEADER, (0, b""), DATA_END, FOOTER], "opcode zero"),
    ],
)
def test_structurally_malformed_robot_refused_by_installed_cli(
    tmp_path, recording, records, reason
):
    robot(recording, envelope(*records))  # Hash and size deliberately match malformed bytes.
    result = invoke(tmp_path, recording)
    assert result.returncode == 2, result.stderr
    assert reason in result.stderr
    assert not (tmp_path / "health.json").exists()


def test_valid_minimal_empty_robot_without_summary(tmp_path, recording):
    robot(recording, envelope(HEADER, DATA_END, FOOTER))
    result = invoke(tmp_path, recording)
    assert result.returncode == 0, result.stderr
    assert json.loads((tmp_path / "health.json").read_text())["robot"]["status"] == (
        "no robot health telemetry"
    )


def test_contradictory_statistics_rejected(tmp_path, recording):
    import struct

    robot(recording)
    path = recording / "media/mcap/trial-01.robot.mcap"
    data = bytearray(path.read_bytes())
    offset = 8
    while data[offset] != 11:
        offset += 9 + struct.unpack_from("<Q", data, offset + 1)[0]
    struct.pack_into("<Q", data, offset + 9, 1)  # Claims one message in an empty file.
    robot(recording, bytes(data))
    result = invoke(tmp_path, recording)
    assert result.returncode == 2 and "message count mismatch" in result.stderr
    assert not (tmp_path / "health.json").exists()
