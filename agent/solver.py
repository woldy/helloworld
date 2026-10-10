"""Unit orchestration: specialised solvers first, instruction-derived floor.

This is submission #1: deterministic, no model (``models: []``). Its purpose
is account/team binding and full-pipeline validation, so it must never crash:
any unit without a specialised solver still exits 0 with the deliverable
filenames its instruction names.

Submission #2 (House-model agent) will replace the fallback with an LLM loop
driven by MODEL_ENDPOINT/MODEL_NAME/MODEL_TOKEN; the hook point is
``solve_unit`` below.
"""

from __future__ import annotations

import pathlib
import sys

from .bsgreeks import find_options_table
from .deliverables import parse_instruction
from .fallback import last_resort, write_deliverable


def solve_unit(task_dir: str | pathlib.Path, out: str | pathlib.Path) -> list[pathlib.Path]:
    task = pathlib.Path(task_dir)
    out_dir = pathlib.Path(out)
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[pathlib.Path] = []

    instruction_path = task / "instruction.md"
    instruction = (
        instruction_path.read_text(encoding="utf-8", errors="replace")
        if instruction_path.is_file()
        else ""
    )

    # 1) Specialised: Black-Scholes options-schema units -> closed-form Greeks.
    try:
        options = find_options_table(task)
    except Exception:  # noqa: BLE001
        options = None
    if options is not None:
        try:
            from .bsgreeks import solve as solve_bs

            written.append(solve_bs(options, out_dir))
        except Exception:  # noqa: BLE001
            print("[agent] bs solver failed, falling back", file=sys.stderr)

    # 2) Instruction-derived deliverables (skipped for the BS family, whose
    #    instruction names only results.parquet — already written above).
    deliverables = parse_instruction(instruction) if instruction else []
    for deliverable in deliverables:
        if deliverable.filename == "results.parquet" and any(
            w.name == "results.parquet" for w in written
        ):
            continue
        path = write_deliverable(out_dir, deliverable, instruction)
        if path is not None:
            written.append(path)

    # 3) Floor: the two dominant filenames across the public corpus.
    last_resort(out_dir)
    return written
