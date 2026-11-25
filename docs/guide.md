# Development guide

Use the source checkout with Docker Compose and Task 3.54.0 on Linux:

```sh
export LOCAL_UID=$(id -u) LOCAL_GID=$(id -g)
task setup
task verify
docker compose run --rm tooling uv run --locked --no-sync python -m livingproof_evaluator_health --help
docker compose run --rm tooling uv run --locked --no-sync python -m livingproof_evaluator_health --version
```

Version prints the installed evaluator version. Run one trial:

```sh
uv run --locked python -m livingproof_evaluator_health \
  --evidence tests/fixtures/original-recording/evidence \
  --media tests/fixtures/original-recording/media --trial 1 --output health.json
```

The output path must not already exist. Repeating with a different output path
produces identical bytes for identical inputs and installed versions. Invalid
inputs return exit 2 without a new result. Omit `--media` for explicit missing
media, or pass `--media-disabled` for an explicit caller declaration that recording
was disabled; this flag is not an independently verified producer fact.

## Supported input and limits

The CLI reads evidence `manifest.json` (livingproof-hallway-evidence/2.0.0),
the selected hashed route observation (livingproof-route-observation/0.1.0),
and, when media is supplied, `run-manifest.json` (livingproof-run-manifest/0.1).
It validates the fields needed for trial/run/configuration identity and simulator
provenance, not every field of the wider evidence specification. Media versions
2.0.0, 2.1.0 and 2.2.0 are supported. Selected declared streams must have relative
confined paths, byte counts and SHA-256; all present selected files are hashed
and frozen before any MCAP decode. Duplicate trial indices/JSON keys, unknown
formats, malformed inputs and mismatched identities/hashes are refused.

JSON documents are capped at 4 MiB. MCAP uses Health's default resource limits
(128 MiB input, 8 MiB expanded chunk, 20,000 snapshots, bounded framing and CRC
checks). No CLI option raises those limits. Only `/base_pose` with upstream
foxglove.PoseInFrame JSON is interpreted, in metres. Output retains snapshots,
per-frame sampled minima, unavailable pose counts, versions, hashes and trial
identity. Equal minima choose the first timestamp in stable replay order.

Media 2.2's `robot_mcap` is separate from simulator `mcap`. A structurally valid
empty robot recording produces `no robot health telemetry`. Nonempty robot
streams produce an explicit unsupported-interpretation status and message counts;
they do not acquire the simulator snapshots or imply health. Older media declares
no robot stream. Missing declared files are explicit missing evidence. There is
no interpolation, morphology rule, threshold, grade or healthy verdict.

## Isolated wheel installation

Use Python 3.12.14 and uv 0.12.23 in a dedicated environment. The upstream
immutable release asset has an opaque filename; download to its wheel filename
and verify it before installation:

```sh
curl -fL https://github.com/Living-Proof-Labs/livingproof-health/releases/download/v1.0.5/health-asset-ziyen2_r \
  -o livingproof_health-1.0.5-py3-none-any.whl
printf '%s  %s\n' d1ce13c2b68e31855ac81a83b478f174182bf0ab4894d917b7e0dd406ba2857c livingproof_health-1.0.5-py3-none-any.whl | sha256sum -c -
uv venv --python 3.12.14 /tmp/health-evaluator-env
uv pip install --python /tmp/health-evaluator-env/bin/python \
  ./livingproof_health-1.0.5-py3-none-any.whl ./livingproof_evaluator_health-VERSION-py3-none-any.whl
/tmp/health-evaluator-env/bin/python -m livingproof_evaluator_health --version
```

For this candidate, replace the evaluator wheel placeholder with the wheel built
by `uv build --wheel`. The normal release workflow publishes immutable GitHub
source releases, not evaluator wheel assets. After release, independently verify
the immutable release/tag/commit through GitHub, then install the exact source
commit instead of the evaluator wheel argument:

```sh
uv pip install --python /tmp/health-evaluator-env/bin/python \
  ./livingproof_health-1.0.5-py3-none-any.whl \
  'livingproof-evaluator-health @ git+https://github.com/Living-Proof-Labs/livingproof-evaluator-health.git@VERIFIED_RELEASE_COMMIT'
```

Replace `VERIFIED_RELEASE_COMMIT` with the full verified release commit, and check
that `--version` matches its genuine stable tag before replaying the fixture. The common dependency is also pinned to its
released wheel URL and SHA-256. The Health wheel pins its transitive runtime
dependencies. Do not install this into a sibling evaluator's environment.
For candidate verification, `uv build --wheel` supplies the evaluator wheel in
`dist/`; use the unchanged Health wheel in `vendor/`. A candidate install is not
proof that a future immutable evaluator release has been published or installed.

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

The PR's **Documentation** workflow builds the exact PR head and uploads
`docs-SOURCE_SHA`, retained for 14 days. Download and extract it, then inspect its
index and Version and source page. PR previews have no live public URL and use a unique shared candidate version.
After verification, protected main releases the evaluator and publishes its versioned
manual through the [publication gate](verification.md#publication-gate).
