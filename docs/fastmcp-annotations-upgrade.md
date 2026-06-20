# Tool Annotations — FastMCP 3.4+ Fleet Standard

**Last updated:** 2026-06-20

---

## What are tool annotations?

Every MCP tool should tell the client whether it reads, writes, or destroys data. This lets AI agents make smarter decisions about which tools to call and in what order.

| Annotation | Meaning | Example tools |
|:---|:---|:---|
| `READ_ONLY` | Tool does **not** mutate state | `plan_info`, `cfd_status`, `freecad_status` |
| `MUTATING` | Tool creates or changes state | `step_to_stl`, `plan_extrude`, `bim_create_wall` |
| `DESTRUCTIVE` | Tool may delete or overwrite | `plan_modify` (with delete op), `marketplace_uninstall` |

## How to apply them

### Current approach (works with all FastMCP 3.x versions)

```python
from fastmcp import FastMCP

_README_ONLY = {"readonly": True}
_MUTATING = {}
# No constant for MUTATING — empty dict means "not readonly"

@mcp.tool(annotations=_README_ONLY)
async def plan_info(file_name: str) -> dict:
    """Read DXF metadata."""

@mcp.tool(annotations=_MUTATING)
async def step_to_stl(file_name: str) -> dict:
    """Convert STEP assembly to STL mesh."""
```

### Future approach (when the package catches up)

FastMCP 3.4's tool annotations module (`from fastmcp.tool.annotations import READ_ONLY, MUTATING, DESTRUCTIVE`) does **not exist in the currently shipped 3.4.2 package**. The constants are referenced in the fleet standard but the actual import path hasn't shipped yet. When it does, the pattern becomes:

```python
from fastmcp import FastMCP
from fastmcp.tool.annotations import READ_ONLY, MUTATING, DESTRUCTIVE

@mcp.tool(annotations=READ_ONLY)
async def plan_info(file_name: str) -> dict: ...
```

Until then, the dict pattern above is the correct approach. They are semantically identical.

### Migration path

```python
# Step 1 (today — dict format, works on all 3.x)
_README_ONLY = {"readonly": True}
_MUTATING = {}

# Step 2 (when fastmcp ships annotations module)
from fastmcp.tool.annotations import READ_ONLY, MUTATING
# Delete _README_ONLY and _MUTATING dicts
```

---

## Current fleet status

| Repo | fastmcp min | Annotations | Tools annotated |
|:---|:---:|:---:|:---:|
| freecad-mcp | >=3.4.2 | Dict pattern | 37/37 |
| qcad-mcp | >=3.4.2 | Dict pattern | 26/26 |
| blender-mcp | — | — | — |
| unity3d-mcp | — | — | — |
| inkscape-mcp | — | — | — |
| gimp-mcp | — | — | — |

---

## Fleet upgrade plan

### Phase 1: Baseline bump (safe, mechanical)

Update `pyproject.toml` in every fleet repo that depends on fastmcp:

```python
# Before
"fastmcp>=3.2.0"

# After
"fastmcp>=3.4.2"
```

This is safe because 3.4.x is backward-compatible. No code changes needed for this phase alone.

**Script:** `scripts/fleet-bump-fastmcp.ps1` (see below)

### Phase 2: Audit + annotate

For each repo, run a script that:

1. Finds all `@mcp.tool()` decorators in `src/*/tools/`
2. Reports which ones have `annotations=` and which don't
3. Adds `_MUTATING = {}` and `_README_ONLY = {"readonly": True}` dicts where needed
4. Adds `annotations=_README_ONLY` or `annotations=_MUTATING` to each bare decorator

**Script:** `scripts/fleet-annotate-tools.ps1` (see below)

### Phase 3: Constants migration (when the module ships)

When fastmcp releases a version with `from fastmcp.tool.annotations import READ_ONLY, MUTATING, DESTRUCTIVE`:

1. Run a fleet-wide grep for `_README_ONLY = {"readonly": True}` and `_MUTATING = {}`
2. Replace with the proper import
3. Replace `annotations=_README_ONLY` with `annotations=READ_ONLY`
4. Replace `annotations=_MUTATING` with `annotations=MUTATING`
5. Remove the dict definitions

---

## Safe batch upgrade scripts

### scripts/fleet-bump-fastmcp.ps1

