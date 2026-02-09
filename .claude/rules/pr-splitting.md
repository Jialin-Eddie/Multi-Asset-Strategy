# PR Splitting Decision Tree

This rule engine determines whether a PR must be split into stacked PRs before review or merge.

---

## Decision Flow

```
START
  │
  ├─ HARD RULES (any one triggers mandatory split)
  │   │
  │   ├─ H1: Does the PR touch >1 distinct topic?
  │   │       Topics: core logic | metric definitions | experiment configs |
  │   │                infrastructure/CI | documentation-only | data pipeline
  │   │       → YES → MUST SPLIT (one PR per topic)
  │   │
  │   ├─ H2: Does the PR modify a high-risk surface AND other things?
  │   │       High-risk: backtest engine | portfolio optimizer | signal generation |
  │   │                  data loader schema | API routes | CI/CD pipeline
  │   │       → YES → MUST SPLIT (isolate high-risk change)
  │   │
  │   ├─ H3: Would reverting this PR break reproducibility of another change in the same PR?
  │   │       Test: Can each logical change be reverted independently without breaking the other?
  │   │       → NO (they're entangled) → MUST SPLIT
  │   │
  │   └─ H4: Does the diff exceed 500 lines AND span ≥3 directories?
  │           → YES → MUST SPLIT (unless purely mechanical rename/refactor with proof)
  │
  ├─ SOFT RULES (count hits; ≥2 triggers recommended split)
  │   │
  │   ├─ S1: PR touches both production code and test code for unrelated features
  │   ├─ S2: PR includes config/parameter changes alongside logic changes
  │   ├─ S3: PR modifies >3 files in different modules
  │   ├─ S4: PR description requires >3 bullet points to summarize scope
  │   ├─ S5: Reviewer would need context-switching between domains to review
  │   └─ S6: PR includes "while I was at it" or "also fixed" changes
  │
  │   → Count ≥ 2 → RECOMMEND SPLIT
  │
  └─ PASS → PR may proceed as-is
```

---

## Output Format (when split is required)

```
【Decision】 MUST SPLIT / RECOMMEND SPLIT
【Rules triggered】 H1, S2, S4 (list all)
【Split Plan】
  PR 1: <title> — <scope> — branch: <name>
  PR 2: <title> — <scope> — branch: <name> (depends on PR 1)
  PR 3: <title> — <scope> — branch: <name> (depends on PR 2)
【Merge Order】 PR 1 → PR 2 → PR 3
【Shortest Fix Path】
  1. git checkout -b <branch-1> origin/master
  2. git cherry-pick <relevant-commits> (or manually move files)
  3. ...
```

---

## Output Format (when no split needed)

```
【Decision】 NO SPLIT REQUIRED
【Rules checked】 H1–H4: clear. S-score: 0/6 (or 1/6).
【Proceed】 PR may enter review.
```

---

## Examples

### Must Split
> PR adds a new carry signal module AND changes the backtest engine's fee model AND updates CI config.
> → H1 triggered (3 topics). H2 triggered (backtest engine is high-risk + other changes).
> Split into: (1) backtest fee model change, (2) carry signal module, (3) CI config update.

### Recommend Split
> PR adds new trend filter parameters AND updates test fixtures AND tweaks a docstring.
> → S1 (test + production), S2 (config + logic). Count = 2. Recommend split.

### No Split
> PR implements a single new visualization in `app/routes/performance.py` with its template.
> → Single topic, single module, low risk. Pass.

---

## Stacked PR Conventions

When splitting, use this branch naming:
```
phase/NN-short-name/01-<sub-topic>
phase/NN-short-name/02-<sub-topic>
phase/NN-short-name/03-<sub-topic>
```

Merge order: always base each stacked PR on the previous one.
After all merge, the Phase Epic PR on `master` captures the full phase.
