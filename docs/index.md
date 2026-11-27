# Health evaluator

This standalone CLI produces deterministic observations for recorded trials.
It validates the evidence/media binding and selected file hashes before using
pinned Health v1.0.5 bounded replay. Simulator base pose remains explicitly
simulator evidence; robot MCAP is examined separately. An advisory result
covers every trial in the evidence manifest and cites `health.json`. Without
media, that command exits 2 and writes no result. The per-trial command
remains for one declared trial. There are no health
verdicts, scores, Action registration, or report UI.

Start with the [development and installation guide](guide.md),
[verification evidence](verification.md), and generated
[CLI reference](reference.md). The original G1 corner fixture yields 614
samples and minimum recorded height 0.74637 m at 4.44 seconds in world frame.
This says nothing about between-sample behavior or physical robot health.

Documentation is published only after verified protected-main release.
The [version and source](version.md) page identifies each build.
