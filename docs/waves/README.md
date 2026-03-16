# Wave Briefs

This folder contains short, execution-ready wave briefs for Claude.

Use:
- `docs/templates/project-brief-template.md` as canonical structure
- `ORCHESTRATOR.md` as execution control plane

Validation helpers:
- `python scripts/brief_lint.py --glob "docs/waves/*.md"`
- `python scripts/wave_overlap_guard.py <briefA> <briefB> <briefC>`

Rule:
- keep each wave to max `3` disjoint tasks
- keep hub-file integration in supervisor merge pass by default

