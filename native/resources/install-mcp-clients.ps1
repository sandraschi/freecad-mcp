#Requires -Version 5.1
<#
.SYNOPSIS
Register (or remove) one MCP server in every detected AI client on this Windows machine.

.DESCRIPTION
CANONICAL COPY. Installers (Tauri/NSIS) vendor this file into their resources, because an
installed app cannot reach the central repo. Drift is checked by audit-mcpb-bundles.ps1.

Clients: Claude Desktop, Cursor, Antigravity, Windsurf, OpenCode (JSON config files) and
Claude Code (through its own `claude mcp` CLI, never by editing ~/.claude.json).
Only clients that are actually installed are touched. For each config file the script
backs it up (timestamped .bak next to it), MERGES a single entry (never replaces the file),
and is idempotent. -Uninstall removes only the entry it owns.

OpenCode's config may contain comments (JSONC) which Windows PowerShell 5.1 cannot parse;
in that case the file is left untouched and the manual snippet is printed.

.EXAMPLE
.\install-mcp-clients.ps1 -Name onenote-mcp -Command "C:\...\onenote-mcp-backend.exe" -Env @{ MCP_TRANSPORT = 'stdio' }
.\install-mcp-clients.ps1 -Name onenote-mcp -List
.\install-mcp-clients.ps1 -Name onenote-mcp -Uninstall
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Name,
    [string]$Command,
    [string[]]$Arguments = @(),
    [hashtable]$Env = @{},
    # KEY=VALUE pairs; the way to pass env when invoked via `powershell -File` (installers).
    [string[]]$EnvPairs = @(),
    [ValidateSet('claude-desktop', 'cursor', 'antigravity', 'windsurf', 'opencode', 'claude-code')]
    [string[]]$Clients,
    [switch]$Uninstall,
    [switch]$List,
    [switch]$DryRun,
    # Machine-readable result: one JSON array [{id,label,status,detail}] on stdout, nothing else.
    # status: not-found | present | absent | registered | updated | removed | skipped | dry-run
    [switch]$Json,
    # Test hook: resolve USERPROFILE / APPDATA under this folder instead of the real ones.
    [string]$ConfigRoot
)
$ErrorActionPreference = 'Stop'

if (-not $Uninstall -and -not $List -and -not $Command) { throw '-Command is required unless -Uninstall or -List.' }
foreach ($p in $EnvPairs) {
    $i = $p.IndexOf('=')
    if ($i -lt 1) { throw "-EnvPairs entry must be KEY=VALUE, got '$p'" }
    $Env[$p.Substring(0, $i)] = $p.Substring($i + 1)
}
$userHome = if ($ConfigRoot) { Join-Path $ConfigRoot 'home' } else { $env:USERPROFILE }
$appData = if ($ConfigRoot) { Join-Path $ConfigRoot 'appdata' } else { $env:APPDATA }
$utf8 = New-Object System.Text.UTF8Encoding($false)

# name, detect-dir, config file, entries key, shape
$defs = @(
    @{ Id = 'claude-desktop'; Label = 'Claude Desktop'; Dir = "$appData\Claude"; File = "$appData\Claude\claude_desktop_config.json"; Key = 'mcpServers'; Shape = 'std' },
    @{ Id = 'cursor'; Label = 'Cursor'; Dir = "$userHome\.cursor"; File = "$userHome\.cursor\mcp.json"; Key = 'mcpServers'; Shape = 'std' },
    @{ Id = 'antigravity'; Label = 'Antigravity'; Dir = "$userHome\.gemini\antigravity"; File = "$userHome\.gemini\antigravity\mcp_config.json"; Key = 'mcpServers'; Shape = 'std' },
    @{ Id = 'windsurf'; Label = 'Windsurf'; Dir = "$userHome\.codeium\windsurf"; File = "$userHome\.codeium\windsurf\mcp_config.json"; Key = 'mcpServers'; Shape = 'std' },
    @{ Id = 'opencode'; Label = 'OpenCode'; Dir = "$userHome\.config\opencode"; File = "$userHome\.config\opencode\opencode.json"; Key = 'mcp'; Shape = 'opencode' }
)
if ($Clients) { $defs = $defs | Where-Object { $Clients -contains $_.Id } }

function Read-JsonFile([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) { return $null }
    $text = [IO.File]::ReadAllText($Path).TrimStart([char]0xFEFF)
    if ($text.Trim() -eq '') { return [pscustomobject]@{} }
    # Comments (JSONC) would be silently dropped on rewrite, so refuse. Look only OUTSIDE string
    # literals: a glob like "src/**/*.ts" inside a value is not a comment.
    $outsideStrings = [regex]::Replace($text, '"(?:\\.|[^"\\])*"', '""')
    if ($outsideStrings -match '//' -or $outsideStrings -match '/\*') { throw 'JSONC' }
    return ($text | ConvertFrom-Json)
}

