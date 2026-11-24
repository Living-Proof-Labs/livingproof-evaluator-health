# Living Proof Labs health evaluator

Initial package and command-line scaffold. Health evaluation is not implemented.
The CLI accepts help and version options only; it reads no trial data and produces
no evaluation results. Work is tracked in [#1](https://github.com/Living-Proof-Labs/livingproof-evaluator-health/issues/1).

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
siblings; before a release tag it is a development version. There is no published
package, image, product release, or deployed manual in this scaffold.

The package and `python -m` naming follow
[livingproof-evaluator-run](https://github.com/Living-Proof-Labs/livingproof-evaluator-run)
and [livingproof-evaluator-scenario](https://github.com/Living-Proof-Labs/livingproof-evaluator-scenario).
Their evaluator descriptors describe implemented capabilities. This scaffold does
not advertise a discovery descriptor or register an evaluator capability.

See [CONTRIBUTING.md](CONTRIBUTING.md) for checks and verification limits.
