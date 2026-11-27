# SPDX-License-Identifier: Apache-2.0
"""Names written on the advisory result. The implementation descriptor repeats them."""

from importlib.metadata import PackageNotFoundError, version
import re

EVALUATOR_ID = "livingproof-health"
DISPLAY_NAME = "Health"
PUBLISHER = "Living Proof Labs"
KIND = "advisory"
EXECUTION = "deterministic"
RESULT_FORMAT = "livingproof-evaluator-result/1.3.0"
TIER = "observation"
PACKAGE = "livingproof-evaluator-health"
PURPOSE = (
    "Recorded simulator posture and base height, separate from robot telemetry. "
    "Optional advisory observations; no effect on grade, Scenario or Run Integrity."
)
ICON = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">'
    '<path d="M4 12h3.2l1.6-4.2 2.4 8.4 1.6-4.2H20" stroke="currentColor" '
    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>'
)

# Contract evaluator.version is SemVer. hatch-vcs reports PEP 440 dev versions
# (1.1.3.devN) until a release tag exists; map those onto a SemVer pre-release.
_SEMVER = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)
_PEP440_DEV = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)(?:\.(0|[1-9]\d*))?\.dev(0|[1-9]\d*)$")


def package_version() -> str:
    try:
        raw = version(PACKAGE)
    except PackageNotFoundError:
        raw = "0.1.dev0"
    if _SEMVER.fullmatch(raw):
        return raw
    match = _PEP440_DEV.fullmatch(raw)
    if match:
        major, minor, patch, dev = match.groups()
        return f"{major}.{minor}.{patch or '0'}-dev.{dev}"
    return "0.1.0"
