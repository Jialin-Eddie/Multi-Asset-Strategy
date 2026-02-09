#!/usr/bin/env python3
"""
Phase Completion Hook — Runs John + Alex after each phase milestone.

Triggered automatically by git post-commit hook when a commit message
contains "Phase" or "phase". Can also be run manually.

Usage:
    python scripts/phase_complete.py              # Auto-detect from last commit
    python scripts/phase_complete.py --phase 0    # Specify phase number
    python scripts/phase_complete.py --dry-run    # Preview without running
"""

import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# ANSI colors
CYAN = "\033[96m"
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
RESET = "\033[0m"


def run_cmd(cmd: str, cwd: str = None) -> str:
    """Run shell command and return output."""
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True,
        cwd=cwd or str(PROJECT_ROOT)
    )
    return result.stdout.strip()


def detect_phase_from_commit() -> str:
    """Detect phase number from the most recent commit message."""
    msg = run_cmd("git log -1 --format=%s")
    msg_lower = msg.lower()

    # Try to extract phase number
    import re
    match = re.search(r'phase\s*(\d+)', msg_lower)
    if match:
        return match.group(1)

    if "phase" in msg_lower:
        return "?"

    return None


def get_phase_summary() -> str:
    """Get a short summary of what this phase commit contains."""
    msg = run_cmd("git log -1 --format=%s")
    files = run_cmd("git diff --name-only HEAD~1 HEAD")
    file_list = [f for f in files.split("\n") if f]
    py_files = [f for f in file_list if f.endswith(".py")]
    test_files = [f for f in file_list if "test" in f.lower()]

    return {
        "commit_msg": msg,
        "total_files": len(file_list),
        "py_files": len(py_files),
        "test_files": len(test_files),
        "file_list": file_list,
    }


def run_john(dry_run: bool = False) -> dict:
    """Run John's code review."""
    print(f"\n{RED}{BOLD}{'='*60}")
    print(f"  Waking up John for code review...")
    print(f"{'='*60}{RESET}\n")

    if dry_run:
        print(f"  {YELLOW}[DRY RUN] Would run: python scripts/john_review.py --branch{RESET}")
        return {"ran": False, "exit_code": 0}

    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "john_review.py"), "--branch"],
        cwd=str(PROJECT_ROOT),
        capture_output=False,
    )

    return {"ran": True, "exit_code": result.returncode}


def run_alex(dry_run: bool = False) -> dict:
    """Run Alex's management report."""
    print(f"\n{CYAN}{BOLD}{'='*60}")
    print(f"  Waking up Alex for management report...")
    print(f"{'='*60}{RESET}\n")

    if dry_run:
        print(f"  {YELLOW}[DRY RUN] Would run: python scripts/alex_report.py --summary{RESET}")
        return {"ran": False, "exit_code": 0}

    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "alex_report.py"), "--summary"],
        cwd=str(PROJECT_ROOT),
        capture_output=False,
    )

    # Also generate full report and save it
    timestamp = datetime.now().strftime("%Y%m%d")
    report_path = PROJECT_ROOT / "outputs" / f"phase_report_{timestamp}.md"
    subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "alex_report.py"),
         "--output", str(report_path)],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
    )

    if report_path.exists():
        print(f"\n  Full report saved to: {report_path}")

    return {"ran": True, "exit_code": result.returncode}


def main():
    args = sys.argv[1:]
    dry_run = "--dry-run" in args

    # Detect phase
    if "--phase" in args:
        idx = args.index("--phase")
        phase = args[idx + 1] if idx + 1 < len(args) else "?"
    else:
        phase = detect_phase_from_commit()

    if phase is None:
        print(f"{YELLOW}No phase detected in recent commit. Use --phase N to specify.{RESET}")
        sys.exit(0)

    # Header
    summary = get_phase_summary()
    print(f"\n{BOLD}{'='*60}")
    print(f"  PHASE {phase} COMPLETION — Review & Report")
    print(f"{'='*60}{RESET}")
    print(f"\n  Commit: {summary['commit_msg']}")
    print(f"  Files:  {summary['total_files']} changed ({summary['py_files']} .py, {summary['test_files']} tests)")
    print(f"  Time:   {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    # Run John
    john_result = run_john(dry_run)

    # Run Alex
    alex_result = run_alex(dry_run)

    # Summary
    print(f"\n{BOLD}{'='*60}")
    print(f"  PHASE {phase} REVIEW COMPLETE")
    print(f"{'='*60}{RESET}")

    john_status = f"{GREEN}PASS{RESET}" if john_result["exit_code"] == 0 else f"{RED}CONCERNS{RESET}"
    alex_status = f"{GREEN}DONE{RESET}" if alex_result["exit_code"] == 0 else f"{RED}ERROR{RESET}"

    if not dry_run:
        print(f"  John's verdict:  {john_status}")
        print(f"  Alex's report:   {alex_status}")
    else:
        print(f"  {YELLOW}[DRY RUN] No agents were actually executed{RESET}")

    print()


if __name__ == "__main__":
    main()
