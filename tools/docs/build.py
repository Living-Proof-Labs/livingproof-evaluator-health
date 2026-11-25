# SPDX-License-Identifier: Apache-2.0
"""Stage authored docs and executable references using the evaluator sibling pattern."""

import hashlib
import json
import shutil
import subprocess
import sys
from importlib.metadata import version
from pathlib import Path
from urllib.request import urlopen

REPO = "https://github.com/Living-Proof-Labs/livingproof-evaluator-health"


def output(*args):
    return subprocess.check_output(args, text=True).strip()


stage = Path("artifacts/docs-source")
if stage.exists():
    shutil.rmtree(stage)
shutil.copytree("docs", stage)
lock = json.loads(Path("docs-brand.lock.json").read_text())
url = f"https://raw.githubusercontent.com/{lock['repository']}/{lock['commit']}/{lock['path']}"
with urlopen(url, timeout=30) as response:
    brand = response.read()
if hashlib.sha256(brand).hexdigest() != lock["sha256"]:
    raise SystemExit("Shared brand checksum mismatch")
(stage / "assets").mkdir()
(stage / "assets/brand.css").write_bytes(brand)
sha = output("git", "rev-parse", "HEAD")
identity = {
    "source_commit": sha,
    "source_dirty": bool(output("git", "status", "--porcelain")),
    "package_version": version("livingproof-evaluator-health"),
    "docs_status": "development preview; not published",
    "brand": lock,
}
(stage / "build.json").write_text(json.dumps(identity, indent=2) + "\n")
(stage / "version.md").write_text(
    "# Version and source\n\n"
    f"Docs: development · [{sha[:12]}]({REPO}/tree/{sha})\n\n"
    f"Full source commit: `{sha}`. Uncommitted changes: `{identity['source_dirty']}`.\n\n"
    f"Installed package metadata: `{identity['package_version']}`; this is not a release claim.\n\n"
    "This manual is a local or pull-request preview. No live or historical manual is "
    "published. Source history remains available in the "
    f"[repository]({REPO}).\n\n"
    "[Machine-readable build identity](build.json). Only clean CI artifacts identify "
    "the exact committed content; dirty local builds include uncommitted work.\n\n"
    f"Shared brand: {lock['version']} at `{lock['commit']}`, verified by SHA-256.\n"
)
help_text = output(sys.executable, "-m", "livingproof_evaluator_health", "--help")
reference = "# Reference\n\n## Commands\n\nGenerated from the installed module's native help.\n\n"
reference += f"```text\n{help_text}\n```\n\n"
reference += "No arguments prints help; unsupported arguments exit with code 2. No data is read.\n"
for taskfile, heading in [
    ("Taskfile.yml", "Host tasks"),
    ("Taskfile.runtime.yml", "Prepared environment tasks"),
]:
    reference += f"\n## {heading}\n\nGenerated from `{taskfile}` using native Task summaries.\n"
    tasks = json.loads(output("task", "-t", taskfile, "--list", "--json"))["tasks"]
    for task in tasks:
        summary = output("task", "-t", taskfile, task["name"], "--summary")
        reference += f"\n### {heading}: {task['name']}\n\n```text\n{summary}\n```\n"
(stage / "reference.md").write_text(reference)
# Contribution instructions remain canonical in the repository root.
(stage / "contribute.md").write_text(
    Path("CONTRIBUTING.md")
    .read_text()
    .replace("[AGENTS.md](AGENTS.md)", f"[AGENTS.md]({REPO}/blob/{sha}/AGENTS.md)")
)
(stage / "license.md").write_text(
    "# License\n\nRepository content is Apache-2.0. The shared brand retains its "
    "upstream license notice.\n\n```text\n" + Path("LICENSE").read_text() + "\n```\n"
)
