# SPDX-License-Identifier: Apache-2.0
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from identity import validate

SHA = "a" * 40


class IdentityTest(unittest.TestCase):
    def test_preview_uniqueness_and_refusals(self):
        versions = set()
        for run_id, run, attempt in [(10, 1, 1), (10, 1, 2), (11, 2, 1)]:
            # Examples of the pinned shared workflow's outputs, not a version selector.
            package = f"1.2.3.dev{run}{run_id:020d}{attempt:020d}"
            env = dict(
                DOCS_KIND="candidate",
                MANUAL_VERSION=f"1.2.3-pr.4.{run}.{attempt}",
                PR_NUMBER="4",
                GITHUB_RUN_NUMBER=str(run),
                GITHUB_RUN_ID=str(run_id),
                GITHUB_RUN_ATTEMPT=str(attempt),
                CANDIDATE_PACKAGE_VERSION=package,
                CANDIDATE_COMMIT=SHA,
            )
            versions.add(validate(SHA, False, "0.1.dev1", env)["version"])
            with self.assertRaises(ValueError):
                validate(SHA, False, package, {**env, "GITHUB_RUN_ATTEMPT": "9"})
            with self.assertRaises(ValueError):
                validate(SHA, True, package, env)
        self.assertEqual(len(versions), 3)

    def test_released_identity(self):
        env = dict(
            DOCS_KIND="release",
            MANUAL_VERSION="1.2.3",
            RELEASE_VERSION="1.2.3",
            RELEASE_TAG="v1.2.3",
            RELEASE_COMMIT=SHA,
        )
        self.assertEqual(validate(SHA, False, "1.2.3", env, SHA)["release_tag"], "v1.2.3")
        for version, dirty, target in [
            ("1.2.3.dev1", False, SHA),
            ("1.2.3", True, SHA),
            ("1.2.3", False, "b" * 40),
        ]:
            with self.assertRaises(ValueError):
                validate(SHA, dirty, version, env, target)
        self.assertEqual(validate(SHA, False, "0.1.dev1", {})["version"], "development")
        with self.assertRaises(ValueError):
            validate(SHA, False, "1.2.3", {"MANUAL_VERSION": "1.2.3"})

    def test_tagged_fixture_real_cli(self):
        # Isolated fixture only: no tag is added to this checkout or any remote.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for file in ("pyproject.toml", "README.md", "LICENSE"):
                shutil.copy(file, root / file)
            shutil.copytree("src", root / "src", ignore=shutil.ignore_patterns("__pycache__"))

            def run(*args, **kwargs):
                return subprocess.check_output(
                    args, cwd=root, text=True, stderr=subprocess.STDOUT, **kwargs
                ).strip()

            run("git", "init", "-q")
            run("git", "add", ".")
            run(
                "git",
                "-c",
                "user.name=Fixture",
                "-c",
                "user.email=fixture@example.invalid",
                "commit",
                "-qm",
                "feat: fixture",
            )
            run("git", "tag", "v1.2.3")
            env = {
                k: v
                for k, v in os.environ.items()
                if not k.startswith("SETUPTOOLS_SCM_PRETEND_VERSION")
            }
            run("uv", "build", "--wheel", env=env)
            run("uv", "venv", "--python", sys.executable, str(root / "env"))
            python = str(root / "env/bin/python")
            wheel = next((root / "dist").glob("*.whl"))
            run("uv", "pip", "install", "--python", python, str(wheel))
            self.assertEqual(
                run(python, "-m", "livingproof_evaluator_health", "--version"),
                "livingproof-evaluator-health 1.2.3",
            )
            self.assertIn(
                "Health evaluation is not",
                run(python, "-m", "livingproof_evaluator_health", "--help"),
            )
