# SPDX-License-Identifier: Apache-2.0
"""Exercise the installed entry point from outside the source checkout."""

import subprocess
import sys
from importlib.metadata import version

import pytest


def run_cli(tmp_path, *args):
    return subprocess.run(
        [sys.executable, "-m", "livingproof_evaluator_health", *args],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=10,
    )


@pytest.mark.parametrize("args", [[], ["--help"], ["-h"]])
def test_help_explains_scaffold(tmp_path, args):
    result = run_cli(tmp_path, *args)
    assert result.returncode == 0
    assert "Health evaluation is not implemented" in " ".join(result.stdout.split())
    assert "python -m livingproof_evaluator_health --version" in result.stdout
    assert not result.stderr
    assert list(tmp_path.iterdir()) == []


def test_version_matches_installed_package(tmp_path):
    result = run_cli(tmp_path, "--version")
    assert result.returncode == 0
    assert result.stdout.strip() == (
        f"livingproof-evaluator-health {version('livingproof-evaluator-health')}"
    )
    assert not result.stderr
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("args", [["trial.json"], ["--out", "result.json"], ["--ver"]])
def test_unsupported_input_fails_without_output_files(tmp_path, args):
    result = run_cli(tmp_path, *args)
    assert result.returncode == 2
    assert "unrecognized arguments" in result.stderr
    assert "usage: python -m livingproof_evaluator_health" in result.stderr
    assert not result.stdout
    assert list(tmp_path.iterdir()) == []
