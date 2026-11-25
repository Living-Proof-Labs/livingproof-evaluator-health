# Verification

The CLI checks exercise installed help, version, no arguments and unsupported
input through subprocesses. They establish scaffold behavior only. They are not
robot-health tests, and no robot quality or safety conclusion follows from them.
No line coverage or capability coverage percentage is claimed.

Documentation generation runs the real CLI help and Task information commands.
The build downloads the shared brand from its locked commit and checks SHA-256.
The render check verifies the landing page, local links and fragments, shared
branding, generated references and source identity. A build needs network access
to the pinned brand; link and fragment checks are local and offline.

Run `task verify`, then `task docs:setup`, `task docs:build`, and
`task docs:verify`. Native equivalents use `-t Taskfile.runtime.yml`.
Linux amd64 is the initial supported verification environment. Arm64, macOS,
Windows and hosted development containers need separate verification.

## Publication gate

The docs workflow is triggered only by `pull_request`, with `contents: read`.
It uploads an ordinary review artifact for 14 days. It has no `push` or dispatch
trigger, Pages artifact, release job, deployment environment, `pages: write`, or
`id-token: write`. It cannot publish this manual from the PR or after merge.

The adopted recipe and brand are collaboration-guidelines v9.9.12, resolved to
`9874b85df12230b390cb8c7381bc7e97ffd36d62`. Zensical and the generation/check
pattern follow the evaluator siblings. Shared `manual-build.yml` and
`deploy-manual.yml` assume release-bound plans and repository-specific sealing
tools; `generated-docs.yml` assumes the shared template's report paths. This
scaffold therefore uses the siblings' local build workflow and pinned standard
Actions without invoking those release/deploy workflows.

Publication requires separate authorization and review: choose the release and
artifact identity contract, wire the appropriate deployment gate, verify the
live manual and only then update README and central directory destinations.
This change does not activate the central publisher or modify repository settings.
Current rendered-manual links are navigation aids, not dependency pins.

Independent review, hosted artifact presentation, and live desktop/mobile/search
verification remain separate from the local build checks. Historical manuals are
not published by this scaffold.
