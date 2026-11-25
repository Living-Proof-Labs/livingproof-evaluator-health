# SPDX-License-Identifier: Apache-2.0
"""Section envelope checks missing from the pinned streaming reader.

MCAP specification: https://mcap.dev/spec#file-structure
This is a bounded top-level framing pass, not a payload/index decoder. Health
still owns field decoding, chunk expansion, resource accounting and data CRCs.
"""

import struct

from livingproof_health.bounds import MAGIC, check


def validate_sections(path, limits):
    size = path.stat().st_size
    check("input_bytes", size, limits)
    phase = "header"
    summary_start = offset_start = 0
    groups = set()
    last_group = None
    count = 0
    with path.open("rb") as stream:
        if stream.read(8) != MAGIC:
            raise ValueError("Invalid MCAP opening magic")
        while True:
            start = stream.tell()
            head = stream.read(9)
            if len(head) != 9:
                raise ValueError("MCAP requires a Footer after DataEnd")
            opcode, length = struct.unpack("<BQ", head)
            count += 1
            check("records", count, limits)
            check(
                "compressed_chunk_bytes" if opcode == 6 else "record_bytes",
                max(0, length - 44) if opcode == 6 else length,
                limits,
            )
            if length > size - stream.tell() - 8:
                raise ValueError("MCAP record exceeds file boundary")
            if opcode == 0:
                raise ValueError("Invalid MCAP opcode zero")
            if phase == "header":
                if opcode != 1:
                    raise ValueError("MCAP must begin with Header")
                phase = "data"
            elif opcode == 1:
                raise ValueError("Duplicate MCAP Header")
            elif opcode == 15:
                if phase != "data" or length != 4:
                    raise ValueError("MCAP requires exactly one four-byte DataEnd")
                phase = "summary"
            elif opcode == 2:
                if phase == "data":
                    raise ValueError("MCAP missing mandatory DataEnd")
                if length != 20:
                    raise ValueError("Invalid MCAP Footer length")
                declared_summary, declared_offsets, _ = struct.unpack("<QQI", stream.read(20))
                if (declared_summary, declared_offsets) != (summary_start, offset_start):
                    raise ValueError("MCAP Footer section offsets mismatch")
                if stream.read(8) != MAGIC or stream.read(1):
                    raise ValueError("Invalid MCAP closing magic or trailing bytes")
                return
            elif phase == "data":
                if opcode in (8, 10, 11, 13, 14):
                    raise ValueError("MCAP summary record before DataEnd")
            elif opcode == 14:
                if not offset_start:
                    offset_start = start
                phase = "offsets"
            else:
                if phase == "offsets" or opcode in (5, 6, 7, 9, 12):
                    raise ValueError("MCAP data/summary record in wrong section")
                if not summary_start:
                    summary_start = start
                if opcode != last_group:
                    if opcode in groups:
                        raise ValueError("MCAP summary records must be grouped by opcode")
                    groups.add(opcode)
                    last_group = opcode
            stream.seek(length, 1)
