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
arm64 runtime support. No release or deployment is configured.

Before merge, obtain the required independent verification of the documented
user commands and record the exact head, CI run, result counts and remaining gaps.
