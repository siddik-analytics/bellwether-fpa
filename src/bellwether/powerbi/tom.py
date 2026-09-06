"""Validate the semantic model with Microsoft's own TMDL parser — criterion 5.33.

ADR 0022's fourth countermeasure requires one external authority per generated artifact, and
says a manual gate is acceptable only where the authority cannot be automated. For the semantic
model it can be, and this module is that gate.

The Tabular Object Model — `Microsoft.AnalysisServices.Tabular` — contains the same TMDL
deserializer Power BI Desktop uses. It ships with several Microsoft tools, DAX Studio among them,
so where one of those is installed the model can be parsed by the real thing without Power BI and
without a human. `TmdlSerializer.DeserializeDatabaseFromFolder` either returns a model or raises
with the document, line number and reason.

This authority earned its place immediately. The project passed the project's own structural
validator and was still rejected here, because a `///` description line followed by a blank line
describes nothing:

    Parsing error type - InvalidLineType
    Detailed error - Unexpected line type: Empty!
    Document - './tables/Measures'
    Line Number - 5

**What it does not cover.** TOM parses and inspects the *model*. It does not read `report.json`,
it does not connect to an engine, and it therefore evaluates no DAX. Criterion 5.30 still needs
Power BI Desktop for the report, and 5.15 still needs it for the numbers.
"""

from __future__ import annotations

import json
import pathlib
import shutil
import subprocess

#: Places the Tabular assembly ships. First match wins; all are ordinary installs, none is a
#: dependency this project declares.
SEARCH_PATHS: tuple[str, ...] = (
    r"C:\Program Files\DAX Studio\bin",
    r"C:\Program Files (x86)\DAX Studio\bin",
    r"C:\Program Files\Tabular Editor 3",
    r"C:\Program Files (x86)\Tabular Editor",
    r"C:\Program Files\Microsoft Power BI Desktop\bin",
)

ASSEMBLY = "Microsoft.AnalysisServices.Tabular.dll"


def find_assembly() -> pathlib.Path | None:
    """Where TOM lives on this machine, or None if no tool that ships it is installed."""
    for directory in SEARCH_PATHS:
        candidate = pathlib.Path(directory) / ASSEMBLY
        if candidate.exists():
            return candidate
    return None


def available() -> bool:
    return find_assembly() is not None and shutil.which("powershell") is not None


#: PowerShell rather than a Python .NET bridge on purpose: `pythonnet` would be a new dependency
#: for a check that must degrade to "skipped" wherever the assembly is absent, and PowerShell can
#: load a .NET assembly with no CLI, no SDK and nothing installed for this project's sake.
_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
Add-Type -Path '{assembly}'
try {{
    $serializer = [Microsoft.AnalysisServices.Tabular.TmdlSerializer]
    $db = $serializer::DeserializeDatabaseFromFolder('{folder}')
    $m = $db.Model
    $tables = @()
    foreach ($t in $m.Tables) {{
        $tables += [ordered]@{{
            name         = $t.Name
            dataCategory = [string]$t.DataCategory
            columns      = @($t.Columns | ForEach-Object {{ [ordered]@{{
                                name = $_.Name
                                dataType = [string]$_.DataType
                                isHidden = [bool]$_.IsHidden
                                isKey = [bool]$_.IsKey
                                summarizeBy = [string]$_.SummarizeBy
                            }} }})
            measures     = @($t.Measures | ForEach-Object {{ [ordered]@{{
                                name = $_.Name
                                expression = $_.Expression
                                formatString = [string]$_.FormatString
                                displayFolder = [string]$_.DisplayFolder
                            }} }})
            partitions   = @($t.Partitions | ForEach-Object {{ $_.Name }})
        }}
    }}
    $relationships = @($m.Relationships | ForEach-Object {{ [ordered]@{{
        from = $_.FromTable.Name + '[' + $_.FromColumn.Name + ']'
        to   = $_.ToTable.Name + '[' + $_.ToColumn.Name + ']'
        crossFiltering = [string]$_.CrossFilteringBehavior
        fromCardinality = [string]$_.FromCardinality
        toCardinality = [string]$_.ToCardinality
    }} }})
    $result = [ordered]@{{
        ok = $true
        tables = $tables
        relationships = $relationships
        expressions = @($m.Expressions | ForEach-Object {{ $_.Name }})
    }}
}} catch {{
    $result = [ordered]@{{ ok = $false; error = $_.Exception.Message }}
}}
$result | ConvertTo-Json -Depth 8 -Compress
"""


def parse_model(definition_dir: pathlib.Path) -> dict:
    """Parse a TMDL definition folder with TOM. Returns the model, or the parser's own error."""
    assembly = find_assembly()
    if assembly is None:
        raise RuntimeError(f"{ASSEMBLY} not found; install DAX Studio or Tabular Editor")

    script = _SCRIPT.format(
        assembly=str(assembly), folder=str(pathlib.Path(definition_dir).resolve())
    )
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )
    output = completed.stdout.strip()
    if not output:
        return {"ok": False, "error": completed.stderr.strip()[-2000:] or "no output"}
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        return {"ok": False, "error": output[-2000:]}
