#!/usr/bin/env python3
"""Basic CHDMAN security check for Retroclamp"""

import logging
import sys
from pathlib import Path


def main():
    issues = []

    # Check core files for shell=True usage
    core_dir = Path("core")
    if core_dir.exists():
        for py_file in core_dir.glob("*.py"):
            try:
                with open(py_file, encoding="utf-8") as f:
                    content = f.read()
                if "shell=True" in content:
                    issues.append(f"Security risk in {py_file}: shell=True usage")
            except Exception as e:
                logging.warning(f"Exception in chdman_security_check: {e}")
                continue

    if issues:
        print("CHDMAN Security Issues:")
        for issue in issues:
            print(f"  - {issue}")
        sys.exit(1)
    else:
        print("[OK] CHDMAN security checks passed")


if __name__ == "__main__":
    main()
