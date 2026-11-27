# SPDX-License-Identifier: Apache-2.0
"""Evaluate recorded trials or show the installed version."""

import argparse
from importlib.metadata import version
import json
from pathlib import Path
import sys

from mcap.exceptions import McapError

from .advisory import write_advisory
from .evaluate import evaluate


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m livingproof_evaluator_health",
        description=(
            "Deterministic recorded-trial Health observations. "
            "Simulator observations are not physical robot health proof. "
            "Pass an evidence manifest and --out to write an advisory result for every trial. "
            "Without media, that command exits 2 and writes nothing. "
            "Pass --evidence, --trial and --output to write one trial."
        ),
        epilog="Example: python -m livingproof_evaluator_health --version",
        allow_abbrev=False,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"livingproof-evaluator-health {version('livingproof-evaluator-health')}",
    )
    parser.add_argument(
        "evidence_manifest",
        nargs="?",
        type=Path,
        help="Evidence manifest.json. An advisory result then covers every trial",
    )
    parser.add_argument("--evidence", type=Path, help="Evidence directory containing manifest.json")
    media = parser.add_mutually_exclusive_group()
    media.add_argument("--media", type=Path, help="Directory containing media.json and MCAP files")
    media.add_argument(
        "--media-disabled",
        action="store_true",
        help="Explicit caller declaration: recording disabled",
    )
    parser.add_argument("--trial", type=int, help="Declared positive trial index")
    parser.add_argument(
        "--output", type=Path, help="New per-trial health.json path (never overwrites)"
    )
    parser.add_argument(
        "--out",
        type=Path,
        help="New advisory result path. Writes health.json beside it and never overwrites",
    )
    args = parser.parse_args(argv)
    advisory = args.evidence_manifest is not None or args.out is not None
    legacy = any((args.evidence is not None, args.trial is not None, args.output is not None))
    if not any((advisory, legacy, args.media is not None, args.media_disabled)):
        parser.print_help()
        return 0
    if advisory and legacy:
        parser.error(
            "pass either the evidence manifest and --out, or --evidence, --trial and --output"
        )
    if advisory and (args.evidence_manifest is None or args.out is None):
        parser.error("an advisory result requires the evidence manifest and --out")
    if not advisory and (
        args.evidence is None or args.trial is None or args.trial < 1 or args.output is None
    ):
        parser.error("--evidence, positive --trial and --output are required")
    if advisory and args.media is None:
        # One line, with no argparse usage text, so a loader that maps exit 2 to
        # refused keeps this sentence as the refusal reason.
        reason = "media disabled" if args.media_disabled else "media missing"
        print(f"Health was not run: {reason}.", file=sys.stderr)
        return 2
    try:
        if advisory:
            write_advisory(args.evidence_manifest, args.media, args.out, args.media_disabled)
        else:
            result = evaluate(args.evidence, args.media, args.trial, args.media_disabled)
            content = (
                json.dumps(result, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
            )
            with args.output.open("x", encoding="utf-8") as stream:
                stream.write(content)
    except (ValueError, OSError, KeyError, TypeError, RecursionError, McapError) as error:
        print(f"health: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
