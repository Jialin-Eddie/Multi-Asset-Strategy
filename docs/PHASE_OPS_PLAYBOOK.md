# Phase Ops Playbook — Minimum Viable Operations

How to manage phases using GitHub Milestones, Issues, and Projects. No concepts — just steps.

---

## Per-Phase Checklist

### 1. Create Milestone

```bash
gh milestone create "Phase NN — <Short Name>" \
  --description "Objective: <one-line goal>. Tag: vX.Y.Z-phaseNN-short-name"
```

### 2. Create Issues (5–12 per phase)

Each issue must have:
- Title: `[Phase NN] <task description>`
- Body: acceptance criteria + verification command
- Label: `phase-NN`
- Milestone: the one you just created

Template:

```bash
gh issue create \
  --title "[Phase NN] <task>" \
  --milestone "Phase NN — <Short Name>" \
  --label "phase-NN" \
  --body "$(cat <<'EOF'
## Acceptance Criteria
- [ ] <concrete criterion 1>
- [ ] <concrete criterion 2>

## Verification
```bash
<command to verify this issue is done>
```

## Expected Output
- Path: `report/phaseNN/results/<file>`
- Content: <what should be in the file>
EOF
)"
```

### 3. Create Phase Epic PR

```bash
git checkout -b phase/NN-short-name origin/master
# ... do work in sub-PRs or directly ...
# When ready, open the Epic PR:
gh pr create \
  --title "Phase NN — <Short Name>" \
  --base master \
  --body "$(cat <<'EOF'
Phase Epic PR. See milestone: Phase NN — <Short Name>

Closes #<issue1>, closes #<issue2>, ...

## Hard Checklist
<fill from .github/pull_request_template.md>
EOF
)"
```

Use `closes #NN` in PR body to auto-close issues when PR merges.

### 4. Merge → Tag → Release

After the Epic PR merges to `master`:

```bash
# Tag the merge commit
git checkout master && git pull origin master
git tag -a "vX.Y.Z-phaseNN-short-name" -m "Phase NN — <Short Name>"
git push origin "vX.Y.Z-phaseNN-short-name"
# CI will auto-create the Release (see .github/workflows/release-on-tag.yml)
```

If CI does not run (or for manual release):

```bash
# Package assets
cd report/phaseNN
zip -r results.zip results/
zip -r model.zip model/   # if applicable
zip -r meta.zip meta/     # if applicable

# Create release
gh release create "vX.Y.Z-phaseNN-short-name" \
  --title "Phase NN — <Short Name> (vX.Y.Z)" \
  --notes-file /tmp/release-notes.md \
  report.pdf results.zip model.zip meta.zip
```

### 5. Verify the Three Artifacts (三件套)

- [ ] **Phase Epic PR** exists and is merged to `master`
- [ ] **Annotated Tag** exists on the merge commit: `git tag -v vX.Y.Z-phaseNN-short-name`
- [ ] **GitHub Release** exists with assets attached: `gh release view vX.Y.Z-phaseNN-short-name`

---

## GitHub Projects Board (Optional but Recommended)

### Setup (once per repo)

1. Create a Project: `Multi-Asset Strategy — Phase Tracker`
2. Add 4 columns:
   - **Backlog** — issues created but not started
   - **In Progress** — actively worked on
   - **Review** — PR open, awaiting review
   - **Done** — merged + released

### Auto-Add Rules

In Project Settings → Workflows:
- Auto-add issues from this repo when labeled `phase-*`
- Auto-move to "Done" when issue is closed

---

## Quick Reference

| Action | Command |
|--------|---------|
| List milestones | `gh milestone list` |
| List phase issues | `gh issue list --milestone "Phase NN — ..."` |
| Check PR status | `gh pr status` |
| View release | `gh release view vX.Y.Z-phaseNN-short-name` |
| Download release assets | `gh release download vX.Y.Z-phaseNN-short-name` |
| List tags | `git tag -l "v*-phase*"` |

---

## One-Sentence Trigger

To start a new phase, tell PhaseOps:

> "Start Phase NN — <Short Name>. Goal: <one-line objective>. Tag: vX.Y.Z-phaseNN-short-name."

PhaseOps will output the milestone, issues, and next actions.
