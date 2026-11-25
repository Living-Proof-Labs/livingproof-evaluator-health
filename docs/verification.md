# Verification

The subprocess tests reproduce the retained original G1 corner MCAP independently
through the installed CLI: 614 simulator base-pose samples, minimum 0.74637 m at
4440000000 ns in world frame, byte-identical results on repetition. Fixture
provenance and hashes are retained under `tests/fixtures/original-recording` and
verified in tests. The rounded observation summary is not used to compute this.

A separate synthetic media 2.2 case pairs the original simulator fixture with a
valid empty robot MCAP. It reports `no robot health telemetry` while retaining
simulator observations separately. Refusal tests cover malformed MCAP even when
its declared hash matches, identity/hash/size mismatches, unsafe paths, unknown
formats and duplicate trials. Missing/disabled evidence is explicit. Tests also
verify that all selected declared hashes are checked before any MCAP decoding.
Installed-CLI regressions reject a hash-matching robot file with no mandatory
DataEnd, duplicate/misordered records and contradictory Statistics, leaving no new
output. Valid empty files with and without optional summary remain accepted.
The clean-wheel check separately repeats missing-DataEnd refusal and genuine
empty telemetry alongside the unchanged original known answer.
These are recorded-observation tests, not robot quality or safety conclusions.

The 21,917-byte immutable Health v1.0.5 wheel is retained unchanged under `vendor/`
and checked against the upstream GitHub asset digest and SHA-256
`d1ce13c2b68e31855ac81a83b478f174182bf0ab4894d917b7e0dd406ba2857c`.
The candidate is clean-installed from its built wheel into a separate environment
with that upstream wheel. The actual immutable evaluator release installation
and fixture replay remain a post-review/post-merge gate; a draft PR cannot prove
that future release. No coverage percentage or hardware claim is made.

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

Aaron's [release-first decision](https://github.com/Living-Proof-Labs/collaboration-guidelines/issues/153#issuecomment-7114173447)
sets the order: verification, stable GitHub Release and tag, production build,
then artifact-only Pages deployment. This replaces the older sealed/forecast
ordering in adopted guidelines v9.9.12. Both shared workflows remain pinned to
that released version, resolving to `9874b85df12230b390cb8c7381bc7e97ffd36d62`.

The read-only candidate job calls `semantic-release-candidate.yml` for PRs to main.
Its SemVer includes PR number, workflow run number and attempt; its Python version
also includes run ID. The manual records the run ID and attempt alongside source
identity. A rerun has a different candidate version. These supplied versions label
PR artifacts only; they never create a tag or deploy. The shared Python candidate value is recorded as `candidate_package_version`,
separately from the installed source package version. Its long development number
exceeds uv 0.12.23's numeric version limit; no candidate Python package is built
or published here. The preview manual uses the shared unique SemVer unchanged.
The production CLI uses the genuine stable tag without any version override. Queue and main verification builds remain
labelled development, with no stable-version claim.

Both **CLI verification** and **Documentation verification** run for PRs and
`merge_group: checks_requested`. The latter also exercises strict release identity,
workflow permission boundaries and the real CLI installed from a wheel built from
an isolated tagged fixture. Fixture tags never touch the source repository or a remote.

After independent review and merge to protected main:

1. The **Documentation** main-push run verifies the CLI, publication tests and
   unversioned documentation. The current protected-main guard gates release.
2. The pinned `semantic-release.yml` writer selects the version, creates the tag
   and GitHub Release, and returns version, tag, commit and publication status.
   It receives no forecast `expected-version` and does not publish packages/images.
3. Only `published == 'true'` enables production. Before checkout or build, an
   authenticated check verifies stable version/tag correspondence, the tag's
   resolved commit, a published non-draft/non-prerelease GitHub Release and
   current protected main. Missing, mismatched or superseded releases fail closed.
4. Production checks out that exact commit with tags, installs without a candidate
   override, runs the actual CLI help/version and requires its version to match
   the release. The manual records the stable version, tag and exact commit.
5. The privileged deployment job repeats the release/current-main checks inside
   the workflow's serialization, then deploys the same-run Pages artifact. It
   never checks out or executes project code. Its URL is passed to a separate
   read-only smoke job, which checks exact source and release/package identity,
   landing/reference/version pages and served assets/brand checksum.

PRs and merge groups cannot release or deploy. When semantic-release reports no
release, production, deployment and smoke skip; verification does not become a
stable artifact. A stale run cannot intentionally republish over current main.
Main advancing after the final guard remains a race; require the newest serialized
run to complete before claiming current-main publication.

There is no manual dispatch or hand-tag fallback. If a transient failure happens,
review the release state and rerun the same current-main workflow; the shared
writer owns existing-tag recovery and refuses ambiguous tag state. Do not retag.
A no-release rerun must not deploy an old manual. A release-worthy Conventional
Commit title makes the normal first verified merge eligible for the first release.
The actual writer permission and first release are verified only after merge.

For a live check after publication:

```sh
task -t Taskfile.runtime.yml docs:smoke -- --url https://docs.livingprooflabs.com/livingproof-evaluator-health/ --commit RELEASE_COMMIT --version RELEASE_VERSION
```

Independent verification must check the genuine Release/tag, installed CLI version,
live version/source identity, navigation, search and mobile/keyboard use. A smoke
failure keeps the workflow red but does not automatically roll back Pages.

## Merge queue checks

Require **CLI verification** and **Documentation verification**, GitHub Actions
integration ID `15368`, through the central policy process. Queue runs use the
combined `github.sha`; actual queue execution must show both checks passing on
that SHA, enforcement of missing/failing checks, and skipped release/publication.
Do not require release, production, deploy or Published documentation smoke for
queue admission. Repository settings and queue admission are managed separately.