function New-Entry($shape) {
    if ($shape -eq 'opencode') {
        $e = [ordered]@{ type = 'local'; command = @($Command) + @($Arguments); enabled = $true }
        if ($Env.Count) { $e['environment'] = $Env }
        return [pscustomobject]$e
    }
    $e = [ordered]@{ command = $Command }
    if ($Arguments.Count) { $e['args'] = @($Arguments) }
    if ($Env.Count) { $e['env'] = $Env }
    return [pscustomobject]$e
}

$results = New-Object System.Collections.ArrayList
$idByLabel = @{ 'Claude Code' = 'claude-code' }
foreach ($d0 in $defs) { $idByLabel[$d0.Label] = $d0.Id }

function Write-Result($label, $status, $detail) {
    [void]$results.Add([pscustomobject]@{ id = $idByLabel[$label]; label = $label; status = $status; detail = [string]$detail })
    if ($Json) { return }
    $color = switch ($status) { 'registered' { 'Green' } 'updated' { 'Green' } 'removed' { 'Green' } 'present' { 'Cyan' } 'skipped' { 'Yellow' } default { 'Gray' } }
    Write-Host ("  {0,-15} {1,-11} {2}" -f $label, $status, $detail) -ForegroundColor $color
}

foreach ($d in $defs) {
    if (-not (Test-Path -LiteralPath $d.Dir)) { Write-Result $d.Label 'not-found' ''; continue }
    try { $cfg = Read-JsonFile $d.File }
    catch {
        $why = if ($_.Exception.Message -eq 'JSONC') { 'config has comments' } else { "config is not valid JSON ($($_.Exception.Message))" }
        Write-Result $d.Label 'skipped' "$why; left untouched. Add '$Name' manually to $($d.File)"
        continue
    }
    $has = $cfg -and $cfg.PSObject.Properties[$d.Key] -and $cfg.($d.Key).PSObject.Properties[$Name]

    if ($List) { Write-Result $d.Label ($(if ($has) { 'present' } else { 'absent' })) $d.File; continue }
    if ($Uninstall -and -not $has) { Write-Result $d.Label 'absent' ''; continue }
    if ($DryRun) { Write-Result $d.Label 'dry-run' $d.File; continue }

    if ($null -eq $cfg) { $cfg = [pscustomobject]@{} }
    if (Test-Path -LiteralPath $d.File) {
        $bak = "$($d.File)." + (Get-Date -Format 'yyyyMMdd_HHmmss') + '.bak'
        Copy-Item -LiteralPath $d.File $bak
    }
    if (-not $cfg.PSObject.Properties[$d.Key]) { $cfg | Add-Member -NotePropertyName $d.Key -NotePropertyValue ([pscustomobject]@{}) }
    if ($Uninstall) {
        $cfg.($d.Key).PSObject.Properties.Remove($Name)
        $status = 'removed'
    } else {
        $cfg.($d.Key) | Add-Member -NotePropertyName $Name -NotePropertyValue (New-Entry $d.Shape) -Force
        $status = if ($has) { 'updated' } else { 'registered' }
    }
    New-Item -ItemType Directory -Force -Path (Split-Path $d.File -Parent) | Out-Null
    [IO.File]::WriteAllText($d.File, ($cfg | ConvertTo-Json -Depth 32), $utf8)
    Write-Result $d.Label $status $d.File
}

# Claude Code: use its own CLI (its ~/.claude.json holds much unrelated state; never hand-edit it).
if (-not $Clients -or $Clients -contains 'claude-code') {
    $cc = Get-Command claude -ErrorAction SilentlyContinue
    # `claude mcp ...` writes failures to stderr; under -ErrorAction Stop (PS 5.1) that becomes a
    # terminating NativeCommandError, so run it with Continue and judge by exit code only.
    function Invoke-Claude([string[]]$CliArgs) {
        $prev = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
        try { & claude @CliArgs *> $null; return $LASTEXITCODE } finally { $ErrorActionPreference = $prev }
    }
    if (-not $cc -or $ConfigRoot) { Write-Result 'Claude Code' 'not-found' '' }
    elseif ($List) { Write-Result 'Claude Code' ($(if ((Invoke-Claude @('mcp', 'get', $Name)) -eq 0) { 'present' } else { 'absent' })) '(user scope)' }
    elseif ($DryRun) { Write-Result 'Claude Code' 'dry-run' '' }
    elseif ($Uninstall) { [void](Invoke-Claude @('mcp', 'remove', '--scope', 'user', $Name)); Write-Result 'Claude Code' 'removed' '(user scope)' }
    else {
        [void](Invoke-Claude @('mcp', 'remove', '--scope', 'user', $Name))
        $ccArgs = @('mcp', 'add', '--scope', 'user', $Name)
        foreach ($k in $Env.Keys) { $ccArgs += @('-e', "$k=$($Env[$k])") }
        $ccArgs += @('--', $Command) + $Arguments
        Write-Result 'Claude Code' ($(if ((Invoke-Claude $ccArgs) -eq 0) { 'registered' } else { 'skipped' })) '(user scope)'
    }
}
if ($Json) { ConvertTo-Json -InputObject @($results) -Depth 4 -Compress }
else { Write-Host 'Restart the AI client(s) above to load the change.' }
