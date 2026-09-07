"""Query the live model in Power BI Desktop's own engine — criterion 5.15.

While a PBIP is open, Desktop hosts a local Analysis Services instance holding the loaded model.
Connecting to it over XMLA and running DAX is the real check the phase 5 spec described and could
not perform: **the measures are evaluated by the engine that will evaluate them in production**,
with filter context, relationship propagation and blank semantics all real.

It is a better check than the one originally specified. Exporting a table visual to CSV reads a
*rendering* — a visual's formatting, its own filters, and whatever the author put on the page sit
between the measure and the number. A DAX query against the engine has none of that in the way.

The instance is ephemeral: it exists only while Desktop has the project open, and its port changes
every session. So this is discovery-then-connect, and everything here skips cleanly when nothing
is running rather than failing — a closed Desktop is not a defect in the model.
"""

from __future__ import annotations

import json
import pathlib
import shutil
import subprocess

from bellwether.powerbi import tom

ADOMD_ASSEMBLY = "Microsoft.AnalysisServices.AdomdClient.dll"

#: Where Desktop writes the workspace port, for the installs that use a file. Checked after the
#: process, because the process is authoritative and the file can be stale.
PORT_FILE_ROOTS = (
    r"Microsoft\Power BI Desktop\AnalysisServicesWorkspaces",
    r"Microsoft\Power BI Desktop Store App\AnalysisServicesWorkspaces",
)


def find_adomd() -> pathlib.Path | None:
    """The ADOMD client, from any tool that ships it."""
    for directory in tom.SEARCH_PATHS:
        candidate = pathlib.Path(directory) / ADOMD_ASSEMBLY
        if candidate.exists():
            return candidate
    return None


_DISCOVER = r"""
$ErrorActionPreference = 'SilentlyContinue'
$ports = @()
foreach ($proc in Get-Process msmdsrv) {
    foreach ($c in Get-NetTCPConnection -OwningProcess $proc.Id -State Listen) {
        $ports += [int]$c.LocalPort
    }
}
if ($ports.Count -eq 0) {
    foreach ($rel in @(__ROOTS__)) {
        $root = Join-Path $env:LOCALAPPDATA $rel
        if (Test-Path $root) {
            foreach ($f in Get-ChildItem -Path $root -Recurse -Filter 'msmdsrv.port.txt') {
                $text = (Get-Content $f.FullName -Raw)
                $clean = $text -replace '[^0-9]', ''
                if ($clean) { $ports += [int]$clean }
            }
        }
    }
}
@{ ports = @($ports | Sort-Object -Unique) } | ConvertTo-Json -Compress
"""


def find_ports() -> list[int]:
    """Every port a local Analysis Services instance is listening on, or an empty list."""
    if shutil.which("powershell") is None:
        return []
    roots = ", ".join(f"'{r}'" for r in PORT_FILE_ROOTS)
    completed = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            _DISCOVER.replace("__ROOTS__", roots),
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    try:
        payload = json.loads(completed.stdout.strip() or "{}")
    except json.JSONDecodeError:
        return []
    ports = payload.get("ports") or []
    return [ports] if isinstance(ports, int) else list(ports)


def available() -> bool:
    return find_adomd() is not None and bool(find_ports())


#: `LoadFrom`, not `Add-Type`: the ADOMD assembly fails to load through `Add-Type` on this
#: runtime with a type-loader exception, and loads cleanly through the reflection API.
_QUERY = r"""
$ErrorActionPreference = 'Stop'
$asm = [System.Reflection.Assembly]::LoadFrom('__ADOMD__')
$connection = New-Object Microsoft.AnalysisServices.AdomdClient.AdomdConnection(
    'Data Source=localhost:__PORT__')
$connection.Open()
try {
    if (-not '__DATABASE__') {
        $catalog = $connection.Databases | Select-Object -First 1
    }
    $command = $connection.CreateCommand()
    $command.CommandText = @'
__DAX__
'@
    $reader = $command.ExecuteReader()
    $columns = @()
    for ($i = 0; $i -lt $reader.FieldCount; $i++) { $columns += $reader.GetName($i) }
    $rows = @()
    while ($reader.Read()) {
        $row = [ordered]@{}
        for ($i = 0; $i -lt $reader.FieldCount; $i++) {
            $row[$columns[$i]] = $reader.GetValue($i)
        }
        $rows += $row
    }
    $reader.Close()
    @{ ok = $true; columns = $columns; rows = $rows } | ConvertTo-Json -Depth 6 -Compress
} finally {
    $connection.Close()
}
"""


def query(dax: str, port: int | None = None) -> dict:
    """Run a DAX query against the live instance. Returns rows, or the engine's own error."""
    adomd = find_adomd()
    if adomd is None:
        return {"ok": False, "error": f"{ADOMD_ASSEMBLY} not found"}
    ports = [port] if port else find_ports()
    if not ports:
        return {"ok": False, "error": "no local Analysis Services instance is listening"}

    last: dict = {"ok": False, "error": "no port answered"}
    for candidate in ports:
        script = (
            _QUERY.replace("__ADOMD__", str(adomd))
            .replace("__PORT__", str(candidate))
            .replace("__DATABASE__", "")
            .replace("__DAX__", dax)
        )
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=600,
        )
        output = completed.stdout.strip()
        if not output:
            last = {"ok": False, "error": completed.stderr.strip()[-1500:] or "no output"}
            continue
        try:
            result = json.loads(output)
        except json.JSONDecodeError:
            last = {"ok": False, "error": output[-1500:]}
            continue
        result["port"] = candidate
        if result.get("ok"):
            rows = result.get("rows") or []
            result["rows"] = [rows] if isinstance(rows, dict) else rows
            return result
        last = result
    return last


#: The reconciliation query. `SUMMARIZECOLUMNS` over the grain the semantic layer works at, so
#: the comparison is row for row rather than one total against another — a total can agree while
#: every month inside it is wrong.
RECONCILIATION_DAX = """
EVALUATE
SUMMARIZECOLUMNS(
    fact_metric[Month],
    fact_metric[Version],
    fact_metric[Scenario],
    "NetRevenue", [Net Revenue],
    "EBITDA", [EBITDA],
    "GrossProfit", [Gross Profit]
)
ORDER BY fact_metric[Month], fact_metric[Version], fact_metric[Scenario]
"""
