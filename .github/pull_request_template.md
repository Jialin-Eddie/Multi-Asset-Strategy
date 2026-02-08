## Summary

<!-- One-line: what does this PR do and why? -->

**Phase:** <!-- e.g., Phase 03 — Backtest Framework -->
**Type:** <!-- feature | bugfix | refactor | experiment | infra | docs -->

---

## Hard Checklist (Required — PhaseOps will block if incomplete)

### Reproduce Command
<!-- Exact command(s) to reproduce the results of this PR. Must be runnable in CI. -->

```bash
# Example:
# python src/data/downloader.py
# python scripts/final_strategy_summary.py
```

### Core Metrics
<!-- Key metrics this PR produces or affects. State value AND source path. -->

| Metric | Value | Source |
|--------|-------|--------|
| <!-- e.g., Sharpe Ratio --> | <!-- e.g., 0.819 --> | <!-- e.g., report/phase03/results/metrics.json --> |

### Test Command
<!-- Command to run tests that validate this PR's changes. -->

```bash
# Example:
# pytest tests/ -v
```

### Asset Plan
<!-- What artifacts does this phase produce? All must be under report/phaseNN/. -->

- [ ] `report/phaseNN/report.pdf` — Phase report document
- [ ] `report/phaseNN/results/` — Result files (CSV, PNG, JSON, logs)
- [ ] `report/phaseNN/model/` — Model weights/checkpoints (if applicable)
- [ ] `report/phaseNN/meta/` — Run config, git SHA, env info (if applicable)

### Risk Assessment
<!-- Check all that apply -->

- [ ] Changes backtest engine core logic
- [ ] Changes signal generation logic
- [ ] Changes portfolio optimization logic
- [ ] Changes data pipeline schema/format
- [ ] Changes API routes or dashboard
- [ ] Changes CI/CD configuration
- [ ] No high-risk changes

### Evidence Completeness
- [ ] Reproduce command tested locally and works
- [ ] Metrics values filled with actual numbers (not placeholders)
- [ ] All artifact paths verified to exist after running reproduce command
- [ ] No large files (>10 MB) committed to git history — artifacts are Release-only

---

## Soft Review Space (For code review — optional)

<!-- Code reviewers: use this space for architectural feedback, naming suggestions,
     performance observations, readability notes, etc. PhaseOps does not evaluate this section. -->

### Architecture & Design
<!-- Any structural concerns or suggestions? -->

### Performance
<!-- Any performance implications? -->

### Naming & Readability
<!-- Any naming or clarity improvements? -->

### Other Notes
<!-- Anything else the reviewer wants to flag? -->
