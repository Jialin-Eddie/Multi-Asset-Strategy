# Release Notes Template

Use this template for every GitHub Release created after a phase completes.

---

## Template

```markdown
# Phase {NN} — {Short Name} (v{X}.{Y}.{Z})

## Scope
- One-line summary of what this phase delivered.
- Key changes: <bullet list of 3–5 items>

## How to Reproduce

### Environment Setup
```bash
conda env create -f environment.yml
conda activate multi_as_env
```

### Run Commands
```bash
# Data pipeline
python src/data/downloader.py
python src/data/loader.py

# Phase-specific execution
<exact command(s) to reproduce this phase's results>
```

### Expected Output
- Results written to: `report/phase{NN}/results/`
- Report generated at: `report/phase{NN}/report.pdf`
- Model artifacts at: `report/phase{NN}/model/` (if applicable)

## Results Summary

| Metric | Value | Source |
|--------|-------|--------|
| <metric_name> | <value> | `report/phase{NN}/results/<file>` |
| ... | ... | ... |

## Assets Attached

| Asset | File | Size | Notes |
|-------|------|------|-------|
| Report | `report.pdf` | — | Phase summary document |
| Results | `results.zip` | — | All CSV/PNG/JSON outputs |
| Model | `model.zip` | — | Weights/checkpoints (if applicable) |
| Metadata | `meta.zip` | — | Run config, git SHA, env info (if applicable) |

> If any asset was split due to size constraints (>1.5 GiB), parts are named
> `model.zip.001`, `model.zip.002`, etc. Reassemble with:
> `cat model.zip.* > model.zip && unzip model.zip`

## Rollback

To revert to the state before this phase:
```bash
git checkout v{PREV_X}.{PREV_Y}.{PREV_Z}-phase{PREV_NN}-{prev-short-name}
```

To revert only this phase's merge commit:
```bash
git revert -m 1 <merge-commit-sha>
```

## Verification

After reproducing, verify key metrics match the Results Summary table above.
Metric files are at: `report/phase{NN}/results/metrics.json`

---

_Tag: `v{X}.{Y}.{Z}-phase{NN}-{short-name}`_
_Commit: `<sha>`_
_Date: `<date>`_
```

---

## Required Fields

Every release note MUST contain:
1. **Scope** — what changed
2. **How to Reproduce** — exact commands (must work in CI)
3. **Results Summary** — table with metric, value, and source file path
4. **Assets Attached** — table listing every uploaded file
5. **Rollback** — how to undo this phase

Optional but recommended:
- **Known Issues** — anything not resolved
- **Dependencies** — other phases or external requirements
- **Split Strategy** — if any asset was split, explain why and how to reassemble

## Rules

- All paths must reference `report/phaseNN/` — never repo root or `outputs/`.
- Reproduce commands must be copy-pasteable (no "adjust as needed").
- Metrics must cite their exact file path, not "see results folder."
- If reproduce requires data download (network), note it explicitly.
