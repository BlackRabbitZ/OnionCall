param([int]$SocksPort = 19051)
$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $Root

function Find-Tor {
    if ($env:ONIONCALL_TOR_BINARY -and (Test-Path -LiteralPath $env:ONIONCALL_TOR_BINARY)) {
        return $env:ONIONCALL_TOR_BINARY
    }
    $cmd = Get-Command tor.exe -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $candidates = @(
        (Join-Path $env:ProgramFiles 'Tor Browser\Browser\TorBrowser\Tor\tor.exe'),
        (Join-Path $env:LOCALAPPDATA 'Tor Browser\Browser\TorBrowser\Tor\tor.exe'),
        (Join-Path $env:USERPROFILE 'Desktop\Tor Browser\Browser\TorBrowser\Tor\tor.exe')
    )
    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path -LiteralPath $candidate)) { return $candidate }
    }
    return $null
}

$GitCmd = Get-Command git.exe -ErrorAction SilentlyContinue
if (-not $GitCmd) { throw 'git.exe fehlt; kein unsicherer Fallback.' }
$Git = $GitCmd.Source
$Tor = Find-Tor
if (-not $Tor) { throw 'tor.exe fehlt; kein unsicherer Clearnet-Fallback.' }
$Remote = (& $Git config --get remote.origin.url).Trim()
if ($Remote -ne 'https://github.com/BlackRabbitZ/OnionCall.git') {
    throw "Windows-Privatupdate erlaubt nur die HTTPS-Remote über SOCKS5h; erhalten: $Remote"
}

$Tmp = Join-Path $env:TEMP ('onioncall-update-' + [guid]::NewGuid().ToString('N'))
$Data = Join-Path $Tmp 'data'
New-Item -ItemType Directory -Path $Data -Force | Out-Null
$Torrc = Join-Path $Tmp 'torrc'
$Log = Join-Path $Tmp 'tor.log'
@"
DataDirectory $Data
SocksPort 127.0.0.1:$SocksPort
SafeSocks 1
TestSocks 1
SafeLogging 1
Log notice file $Log
"@ | Set-Content -LiteralPath $Torrc -Encoding ASCII

$TorProcess = Start-Process -FilePath $Tor -ArgumentList @('-f', $Torrc) -PassThru -WindowStyle Hidden
try {
    $deadline = (Get-Date).AddMinutes(3)
    do {
        Start-Sleep -Milliseconds 300
        if ($TorProcess.HasExited) { throw 'Tor wurde beim privaten Update beendet.' }
        $ready = Test-NetConnection -ComputerName 127.0.0.1 -Port $SocksPort -InformationLevel Quiet -WarningAction SilentlyContinue
        $bootstrapped = (Test-Path $Log) -and ((Get-Content $Log -Raw) -match 'Bootstrapped 100%')
    } until (($ready -and $bootstrapped) -or (Get-Date) -gt $deadline)
    if ((Get-Date) -gt $deadline) { throw 'Tor wurde nicht rechtzeitig bereit.' }

    Write-Host '[1/4] Git-Fetch ausschließlich über Tor …'
    & $Git -c "http.proxy=socks5h://127.0.0.1:$SocksPort" -c "https.proxy=socks5h://127.0.0.1:$SocksPort" fetch --tags --prune origin
    if ($LASTEXITCODE -ne 0) { throw 'Git-Fetch über Tor fehlgeschlagen.' }

    $Target = (& $Git rev-parse --verify 'origin/main^{commit}').Trim()
    $Current = (& $Git rev-parse --verify 'main^{commit}').Trim()
    & $Git merge-base --is-ancestor $Current $Target
    if ($LASTEXITCODE -ne 0) { throw 'Update abgebrochen: origin/main ist kein Fast-Forward von lokalem main.' }

    Write-Host "[2/4] Ziel-Commit vor Installation verifizieren: $Target"
    $Verified = $false
    if ($env:ONIONCALL_TRUSTED_COMMIT) {
        if ($env:ONIONCALL_TRUSTED_COMMIT.Trim().ToLowerInvariant() -eq $Target.ToLowerInvariant()) {
            $Verified = $true
            Write-Host 'Commit stimmt mit ONIONCALL_TRUSTED_COMMIT überein.'
        } else {
            throw "Gepinnter Commit stimmt nicht mit Ziel-Commit $Target überein."
        }
    }

    if (-not $Verified) {
        & $Git verify-commit $Target *> $null
        if ($LASTEXITCODE -eq 0) {
            $Verified = $true
            Write-Host 'Commit-Signatur wurde lokal erfolgreich verifiziert.'
        }
    }

    if (-not $Verified) {
        $Tags = @(& $Git tag --points-at $Target)
        foreach ($Tag in $Tags) {
            if (-not $Tag) { continue }
            & $Git verify-tag $Tag *> $null
            if ($LASTEXITCODE -eq 0) {
                $Verified = $true
                Write-Host "Signierter Tag '$Tag' wurde lokal erfolgreich verifiziert."
                break
            }
        }
    }

    if (-not $Verified) {
        throw @"
Update abgebrochen: Ziel-Commit ist lokal nicht vertrauenswürdig verifiziert.
Für einen einmalig extern geprüften Commit vor dem Start setzen:
  `$env:ONIONCALL_TRUSTED_COMMIT='$Target'
Besser: zukünftige Release-Tags/Commits mit einem lokal vertrauenswürdigen GPG-/SSH-Key signieren.
"@
    }

    Write-Host '[3/4] Verifizierten Fast-Forward anwenden …'
    & $Git checkout main
    if ($LASTEXITCODE -ne 0) { throw 'git checkout main fehlgeschlagen.' }
    & $Git merge --ff-only $Target
    if ($LASTEXITCODE -ne 0) { throw 'Fast-forward fehlgeschlagen.' }

    Write-Host '[4/4] Lokales Paket aktualisieren – kein Clearnet-Fallback.'
    $Python = Join-Path $Root '.venv\Scripts\python.exe'
    if (Test-Path -LiteralPath $Python) {
        & $Python -m pip install --no-deps -e .
        if ($LASTEXITCODE -ne 0) { throw 'Lokale Paketinstallation fehlgeschlagen.' }
    }
} finally {
    if ($TorProcess -and -not $TorProcess.HasExited) {
        Stop-Process -Id $TorProcess.Id -Force -ErrorAction SilentlyContinue
    }
    Remove-Item -LiteralPath $Tmp -Recurse -Force -ErrorAction SilentlyContinue
}
