#!/usr/bin/env python3
"""
John — Local Code Review Agent 🔴

Run this script to get John's review of your current changes before creating a PR.

Usage:
    python scripts/john_review.py              # Review uncommitted changes
    python scripts/john_review.py --pr 42      # Review a specific PR (requires gh CLI)
    python scripts/john_review.py --branch     # Review current branch vs main
"""

import subprocess
import sys
import os
from pathlib import Path


def run_cmd(cmd: str) -> str:
    """Run shell command and return output."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout.strip()


def detect_base_branch() -> str:
    """Detect the default branch (main or master)."""
    for branch in ["origin/main", "origin/master"]:
        result = subprocess.run(
            f"git rev-parse --verify {branch}",
            shell=True, capture_output=True, text=True
        )
        if result.returncode == 0:
            return branch
    return "origin/main"


def get_diff(mode: str, pr_number: str = None) -> dict:
    """Get diff and file statistics."""
    base = detect_base_branch()

    if mode == "pr" and pr_number:
        diff = run_cmd(f"gh pr diff {pr_number}")
        files = run_cmd(f"gh pr diff {pr_number} --name-only")
        new_filter_cmd = f"gh pr diff {pr_number} --name-only"
    elif mode == "branch":
        diff = run_cmd(f"git diff {base}...HEAD")
        files = run_cmd(f"git diff {base}...HEAD --name-only")
        new_filter_cmd = f"git diff {base}...HEAD --name-only --diff-filter=A"
    else:
        diff = run_cmd("git diff HEAD")
        files = run_cmd("git diff HEAD --name-only")
        new_filter_cmd = "git diff HEAD --name-only --diff-filter=A"

    file_list = [f for f in files.split("\n") if f]

    return {
        "diff": diff,
        "files": file_list,
        "new_files": [f for f in run_cmd(new_filter_cmd).split("\n") if f],
        "py_count": sum(1 for f in file_list if f.endswith(".py")),
        "md_count": sum(1 for f in file_list if f.endswith(".md")),
    }


def johns_automated_checks(stats: dict) -> list:
    """Run John's rule-based checks."""
    warnings = []

    # Check 1: Too many new files
    n_new = len(stats["new_files"])
    if n_new > 3:
        warnings.append(f"🔴 {n_new} new files. Each file is a maintenance liability. Justify every one.")

    # Check 2: More docs than code
    if stats["md_count"] > stats["py_count"] and stats["md_count"] > 0:
        warnings.append(
            f"⚠️  More .md files ({stats['md_count']}) than .py files ({stats['py_count']}). "
            f"Are we writing documentation or software?"
        )

    # Check 3: New CLAUDE.md files
    new_claude = [f for f in stats["new_files"] if "CLAUDE.md" in f]
    if new_claude:
        warnings.append(f"⚠️  {len(new_claude)} new CLAUDE.md file(s). Meta-documentation is meta-complexity.")

    # Check 4: Placeholder detection
    if stats["diff"]:
        placeholders = ["placeholder", "todo", "fixme", "hack", "temporary", "workaround"]
        found = [p for p in placeholders if p.lower() in stats["diff"].lower()]
        if found:
            warnings.append(f"🔴 Found in diff: {', '.join(found)}. Ship it done or don't ship it.")

    # Check 5: Pure additions
    additions = stats["diff"].count("\n+") if stats["diff"] else 0
    deletions = stats["diff"].count("\n-") if stats["diff"] else 0
    if additions > 50 and deletions == 0:
        warnings.append(f"⚠️  {additions} additions, 0 deletions. Pure growth increases complexity. What can be removed?")

    # Check 6: Large files
    for f in stats["new_files"]:
        filepath = Path(f)
        if filepath.exists():
            lines = sum(1 for _ in open(filepath))
            if lines > 300:
                warnings.append(f"⚠️  {f} is {lines} lines. Can it be split or simplified?")

    return warnings


def print_review(stats: dict, warnings: list):
    """Print John's review to terminal."""
    RED = "\033[91m"
    YELLOW = "\033[93m"
    GREEN = "\033[92m"
    BOLD = "\033[1m"
    RESET = "\033[0m"

    print(f"\n{RED}{BOLD}{'='*60}")
    print(f"  🔴 JOHN'S CODE REVIEW")
    print(f"{'='*60}{RESET}\n")

    # Stats
    print(f"{BOLD}Files Changed:{RESET}")
    print(f"  Total:     {len(stats['files'])}")
    print(f"  New:       {len(stats['new_files'])}")
    print(f"  .py files: {stats['py_count']}")
    print(f"  .md files: {stats['md_count']}")

    if stats["new_files"]:
        print(f"\n{BOLD}New Files (John scrutinizes these):{RESET}")
        for f in stats["new_files"]:
            print(f"  {RED}+ {f}{RESET}")

    # Warnings
    print(f"\n{BOLD}Automated Checks:{RESET}")
    if warnings:
        for w in warnings:
            print(f"  {w}")
    else:
        print(f"  {GREEN}✅ No automated concerns.{RESET}")

    # Complexity score
    score = 0
    score += min(len(stats["new_files"]) * 2, 6)
    score += 2 if stats["md_count"] > stats["py_count"] else 0
    score += 2 if any("🔴" in w for w in warnings) else 0
    score = min(score, 10)

    color = GREEN if score <= 3 else YELLOW if score <= 6 else RED
    print(f"\n{BOLD}Complexity Score: {color}{score}/10{RESET}")

    if score > 5:
        print(f"{RED}  John demands justification for every new file in this PR.{RESET}")

    # John's maxim
    print(f"\n{RED}  — \"The best code is the code you didn't write.\"{RESET}")
    print(f"{RED}{'='*60}{RESET}\n")


def main():
    args = sys.argv[1:]

    if "--pr" in args:
        idx = args.index("--pr")
        pr_number = args[idx + 1] if idx + 1 < len(args) else None
        if not pr_number:
            print("Usage: john_review.py --pr <number>")
            sys.exit(1)
        stats = get_diff("pr", pr_number)
    elif "--branch" in args:
        stats = get_diff("branch")
    else:
        stats = get_diff("local")

    warnings = johns_automated_checks(stats)
    print_review(stats, warnings)

    # Exit code: 1 if any red warnings
    if any("🔴" in w for w in warnings):
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
