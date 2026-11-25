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

The Documentation workflow keeps PR review artifacts for 14 days. It also runs
on pushes to main and manual dispatch. Only main push/dispatch runs can upload
Pages artifacts or enter deployment. The deployment job alone receives
`pages: write` and `id-token: write`, uses the `github-pages` environment, and
requires both GitHub's protected-ref context and live branch protection.
It rejects a stale SHA or API failure immediately before deploying the same-run
Pages artifact. Runs are serialized without cancelling an active deployment.
PR code and feature-branch dispatches cannot enter the deployment job.

`task docs:test` exercises the actual workflow shell guard with current, stale,
unprotected, missing and failing API responses, as well as PR and feature-branch
contexts. It also tests the served-manual smoke checker against local HTTP
fixtures, including stale/dirty identity, changed brand and missing assets.

After independent review and merge to protected main:

1. The **Documentation** main-push run installs locked tools, runs CLI checks,
   publication tests, builds the manual, and checks rendered links and identity.
2. It retains a review artifact and uploads the same built site for Pages.
3. The deployment guard requires the run's SHA to equal current protected main.
   `actions/deploy-pages` publishes through the existing Pages configuration.
4. The live smoke step checks the deployment URL for the exact clean commit,
   landing page, CLI reference, version page, CSS/JavaScript and brand checksum.
   Six attempts allow brief Pages propagation; failure keeps the workflow red.
5. Independently verify README-to-manual navigation, mobile/keyboard use,
   search and a deep link. Update the README start-here destination only after
   the live result is verified. No central publisher activation is included.

Retry a failed publication with **Run workflow**, selecting **main**; feature
branches are refused. A stale run cannot republish over newer main. A new main
commit arriving after the final guard is a remaining deployment race; the newer
serialized workflow must finish before claiming current-main publication.

For a manual live smoke check in a prepared environment:

```sh
task -t Taskfile.runtime.yml docs:smoke -- --url https://docs.livingprooflabs.com/livingproof-evaluator-health/ --commit FULL_MERGED_SHA
```

Repository settings are not changed here. Main must already be protected before
publication; missing protection is an explicit deployment blocker. A failed live
smoke does not roll back Pages automatically. Inspect the deployed identity and
repair through reviewed main or rerun current main after transient propagation.

This adopts the scenario evaluator's Pages path with pinned Actions and adds
protected-main and live smoke gates. Shared release-bound workflows are not
invoked: a development manual must not create an unrelated product release.
The recipe and shared brand stay pinned to collaboration-guidelines v9.9.12.
Current rendered-manual links are navigation aids, not dependency pins.
