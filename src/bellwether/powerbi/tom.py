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

import functools
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

#: Power BI Desktop's own modelling assembly, which carries rules TOM does not. Found by walking
#: the Store package rather than a fixed path, because the version is in the folder name.
DESKTOP_PACKAGE_ROOT = r"C:\Program Files\WindowsApps"
DESKTOP_PACKAGE_PREFIX = "Microsoft.MicrosoftPowerBIDesktop_"
MODELER_ASSEMBLY = "Microsoft.PowerBI.Modeler.dll"


@functools.cache
def find_modeler() -> pathlib.Path | None:
    """`Microsoft.PowerBI.Modeler.dll`, wherever this machine's Desktop install put it.

    Asked of the package manager rather than found by globbing. Desktop installs as a Store
    package under ``WindowsApps``, which cannot be *listed* by an ordinary process even though a
    known path inside it opens fine — so a glob returns nothing and a direct path works.
    """
    for directory in SEARCH_PATHS:
        candidate = pathlib.Path(directory) / MODELER_ASSEMBLY
        if candidate.exists():
            return candidate
    if shutil.which("powershell") is None:
        return None
    completed = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            "(Get-AppxPackage -Name '*PowerBIDesktop*' | "
            "Sort-Object Version -Descending | Select-Object -First 1).InstallLocation",
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    location = completed.stdout.strip()
    if not location:
        return None
    candidate = pathlib.Path(location) / "bin" / MODELER_ASSEMBLY
    return candidate if candidate.exists() else None


def names_available() -> bool:
    return find_modeler() is not None and find_assembly() is not None


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


#: Desktop rejects a model whose object name differs from its own sanitised form. The rule, read
#: out of `ModelSchemaValidator.EnsureValidObjectName`, is exactly:
#:
#:     name != NameValidator.RemoveInvalidNameCharacters(name, objectType)  ->  reject
#:
#: It is not a reserved-word list, which is why it could not be guessed: `Measures` comes back as
#: `Measures 1`, and that inequality is the whole failure.
_NAMES_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
Add-Type -Path '{tabular}'
$modeler = [System.Reflection.Assembly]::LoadFrom('{modeler}')
$flags = [System.Reflection.BindingFlags]'Public,NonPublic,Static,Instance'
$validator = $modeler.GetType('Microsoft.PowerBI.Modeler.NameValidator')
$wanted = 'RemoveInvalidNameCharacters'
$named = $validator.GetMethods($flags) | Where-Object {{ $_.Name -eq $wanted }}
$sanitise = $named | Select-Object -First 1
$db = [Microsoft.AnalysisServices.Tabular.TmdlSerializer]::DeserializeDatabaseFromFolder('{folder}')
$bad = @()
function Check($name, $kind, $where) {{
    $out = $sanitise.Invoke($null, @($name, [Microsoft.AnalysisServices.Tabular.ObjectType]::$kind))
    if ($out -cne $name) {{
        $script:bad += [ordered]@{{ kind = $kind; where = $where; name = $name; fixed = $out }}
    }}
}}
foreach ($t in $db.Model.Tables) {{
    Check $t.Name 'Table' $t.Name
    foreach ($c in $t.Columns) {{ Check $c.Name 'Column' ($t.Name + '[' + $c.Name + ']') }}
    foreach ($m in $t.Measures) {{ Check $m.Name 'Measure' $m.Name }}
}}
@{{ ok = ($bad.Count -eq 0); offenders = $bad }} | ConvertTo-Json -Depth 6 -Compress
"""


def validate_names(definition_dir: pathlib.Path) -> dict:
    """Every object name, through Power BI Desktop's own validator — criterion 5.36.

    TOM parses a model that Desktop then refuses, so parsing is a weaker gate than it looks.
    This is the layer that catches the difference, and it is still not the whole of Desktop.
    """
    tabular, modeler = find_assembly(), find_modeler()
    if tabular is None or modeler is None:
        raise RuntimeError("need both the Tabular assembly and Power BI Desktop's Modeler")

    script = _NAMES_SCRIPT.format(
        tabular=str(tabular),
        modeler=str(modeler),
        folder=str(pathlib.Path(definition_dir).resolve()),
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
        result = json.loads(output)
    except json.JSONDecodeError:
        return {"ok": False, "error": output[-2000:]}
    offenders = result.get("offenders") or []
    if isinstance(offenders, dict):
        offenders = [offenders]
    return {"ok": bool(result.get("ok")), "offenders": offenders}
