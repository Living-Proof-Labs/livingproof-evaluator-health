# Immutable Health dependency

`livingproof_health-1.0.5-py3-none-any.whl` is the unchanged Apache-2.0 upstream
wheel from [livingproof-health v1.0.5](https://github.com/Living-Proof-Labs/livingproof-health/releases/tag/v1.0.5),
commit `8efd819910c364ee25d33ef81a5cf6c0a4f63f97`.

- GitHub release: `immutable: true` verified through the release API.
- Asset ID: `788842298`; name `health-asset-ziyen2_r`; label is the wheel filename.
- API digest and independently downloaded bytes both match SHA-256
  `d1ce13c2b68e31855ac81a83b478f174182bf0ab4894d917b7e0dd406ba2857c`.
- Download: https://github.com/Living-Proof-Labs/livingproof-health/releases/download/v1.0.5/health-asset-ziyen2_r

The immutable asset's URL has no wheel extension, which uv 0.12.23 refuses as a
direct wheel source. This small, byte-identical vendored wheel gives `uv sync
--locked` a portable filename without rebuilding upstream or changing its release.
Its embedded license is retained. Tests verify the digest independently of uv's
local path source. Install it explicitly alongside a built evaluator wheel; see
`docs/guide.md`. Keep this evaluator in its own virtual environment: Health pins
MCAP 1.3.0, while other evaluators may require a different version.
