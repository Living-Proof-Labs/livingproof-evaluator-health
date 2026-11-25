# Recorded trial provenance

`original-recording/` is copied byte-for-byte from livingproof-health v1.0.5,
commit `8efd819910c364ee25d33ef81a5cf6c0a4f63f97`,
`tests/fixtures/original-recording`. Apache-2.0. Its original `provenance.json`
retains producer, robot package, hashes, environment, and the failed original
artifact retrieval followed by the authorized unmodified recorder rerun.
These are simulator recordings, not hardware telemetry. No models or policies
are redistributed. Tests verify every file digest in that provenance manifest.

Expected independent MCAP result: 614 `/base_pose` samples in world frame,
minimum z 0.74637 m at 4440000000 ns; original observation summary rounds this
to 0.7464 m. The evaluator does not read that summary to calculate its minimum.

The media 2.2 empty-robot case is a separately labelled synthetic test assembled
in a temporary directory: unchanged original simulator recording plus an empty
valid MCAP made by pinned mcap.writer 1.3.0. Its media manifest declares its exact
size and SHA-256. It is not claimed to be the original recorder's robot output.
