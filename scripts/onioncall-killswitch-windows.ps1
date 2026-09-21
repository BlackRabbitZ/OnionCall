param([Parameter(Position=0)][ValidateSet('install','remove','status')][string]$Action='status')
$ErrorActionPreference='Stop'
$Root=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Python=Join-Path $Root '.venv\Scripts\python.exe'
$Rule4='BRZ OnionCall Killswitch IPv4'; $Rule6='BRZ OnionCall Killswitch IPv6'
function Test-Administrator { $id=[Security.Principal.WindowsIdentity]::GetCurrent(); $p=New-Object Security.Principal.WindowsPrincipal($id); $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator) }
function Get-Rule([string]$Name){ Get-NetFirewallRule -DisplayName $Name -ErrorAction SilentlyContinue }
if($Action -eq 'status'){$r4=Get-Rule $Rule4;$r6=Get-Rule $Rule6;if($r4 -and $r6){Write-Host '[OK] Windows-Killswitch ist aktiv.' -ForegroundColor Green;Write-Host "Geschützter Python-Interpreter: $Python";exit 0};Write-Host '[WARNUNG] Windows-Killswitch ist nicht vollständig aktiv.' -ForegroundColor Yellow;exit 1}
if(-not(Test-Administrator)){
    $argLine = "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`" $Action"
    $proc = Start-Process powershell.exe -Verb RunAs -Wait -PassThru -ArgumentList $argLine
    exit $proc.ExitCode
}
if($Action -eq 'remove'){Get-Rule $Rule4|Remove-NetFirewallRule -ErrorAction SilentlyContinue;Get-Rule $Rule6|Remove-NetFirewallRule -ErrorAction SilentlyContinue;Write-Host '[OK] Windows-Killswitch wurde entfernt.' -ForegroundColor Green;exit 0}
if(-not(Test-Path -LiteralPath $Python -PathType Leaf)){Write-Error "Lokales OnionCall-Python fehlt: $Python. Zuerst py OnionCall-Setup.py ausführen."}
Get-Rule $Rule4|Remove-NetFirewallRule -ErrorAction SilentlyContinue;Get-Rule $Rule6|Remove-NetFirewallRule -ErrorAction SilentlyContinue
New-NetFirewallRule -DisplayName $Rule4 -Direction Outbound -Action Block -Program $Python -Profile Any -RemoteAddress @('0.0.0.0-126.255.255.255','128.0.0.0-255.255.255.255')|Out-Null
New-NetFirewallRule -DisplayName $Rule6 -Direction Outbound -Action Block -Program $Python -Profile Any -RemoteAddress @('::','::2-ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff')|Out-Null
Write-Host '[OK] Windows-Killswitch wurde aktiviert.' -ForegroundColor Green
Write-Host 'OnionCall-Python darf nur Loopback erreichen; tor.exe bleibt separat netzwerkfähig.'
Write-Host "Geschützter Python-Interpreter: $Python"