```powershell
<#
.SYNOPSIS
    Bump fastmcp minimum version to 3.4.2 in all fleet repos.
#>
$repos = @(
    "D:\Dev\repos\freecad-mcp",
    "D:\Dev\repos\qcad-mcp",
    "D:\Dev\repos\blender-mcp",
    "D:\Dev\repos\inkscape-mcp",
    "D:\Dev\repos\gimp-mcp",
    "D:\Dev\repos\unity3d-mcp"
)

foreach ($repo in $repos) {
    $toml = Join-Path $repo "pyproject.toml"
    if (-not (Test-Path $toml)) { Write-Host "Skip $repo (no pyproject.toml)"; continue }
    $content = Get-Content $toml -Raw
    if ($content -notmatch 'fastmcp') { Write-Host "Skip $repo (no fastmcp dep)"; continue }
    
    # Backup
    $bak = "$toml.$(Get-Date -Format 'yyyyMMdd_HHmmss').bak"
    Copy-Item $toml $bak
    
    # Bump
    $content = $content -replace '"fastmcp>=3\.[0-9]+\.[0-9]+"', '"fastmcp>=3.4.2"'
    $content = $content -replace '"fastmcp==3\.[0-9]+\.[0-9]+"', '"fastmcp>=3.4.2"'
    Set-Content $toml $content
    Write-Host "Updated: $repo"
}
```

### scripts/fleet-annotate-tools.ps1

```powershell
<#
.SYNOPSIS
    Add annotation constants and annotate all @mcp.tool() decorators in a repo.
    Dry-run first with -DryRun flag.
.PARAMETER RepoPath
    Path to the repo root (e.g. D:\Dev\repos\freecad-mcp)
.PARAMETER DryRun
    If set, only report what would change without modifying files.
#>
param([string]$RepoPath, [switch]$DryRun)

$toolFiles = Get-ChildItem -Recurse -Path "$RepoPath\src" -Filter "*.py" | Select-String -Pattern "@mcp\.tool"
$errors = 0
$fixed = 0

foreach $file in $toolFiles.Path | Sort-Object -Unique {
    $content = Get-Content $file
    $hasReadme = $content -match '_README_ONLY'
    $hasMutating = $content -match '_MUTATING'
    $hasBareTools = $content -match '@mcp\.tool\(\)'
    
    if ($hasBareTools) {
        if ($DryRun) {
            Write-Host "[DRY-RUN] Would fix $file" -ForegroundColor Yellow
        } else {
            # Add dicts after imports if missing
            if (-not $hasReadme) {
                $bak = "$file.$(Get-Date -Format 'yyyyMMdd_HHmmss').bak"
                Copy-Item $file $bak
                # Find where to insert: after last import before first non-import line
                $lines = Get-Content $file
                $lastImport = 0
                for ($i = 0; $i -lt $lines.Count; $i++) {
                    if ($lines[$i] -match '^(import|from )') { $lastImport = $i }
                }
                $newLines = @()
                for ($i = 0; $i -le $lastImport; $i++) { $newLines += $lines[$i] }
                $newLines += ''
                $newLines += '_README_ONLY = {"readonly": True}'
                if (-not $hasMutating) { $newLines += '_MUTATING = {}' }
                for ($i = $lastImport + 1; $i -lt $lines.Count; $i++) { $newLines += $lines[$i] }
                Set-Content $file $newLines
                Write-Host "  Added dicts to: $file"
            }
            # Replace bare @mcp.tool() with annotated versions based on heuristics
            # (This part requires manual review — see guidelines below)
        }
        $fixed++
    } else {
        Write-Host "OK: $file"
    }
}

Write-Host "Done. $fixed files with issues, $errors errors."
```

### Manual annotation guidelines

After the script adds dicts, you still need to decide each tool's annotation type:

| Signal | Annotate as |
|:---|:---|
| Tool name starts with `get_`, `list_`, `search_`, `status`, `info`, `read_` | `READ_ONLY` |
| Tool name starts with `create_`, `add_`, `set_`, `update_`, `convert_`, `export_`, `import_` | `MUTATING` |
| Tool name starts with `delete_`, `remove_`, `clear_`, `purge_` | `DESTRUCTIVE` |
| Tool calls `run_` or `execute_` | Depends on side effects — review |
| Unsure | Default to `MUTATING` (safe overapproximation) |

---

## Version history

| Date | Version | Notes |
|:---|:---:|:---|
| 2026-06-20 | 1.0 | Initial fleet standard. Dict pattern accepted as 3.4.x fallback. |
