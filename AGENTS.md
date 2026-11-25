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
Docker quickstart and product release automation requirements.
Documentation publication is authorized only through reviewed protected main. Use local Docker tooling
and the documented native CI fallback. No released product is claimed.
Settings, fleet registration, and board work are managed separately under #1.

Documentation follows the v9.9.12 documentation recipe with PR preview artifacts and protected-main Pages publication.
Use `docs:setup`, `docs:build`, and `docs:verify` through the same Task interfaces.
Do not claim the public manual is verified until post-merge deployment and
live checks pass. No product release is part of documentation publication. Current root/sibling manual links are navigation-only exceptions
to dependency pinning; executable inputs and shared guidance remain pinned.
