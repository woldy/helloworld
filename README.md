# agenthon-t1-sub

Agenthon 2026 Track 1 (coding) — submission image build.

CI builds `woldywei-agenthon-t1:sub1` and pushes it to
`ghcr.io/woldy/agenthon-t1-sub1:sub1` using the built-in `GITHUB_TOKEN`
(packages: write). The base image is pinned by digest so the build is
reproducible; all runtime dependencies are vendored as wheels and installed
offline, matching the locally verified image bit-for-bit in content.

Agent: deterministic BS-Greeks closed-form solver + instruction-derived
deliverable floor, `models: []` (no external model calls; runs fully offline).
License: Apache-2.0.
