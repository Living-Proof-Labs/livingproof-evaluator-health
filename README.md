# Living Proof Labs health evaluator

**Start here: [documentation source / preview instructions](docs/index.md).**
Build locally or download the PR preview until post-merge publication is verified.
The configured [Pages destination](https://docs.livingprooflabs.com/livingproof-evaluator-health/)
is not a claim that deployment has completed.

Deterministic standalone recorded-trial Health observations, tracked in
[#4](https://github.com/Living-Proof-Labs/livingproof-evaluator-health/issues/4).
The CLI validates trial bindings and media hashes before bounded replay with
immutable Health v1.0.5. It writes per-trial `health.json`, preserving simulator
and robot streams. It does not grade health or establish physical robot health.

```sh
uv run --locked python -m livingproof_evaluator_health \
  --evidence tests/fixtures/original-recording/evidence \
  --media tests/fixtures/original-recording/media --trial 1 --output health.json
```

See the [guide](docs/guide.md) for isolated installation, supported input contracts,
missing evidence, and reproduction limits.

## Development

On a Linux host with Docker Compose and Task 3.54.0:

```sh
export LOCAL_UID=$(id -u) LOCAL_GID=$(id -g)
task setup
task verify
docker compose run --rm tooling uv run --locked --no-sync python -m livingproof_evaluator_health --help
docker compose run --rm tooling uv run --locked --no-sync python -m livingproof_evaluator_health --version
```

Docker supplies Python 3.12.14, uv 0.12.23, and Task 3.54.0. The checkout is
mounted with your user ID; `.docker-venv` holds container dependencies separately
from a native `.venv`. Export the IDs above for all Docker tasks.

In an environment already providing those exact versions:

```sh
task -t Taskfile.runtime.yml setup
task -t Taskfile.runtime.yml verify
uv run --locked --no-sync python -m livingproof_evaluator_health --help
uv run --locked --no-sync python -m livingproof_evaluator_health --version
```

No arguments prints help successfully. Unsupported arguments fail with exit code 2.
Version comes from installed package metadata via hatch-vcs, as in the evaluator
siblings; before a release tag it is a development version. On a released tag,
the installed CLI reports that stable version. The shared semantic-release workflow
creates a GitHub Release and tag after verified protected-main
integration; only then is the versioned production manual built and deployed.
No PyPI package or container image is published. See the
[release and publication gate](docs/verification.md#publication-gate).

The package and `python -m` naming follow
[livingproof-evaluator-run](https://github.com/Living-Proof-Labs/livingproof-evaluator-run)
and [livingproof-evaluator-scenario](https://github.com/Living-Proof-Labs/livingproof-evaluator-scenario).
Their evaluator descriptors describe registered capabilities. This standalone CLI does
not advertise a discovery descriptor or register an evaluator capability.

See [CONTRIBUTING.md](CONTRIBUTING.md) for checks and verification limits.

## Documentation preview

Run `task docs:setup`, `task docs:build`, then `task docs:verify` with the Docker
user IDs above. In the prepared environment, add `-t Taskfile.runtime.yml`.
Open `artifacts/site/index.html`, or serve `artifacts/site` locally for search.
The docs workflow uploads PR review artifacts as `docs-SOURCE_SHA` for 14 days. See the
[guide](docs/guide.md) and [publication gate](docs/verification.md#publication-gate).
