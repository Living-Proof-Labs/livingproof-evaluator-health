# Offline primary sources

These JSON files are unmodified primary source bytes, used only when the evidence
pins and embedded profiles agree. They are data, not executable evaluator inputs.
Both upstream repositories are Living Proof Labs projects licensed Apache-2.0.

- `parameters.json`: robot-capability-specs commit
  `57317e617014a6df97bb7fba9d92a890af8d42e5`,
  `specs/scenarios/walk-hallway/parameters.json`, SHA-256
  `9226aa6bc0e577863bdc210514e7e7c3a7edc32f49c4f7b46aa7249837f08b3d`.
- `stock.json`: livingproof-unitree-g1 commit
  `d554c8243a12849dc7fe8acc1921bb3d4e5239a7`,
  `configurations/stock.json`, SHA-256
  `8baf584eb025fa4408aad20a81521b73bc068a3a7e613dfeeb8f03d24eb02b5e`.

The threshold is read from the authenticated configuration via the rule in the
parameter document, never supplied as a Health default. Unknown source revisions
remain unevaluated. Verification and source-set expansion belong to evaluator
releases, not per-evaluator rendering code in consumers.
