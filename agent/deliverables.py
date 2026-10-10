"""Parse a unit's instruction.md for its deliverable contract.

There is no schema file for Track 1 deliverables — the unit's instruction.md is
the only machine-adjacent statement. Observed naming patterns across the public
corpus (all handled here):

* section headings:      ``### `summary.json````, ``### File 1: calibration.json``
* bold list items:       ``7. **`summary.json`**:``
* explicit output paths: ``/output/results.parquet``, ``/app/output/summary.json``
* write/produce verbs:   "write ``results.json``", "produce ``x.csv``"
* bare backticked names: `` `turnover.csv` `` anywhere in the text

Shape hints per file, in priority order:

1. a fenced ```` ```json ```` block appearing shortly after the file's mention
   (the corpus documents deliverables with a literal example) — mirrored with
   zeroed values, keys preserved;
2. "Include these keys:" bullet lists;
3. bullet backticked identifiers under the file's section;
4. for CSV, the first-column cells of the markdown table under its section.

Inputs, reference files and checker artifacts (reward.json, ...) are excluded —
the exemplar instruction explicitly notes reward.json is the checker's own file.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

EXTENSIONS = ("json", "csv", "parquet", "txt")

CHECKER_ARTIFACTS = {
    "reward.json",
    "reward.txt",
    "pytest_report.json",
    "diagnostic.json",
    "reward_summary.json",
    "report.html",
}

KIT_FILES = {
    "instruction.md",
    "manifest.json",
    "card.toml",
    "conftest.py",
    "test_outputs.py",
    "verifier.py",
    "test.sh",
    "requirements.txt",
    "pyproject.toml",
    "dockerfile",
    "environment.yml",
    "readme.md",
}

_NAME = r"[A-Za-z0-9_][A-Za-z0-9_.\-]{0,80}?\.(?:json|csv|parquet|txt)"
_FENCE_JSON = re.compile(r"```json\s*\n(.*?)```", re.S)
_BULLET_KEY = re.compile(r"^\s*[-*]\s+`([A-Za-z_][A-Za-z0-9_]*)`")
_TABLE_CELL = re.compile(r"^\s*\|\s*`?([A-Za-z_][A-Za-z0-9_ ]*)`?\s*\|")


@dataclass
class Deliverable:
    filename: str
    json_example: str | None = None
    json_keys: list[str] = field(default_factory=list)
    csv_columns: list[str] = field(default_factory=list)


def _clean(name: str) -> str:
    return name.strip().strip("`*").split("/")[-1].strip()


def _acceptable(name: str) -> bool:
    base = _clean(name).lower()
    if not base.endswith(EXTENSIONS):
        return False
    if base in CHECKER_ARTIFACTS or base in KIT_FILES:
        return False
    return True


def parse_instruction(text: str) -> list[Deliverable]:
    found: dict[str, Deliverable] = {}
    lines = text.splitlines()

    # Names mentioned under an Inputs section are inputs, not deliverables.
    # The heading must START with "Input(s)" — "Step 1: Load and Validate
    # Input Data" merely contains the word and is not an Inputs section.
    input_names: set[str] = set()
    in_inputs = False
    for line in lines:
        if re.match(r"^#{1,3}\s+[Ii]nputs?\b", line):
            in_inputs = True
            continue
        if in_inputs and re.match(r"^#{1,2}\s+", line):
            in_inputs = False
        if in_inputs:
            for m in re.finditer(rf"`?({_NAME})`?", line):
                input_names.add(_clean(m.group(1)).lower())

    def accept(name: str) -> None:
        name = _clean(name)
        if _acceptable(name) and name.lower() not in input_names:
            found.setdefault(name, Deliverable(filename=name))

    # All naming patterns; keep mention positions for shape-hint binding.
    for i, line in enumerate(lines):
        stripped = line.strip()
        # ### `summary.json` / ### 1. calibration.json / ### File 1: x.json
        m = re.match(rf"^#+\s*(?:(?:File\s*\d+:|\d+\.)\s*)?`?({_NAME})`?\s*$", stripped)
        if m:
            accept(m.group(1))
        # **`summary.json`** or **summary.json** (bold, numbered lists)
        m = re.match(rf"^(?:\d+\.\s*)?\*\*`?({_NAME})`?\*\*", stripped)
        if m:
            accept(m.group(1))
        # /output/... and /app/output/... paths
        for m in re.finditer(rf"/(?:app/)?output/({_NAME})", line):
            accept(m.group(1))
        # write/produce/save verbs
        for m in re.finditer(rf"[Ww]rites?\s+(?:a\s+|an\s+|the\s+|one\s+)?`?({_NAME})", line):
            accept(m.group(1))
        for m in re.finditer(rf"[Pp]roduce\s+`?({_NAME})", line):
            accept(m.group(1))
        # bare backticked names anywhere
        for m in re.finditer(rf"`({_NAME})`", line):
            accept(m.group(1))

    deliverables = list(found.values())
    if not deliverables:
        return deliverables

    # Shape pass 1: nearest fenced json block after any mention of each file.
    fence_spans: list[tuple[int, int, str]] = []
    for m in _FENCE_JSON.finditer(text):
        start_line = text[: m.start()].count("\n")
        fence_spans.append((start_line, m.start(), m.group(1)))

    mention_lines: dict[str, int] = {}
    for i, line in enumerate(lines):
        for name in found:
            if name in line:
                mention_lines.setdefault(name, i)

    for name, d in found.items():
        if not name.endswith(".json"):
            continue
        mi = mention_lines.get(name)
        if mi is None:
            continue
        best: tuple[int, str] | None = None
        for start_line, pos, body in fence_spans:
            if mi <= start_line <= mi + 12:
                if best is None or start_line < best[0]:
                    best = (start_line, body)
        if best is not None:
            try:
                json.loads(best[1])
                d.json_example = best[1]
            except (json.JSONDecodeError, ValueError):
                pass

    # Shape pass 2/3: keys from bullets / CSV columns from tables, per section.
    current: Deliverable | None = None
    expect_keys = False
    for line in lines:
        stripped = line.strip()
        m = re.match(rf"^#+\s*(?:(?:File\s*\d+:|\d+\.)\s*)?`?({_NAME})`?\s*$", stripped)
        bold = re.match(rf"^(?:\d+\.\s*)?\*\*`?({_NAME})`?\*\*", stripped)
        if m or bold:
            current = found.get(_clean((m or bold).group(1)))
            expect_keys = False
            continue
        if current is None:
            continue
        if re.search(r"[Ii]nclude (?:these|the following) keys", line):
            expect_keys = True
            continue
        if current.filename.endswith(".json"):
            bm = _BULLET_KEY.match(line)
            if bm and (expect_keys or not current.json_keys):
                if bm.group(1) not in current.json_keys:
                    current.json_keys.append(bm.group(1))
        elif current.filename.endswith(".csv"):
            tm = _TABLE_CELL.match(line)
            if tm and tm.group(1).strip() and tm.group(1).strip().lower() not in (
                "column",
                "field",
            ):
                col = tm.group(1).strip()
                if col not in current.csv_columns:
                    current.csv_columns.append(col)
            else:
                bm = _BULLET_KEY.match(line)
                if bm and not current.csv_columns:
                    current.csv_columns.append(bm.group(1))
    return deliverables
