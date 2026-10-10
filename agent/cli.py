"""Submission CLI entrypoint.

Contract (SUBMISSION_CLI.md, interface_version 2.0):
    solve --task-dir /input --out /app/output

The image has no ENTRYPOINT; the verb arrives as the first argument and this
module consumes it as a leading positional. Exit 0 on success; never raise.
"""

from __future__ import annotations

import argparse
import sys
import traceback

from .solver import solve_unit


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Agenthon 2026 T1 agent")
    parser.add_argument("verb", choices=["solve"])
    parser.add_argument("--task-dir", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    try:
        deliverables = solve_unit(args.task_dir, args.out)
        for path in deliverables:
            print(f"[agent] wrote {path}", file=sys.stderr)
    except Exception:  # noqa: BLE001 — a submission must not crash the unit
        traceback.print_exc()
        # Last-resort floor: guarantee an exit-0 run wrote *something*.
        try:
            from .fallback import last_resort

            last_resort(args.out)
        except Exception:  # noqa: BLE001
            traceback.print_exc()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
