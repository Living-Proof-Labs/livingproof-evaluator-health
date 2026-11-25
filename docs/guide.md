# Development guide

Use the source checkout with Docker Compose and Task 3.54.0 on Linux:

```sh
export LOCAL_UID=$(id -u) LOCAL_GID=$(id -g)
task setup
task verify
docker compose run --rm tooling uv run --locked --no-sync python -m livingproof_evaluator_health --help
docker compose run --rm tooling uv run --locked --no-sync python -m livingproof_evaluator_health --version
```

Help states that evaluation is not implemented. Version prints the installed
`livingproof-evaluator-health` development version. Unsupported arguments fail
with exit code 2 and do not create results. No trial data is needed or accepted.

The tooling image supplies Python 3.12.14, uv 0.12.23 and Task 3.54.0. Dependencies
are locked. Docker uses `.docker-venv`; native development uses `.venv`.

## Build and inspect the manual

```sh
task docs:setup
task docs:build
task docs:verify
```

Open `artifacts/site/index.html`. Relative `.html` links support inspection of the
downloaded artifact. For interactive search and navigation, serve that directory
with a local static server and open its index; an HTTP server is more reliable
than `file://` for browser search resources. In the prepared environment:

```sh
uv run --locked --no-sync python -m http.server 8765 --bind 127.0.0.1 --directory artifacts/site
```

Open `http://127.0.0.1:8765/`. This starts a local preview only.

In a prepared environment with the same Python, uv and Task versions, use
`task -t Taskfile.runtime.yml setup`, `verify`, `docs:setup`, `docs:build`, and
`docs:verify`. Run the detailed Taskfile directly inside the container; do not
invoke the host Docker wrappers recursively.

The PR's **Documentation preview** workflow builds the exact PR head and uploads
`docs-SOURCE_SHA`, retained for 14 days. Download and extract it, then inspect its
index and Version and source page. The preview has no live public URL.
