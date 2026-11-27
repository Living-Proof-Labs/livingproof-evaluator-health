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

Or write one advisory result for every trial in the manifest:

```sh
uv run --locked python -m livingproof_evaluator_health \
  tests/fixtures/original-recording/evidence/manifest.json \
  --media tests/fixtures/original-recording/media \
  --out result.json
```

That command follows `livingproof-evaluator.json`. It writes `result.json` and
`health.json` in the same directory. The advisory `health.json` keeps format
`livingproof-evaluator-health/1` and holds every per-trial document in
`trials`, in manifest order. The per-trial command's own `health.json` is
unchanged. Neither output path may already exist. Repeating with a different
output path produces identical per-trial bytes for identical inputs and
installed versions. Invalid inputs return exit 2 without a new result. On the per-trial command,
omit `--media` for explicit missing media, or pass `--media-disabled` for an
explicit caller declaration that recording was disabled; this flag is not an
independently verified producer fact. That command still writes `health.json`
with the matching status. On the advisory command, either choice writes no
result and exits 2. Stderr is one line: `Health was not run: media missing.`
or `Health was not run: media disabled.`

## Supported input and limits

The CLI reads evidence `manifest.json` (livingproof-hallway-evidence/2.0.0),
the selected hashed observation (`livingproof-route-observation/0.1.0` or
`livingproof-hallway-observation/2.0.0`),
and, when media is supplied, `run-manifest.json` (livingproof-run-manifest/0.1).
Separate format adapters validate the producer-defined shape, including required
fields, trace columns, finite values and time ordering. Unknown formats and
route/hallway field substitution fail; observation bytes are never converted or
rewritten. Health values still come from MCAP, not the observation summary.
It validates the fields needed for trial/run/configuration identity and simulator
provenance, not every field of the wider evidence specification. Media versions
2.0.0, 2.1.0 and 2.2.0 are supported. Selected declared streams must have relative
confined paths, byte counts and SHA-256; all present selected files are hashed
and frozen before any MCAP decode. Duplicate trial indices/JSON keys, unknown
formats, malformed inputs and mismatched identities/hashes are refused.

JSON documents are capped at 4 MiB. MCAP uses Health's default resource limits
(128 MiB input, 8 MiB expanded chunk, 20,000 snapshots, bounded framing and CRC
checks). Before decoding, a bounded top-level framing pass enforces the mandatory
single Header/DataEnd/Footer envelope, section placement, grouped summary records,
fixed DataEnd/Footer sizes and footer section offsets. Optional Statistics message
counts must agree with the messages actually read; summary channels never add
messages. This closes the pinned reader's missing-DataEnd acceptance gap. It is
not a general index/conformance validator; payloads, chunk expansion and data/chunk
CRCs remain the pinned Health reader's responsibility. The section rules follow
the [MCAP specification](https://mcap.dev/spec#file-structure).
No CLI option raises those limits. Only `/base_pose` with upstream
foxglove.PoseInFrame JSON is interpreted, in metres. Output retains snapshots,
per-frame sampled minima, unavailable pose counts, versions, hashes and trial
identity. Equal minima choose the first timestamp in stable replay order.

Media 2.2's `robot_mcap` is separate from simulator `mcap`. A structurally valid
empty robot recording produces `no robot health telemetry`. Nonempty robot
streams produce an explicit unsupported-interpretation status and message counts;
they do not acquire the simulator snapshots or imply health. Older media declares
no robot stream. Missing declared files are explicit missing evidence. There is
no interpolation, morphology rule, threshold, grade or healthy verdict.

## Install the released source in isolation

Use Python 3.12.14 and uv 0.12.23 in a new working directory. This verified
example installs immutable release **v1.1.0**, whose tag resolves to
`3d0b4b211d93ea2b559ed08e65dbc31217e18015`. The normal release workflow publishes
GitHub source releases, not evaluator wheel assets.

Set `HEALTH_EVIDENCE` and `HEALTH_MEDIA` to absolute paths to your recorded trial's
evidence and media directories. For the retained known-answer fixture, use
`tests/fixtures/original-recording/evidence` and `tests/fixtures/original-recording/media`
from a checkout of that release. Then run this block from the new working directory:

<!-- released-source-install:start -->
```sh
uv venv --python 3.12.14 .health-env
uv pip install --python .health-env/bin/python \
  'livingproof-evaluator-health @ git+https://github.com/Living-Proof-Labs/livingproof-evaluator-health.git@3d0b4b211d93ea2b559ed08e65dbc31217e18015'
.health-env/bin/python -m livingproof_evaluator_health --version
.health-env/bin/python -m livingproof_evaluator_health \
  --evidence "$HEALTH_EVIDENCE" --media "$HEALTH_MEDIA" --trial 1 --output health.json
```
<!-- released-source-install:end -->

The version must be `livingproof-evaluator-health 1.1.0`. The retained original
fixture yields 614 simulator samples, minimum 0.74637 m at 4440000000 ns in world
frame. `health.json` must be a new output path. The source install supplies its
vendored, pinned Health wheel itself; adding a second Health wheel argument causes
conflicting source URLs in uv. Keep this evaluator in its own environment.
The common dependency is pinned to its released wheel URL and SHA-256, and the
Health wheel pins its transitive runtime dependencies.

`task verify` executes the exact block above in a temporary directory against
this pinned immutable source, checking the stable installed version and repeated
known-answer replay. This is a historical released-source installation regression;
the separate candidate-wheel check tests current code. A future release still
requires verification of its own immutable tag/commit and installed stable version.

## Install a locally built candidate wheel

For development, `uv build --wheel` writes the candidate evaluator wheel in `dist/`.
Unlike the Git source install, this wheel needs the explicit upstream Health wheel.
Use a separate environment and replace `VERSION` below with the built filename:

```sh
uv venv --python 3.12.14 .candidate-env
uv pip install --python .candidate-env/bin/python \
  ./vendor/livingproof_health-1.0.5-py3-none-any.whl ./dist/livingproof_evaluator_health-VERSION-py3-none-any.whl
.candidate-env/bin/python -m livingproof_evaluator_health --version
```

The unchanged upstream Health v1.0.5 wheel is checked against SHA-256
`d1ce13c2b68e31855ac81a83b478f174182bf0ab4894d917b7e0dd406ba2857c`.
A candidate install does not prove a future immutable evaluator release.

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
