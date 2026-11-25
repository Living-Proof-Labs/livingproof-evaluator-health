# Compatibility harness, not the current stock baseline

Original files (`README.md`, `PROVENANCE.json`, `generate.py.txt`, observation,
binding and MCAP) are unchanged byte copies from livingproof-evaluator-scenario
**v1.5.18**, commit `023bd6bb4a0a2cd7a4329ed06fe67219ff86006e`, directory
`tests/fixtures/sim-v3.8.1-g1-playground`. Apache-2.0. Tests verify every digest in
the original provenance map. No generator was run for this change.

The upstream fixture is a previously retained G1 **playground** recording from
simulator v3.8.1. It is **not** the stock baseline from Action run 45572701070.
Its own provenance distinguishes actual producer commits from nominal lock pins.
The original observation and MCAP were paired upstream; neither is rewritten.

The three added JSON files `manifest.json`, `run-manifest.json` and `media.json`
are **synthetic test wrappers**, carrying only fields this CLI consumes. Their
run ID explicitly says `test-wrapper-historical-g1-playground`. The simulator
version is not recorded in the retained fixture, so the test wrapper explicitly
says `not-recorded-in-retained-fixture`; it is not a measured version. These are
not fetched hosted manifests. Media 2.2 empty-robot tests create a separate valid
empty MCAP in temporary storage; they do not claim an original robot recording.

The producer-defined hallway schema was checked against the actual baseline's
runner **livingproof-sim-mujoco v3.9.7**, commit
`727d8706598e8ac706324ca87edd0973fdbb3485`,
`src/livingproof_sim_mujoco/observations.py` (`observe`, lines 327–440).
SHA-256 of that source file:
`d8050f3918e45980f1d55f2aa11f7dda784716a71dc22be64f06da105f87d26e`.
Its `observe_route` defines the separately accepted route format. This legacy
observation format is defined by the producer, not the unrelated graded-result
JSON Schema. No grade policy or observation-to-MCAP reconstruction is used here.

Independent bounded replay of these retained bytes gives 481 pose samples and
minimum z **0.70652 m at 2900000000 ns** in world frame. The observation summary
rounds this to 0.7065 m; that summary is not the Health calculation's input.

Current hosted baseline evidence remains unavailable to this worker: ordinary
GitHub Actions download of artifact 15002333477 returned HTTP 403 from Azure blob
storage. Hosted check 139066491761 in run 45572701070 confirms the baseline's
actual observation format is hallway/2.0.0, but does not supply its bytes. Report
artifact 15002234798 and MCAP artifact 15002428847 identify the remaining replay
gate. Do not substitute this historical fixture for that exact-evidence proof.
