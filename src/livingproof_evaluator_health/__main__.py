# SPDX-License-Identifier: Apache-2.0
"""Evaluate one recorded trial or show the installed version."""

import argparse
from importlib.metadata import version
import json
from pathlib import Path
import sys

from mcap.exceptions import McapError

from .evaluate import evaluate


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m livingproof_evaluator_health",
        description=(
            "Deterministic recorded-trial Health observations. "
            "Simulator observations are not physical robot health proof."
        ),
        epilog="Example: python -m livingproof_evaluator_health --version",
        allow_abbrev=False,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"livingproof-evaluator-health {version('livingproof-evaluator-health')}",
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
    args = parser.parse_args(argv)
    if not any(
        (args.evidence, args.media, args.media_disabled, args.trial is not None, args.output)
    ):
        parser.print_help()
        return 0
    if args.evidence is None or args.trial is None or args.trial < 1 or args.output is None:
        parser.error("--evidence, positive --trial and --output are required")
    try:
        result = evaluate(args.evidence, args.media, args.trial, args.media_disabled)
        content = json.dumps(result, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
        with args.output.open("x", encoding="utf-8") as stream:
            stream.write(content)
    except (ValueError, OSError, KeyError, TypeError, RecursionError, McapError) as error:
        print(f"health: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
