# SPDX-License-Identifier: Apache-2.0
"""Exercise the workflow's actual guard and served-manual verification failures."""

import functools
import hashlib
import json
import os
import subprocess
import tempfile
import threading
import unittest
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import yaml

from smoke import check

SHA = "a" * 40


class PublicationTest(unittest.TestCase):
    def test_workflow_and_guard(self):
        workflow = yaml.load(Path(".github/workflows/docs.yml").read_text(), Loader=yaml.BaseLoader)
        expected = (
            "github.ref == 'refs/heads/main' && "
            "(github.event_name == 'push' || github.event_name == 'workflow_dispatch')"
        )
        self.assertEqual(set(workflow["on"]), {"pull_request", "push", "workflow_dispatch"})
        self.assertEqual(workflow["on"]["push"]["branches"], ["main"])
        self.assertEqual(workflow["permissions"], {"contents": "read"})
        self.assertEqual(workflow["concurrency"]["cancel-in-progress"], "false")
        deploy = workflow["jobs"]["deploy"]
        self.assertEqual(deploy["if"], expected)
        self.assertEqual(deploy["needs"], "build")
        steps = deploy["steps"]
        guard = steps[1]
        self.assertEqual(guard["name"], "Require current protected main")
        self.assertTrue(steps[2]["uses"].startswith("actions/deploy-pages@"))
        uploads = workflow["jobs"]["build"]["steps"]
        pages = [
            s for s in uploads if s.get("uses", "").startswith("actions/upload-pages-artifact@")
        ]
        self.assertEqual(len(pages), 1)
        self.assertEqual(pages[0]["if"], expected)
        for event, ref, protected, response, api_exit, succeeds in (
            ("push", "main", "true", SHA + "\ttrue", 0, True),
            ("workflow_dispatch", "main", "true", SHA + "\ttrue", 0, True),
            ("pull_request", "main", "true", SHA + "\ttrue", 0, False),
            ("workflow_dispatch", "feature", "true", SHA + "\ttrue", 0, False),
            ("push", "main", "false", SHA + "\ttrue", 0, False),
            ("push", "main", "true", SHA + "\tfalse", 0, False),
            ("push", "main", "true", "b" * 40 + "\ttrue", 0, False),
            ("push", "main", "true", "", 0, False),
            ("push", "main", "true", "", 1, False),
        ):
            with self.subTest(event=event, ref=ref, response=response):
                with tempfile.TemporaryDirectory() as directory:
                    gh = Path(directory) / "gh"
                    gh.write_text('#!/bin/sh\nprintf "%s\\n" "$MOCK_RESPONSE"\nexit "$MOCK_EXIT"\n')
                    gh.chmod(0o755)
                    result = subprocess.run(
                        ["bash", "-c", guard["run"]],
                        env={
                            **os.environ,
                            "PATH": directory + ":" + os.environ["PATH"],
                            "GITHUB_REF": "refs/heads/" + ref,
                            "GITHUB_EVENT_NAME": event,
                            "GITHUB_REF_PROTECTED": protected,
                            "GITHUB_SHA": SHA,
                            "GITHUB_REPOSITORY": "example/repo",
                            "MOCK_RESPONSE": response,
                            "MOCK_EXIT": str(api_exit),
                        },
                        capture_output=True,
                    )
                    self.assertEqual(result.returncode == 0, succeeds, result.stderr)

    def test_served_manual(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "manual"
            (root / "assets").mkdir(parents=True)
            brand = b"/* test brand */"
            (root / "assets/brand.css").write_bytes(brand)
            identity = {
                "source_commit": SHA,
                "source_dirty": False,
                "brand": {"sha256": hashlib.sha256(brand).hexdigest()},
            }
            (root / "build.json").write_text(json.dumps(identity))
            for page, text in [
                ("index", "Health evaluator scaffold"),
                ("reference", "--version"),
                ("version", SHA),
            ]:
                (root / f"{page}.html").write_text(
                    '<link rel="stylesheet" href="assets/brand.css">' + text
                )
            handler = functools.partial(SimpleHTTPRequestHandler, directory=directory)
            server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                url = f"http://127.0.0.1:{server.server_port}/manual/"
                check(url, SHA)
                with self.assertRaisesRegex(ValueError, "stale or dirty"):
                    check(url, "b" * 40)
                identity["source_dirty"] = True
                (root / "build.json").write_text(json.dumps(identity))
                with self.assertRaisesRegex(ValueError, "stale or dirty"):
                    check(url, SHA)
                identity["source_dirty"] = False
                (root / "build.json").write_text(json.dumps(identity))
                (root / "assets/brand.css").write_bytes(b"changed")
                with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                    check(url, SHA)
                (root / "assets/brand.css").unlink()
                with self.assertRaises(OSError):
                    check(url, SHA)
            finally:
                server.shutdown()
                server.server_close()
                thread.join()
