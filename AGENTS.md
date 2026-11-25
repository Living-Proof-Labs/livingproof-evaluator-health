# Agent instructions

<!-- renovate: guidelines -->
Read and apply [collaboration-guidelines v9.9.12](https://github.com/Living-Proof-Labs/collaboration-guidelines/blob/v9.9.12/AGENTS.md)
and relevant procedures at that tag before work. Adoption resolved to
`9874b85df12230b390cb8c7381bc7e97ffd36d62`.

## Local additions

Use `task setup` and `task verify` with Docker, or `task -t Taskfile.runtime.yml`
in a prepared environment. Keep issue #1 limited to package, CLI and documentation scaffolding.
Do not add health evaluation, real-data handlers, result reports or verdicts.

## Local overrides

For this initial scaffold, defer the shared published tooling image, released
Docker quickstart requirements. The scaffold release automation is required by issue #3.
Documentation publication is authorized only through reviewed protected main. Use local Docker tooling
and the documented native CI fallback. No evaluator functionality is implied by a scaffold release.
Settings, fleet registration, and board work are managed separately under #1.

Documentation follows the v9.9.12 documentation recipe with PR preview artifacts and protected-main Pages publication.
Use `docs:setup`, `docs:build`, and `docs:verify` through the same Task interfaces.
Do not claim the public manual is verified until post-merge deployment and
live checks pass. The shared semantic-release writer must publish the stable scaffold release before any production manual build. Current root/sibling manual links are navigation-only exceptions
to dependency pinning; executable inputs and shared guidance remain pinned.

Aaron's [release-first decision](https://github.com/Living-Proof-Labs/collaboration-guidelines/issues/153#issuecomment-7114173447)
overrides the older sealed-artifact ordering in v9.9.12 release guidance:
verification gates release, then production uses the actual released version/tag/commit.
Use the pinned shared candidate workflow for unique PR versions. Never hand-tag,
merge, publish or alter settings as part of implementing or reviewing this change.
