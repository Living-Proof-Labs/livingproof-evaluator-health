# SPDX-License-Identifier: Apache-2.0
"""Show help and the installed scaffold version."""

import argparse
from importlib.metadata import version


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m livingproof_evaluator_health",
        description=(
            "Living Proof Labs health evaluator scaffold. "
            "Health evaluation is not implemented; no data inputs are accepted."
        ),
        epilog="Example: python -m livingproof_evaluator_health --version",
        allow_abbrev=False,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"livingproof-evaluator-health {version('livingproof-evaluator-health')}",
    )
    parser.parse_args(argv)
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
