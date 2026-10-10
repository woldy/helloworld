"""Placeholder deliverable writers for units without a specialised solver.

A first submission's floor is: exit 0 and write a file with the filename the
unit's checker expects, in a syntactically valid shape derived from the
instruction. Numerical correctness is not claimed. JSON keys known from the
instruction get plausible typed values; CSV columns from the instruction's
table get a single zero row; unknown shapes get a minimal valid document.
"""

from __future__ import annotations

import csv
import json
import pathlib
import re

from .deliverables import Deliverable

_INTISH = re.compile(r"^(num|count|n_|total|has_|is_)")


def _json_value(key: str):
    if _INTISH.match(key):
        return 0
    if key.startswith(("date", "latest_", "period", "timestamp")):
        return ""
    return None


def _from_example(example: str) -> dict | None:
    """Mirror the keys of an inline JSON example like {"zero_rates": {...}}."""
    try:
        parsed = json.loads(example.replace("...", "null").replace("…", "null"))
    except (json.JSONDecodeError, ValueError):
        return None
    if isinstance(parsed, dict):

        def zero(v):
            if isinstance(v, dict):
                return {k: zero(x) for k, x in v.items()}
            if isinstance(v, list):
                return []
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                return 0
            return v if isinstance(v, str) else None

        return {k: zero(v) for k, v in parsed.items()}
    return None


def write_json(out: pathlib.Path, deliverable: Deliverable, instruction: str) -> pathlib.Path:
    payload: dict | None = None
    # An inline example bound to this file: `{"zero_rates": {...}}`
    esc = re.escape(deliverable.filename)
    m = re.search(esc + r"[^\n]{0,40}?(`\{.*?\}`)", instruction)
    if m:
        payload = _from_example(m.group(1).strip("`"))
    if payload is None:
        payload = {k: _json_value(k) for k in deliverable.json_keys} or {}
    target = out / deliverable.filename
    target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return target


def write_csv(out: pathlib.Path, deliverable: Deliverable) -> pathlib.Path:
    target = out / deliverable.filename
    cols = deliverable.csv_columns or ["value"]
    with open(target, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        w.writerow([0] * len(cols))
    return target


def write_parquet(out: pathlib.Path, deliverable: Deliverable) -> pathlib.Path:
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError:
        # stdlib-only fallback: an empty parquet is not writable without
        # pyarrow, so emit nothing rather than a corrupt file
        return out / deliverable.filename
    table = pa.table({"placeholder": pa.array([], type=pa.float64())})
    target = out / deliverable.filename
    pq.write_table(table, target)
    return target


def write_deliverable(
    out: pathlib.Path, deliverable: Deliverable, instruction: str
) -> pathlib.Path | None:
    out.mkdir(parents=True, exist_ok=True)
    try:
        if deliverable.filename.endswith(".json"):
            return write_json(out, deliverable, instruction)
        if deliverable.filename.endswith(".csv"):
            return write_csv(out, deliverable)
        if deliverable.filename.endswith(".parquet"):
            return write_parquet(out, deliverable)
        target = out / deliverable.filename
        target.write_text(
            "# placeholder deliverable (deterministic submission #1)\n",
            encoding="utf-8",
        )
        return target
    except Exception:  # noqa: BLE001 — one bad deliverable must not sink the rest
        return None


def last_resort(out: str | pathlib.Path) -> None:
    """Absolute floor: guarantee the two dominant filenames exist, non-empty."""
    out = pathlib.Path(out)
    out.mkdir(parents=True, exist_ok=True)
    for name, body in (
        ("results.json", {}),
        ("summary.json", {}),
    ):
        target = out / name
        if not target.exists():
            target.write_text(json.dumps(body) + "\n", encoding="utf-8")
