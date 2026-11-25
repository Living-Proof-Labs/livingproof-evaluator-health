# Contributing

Keep changes small and link the tracking issue in the pull request. Use a feature
branch and conventional commit messages. Follow [AGENTS.md](AGENTS.md), including
its explicit scaffold exceptions. Scope or settings changes belong in separate work.

Run the setup and verification commands in the README before requesting review.
`task check` runs Ruff lint and formatting checks. `task test` exercises the
installed module through subprocesses: help, no arguments, installed version, and
rejected unsupported input without creating files. Reports go to
`artifacts/tests.xml`; CI retains them for 14 days and publishes individual cases
through GitHub Checks for same-repository pull requests. Forks retain artifacts
but cannot publish Checks with a read-only token.

CI uses the documented native fallback until image publication is separately
scoped. Only Linux amd64 is initially verified; arm64, macOS, Windows, hosted
development containers, and CI report presentation require separate verification.
The Dockerfile includes amd64 and arm64 Task binaries but that does not establish
arm64 runtime support. The scaffold release uses shared semantic-release after verification of protected main.
Production documentation requires that published release.

Before merge, obtain the required independent verification of the documented
user commands and record the exact head, CI run, result counts and remaining gaps.

For documentation changes run `task docs:setup`, `task docs:build`, and
`task docs:verify` (native: add `-t Taskfile.runtime.yml`). Edit authored pages in
`docs/`; CLI/Task reference, contribution page, license and identity are generated.
Do not edit `artifacts/` or copy the shared brand into this repository. Pin brand
version, resolved commit and checksum together. Preview artifacts last 14 days;
publication runs only after review and merge to protected main. Run `task docs:test`
for the deployment guard and smoke checker tests.

Use a release-worthy Conventional Commit PR title (`feat:`, `fix:`, or the shared
maintenance types) so the verified merge creates a real release. Do not select a
stable version manually. PR candidates use the shared SemVer and Python versions;
main verification artifacts are unversioned and cannot be deployed. The production
build installs the tagged checkout without a version override and checks the real CLI.
