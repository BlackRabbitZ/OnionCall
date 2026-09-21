param([int]$SocksPort=19051)
$ErrorActionPreference='Stop';$Root=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path;Set-Location $Root
function Find-Tor { if($env:ONIONCALL_TOR_BINARY -and(Test-Path -LiteralPath $env:ONIONCALL_TOR_BINARY)){return $env:ONIONCALL_TOR_BINARY};$c=Get-Command tor.exe -ErrorAction SilentlyContinue;if($c){return $c.Source};$xs=@((Join-Path $env:ProgramFiles 'Tor Browser\Browser\TorBrowser\Tor\tor.exe'),(Join-Path $env:LOCALAPPDATA 'Tor Browser\Browser\TorBrowser\Tor\tor.exe'),(Join-Path $env:USERPROFILE 'Desktop\Tor Browser\Browser\TorBrowser\Tor\tor.exe'));foreach($x in $xs){if($x -and(Test-Path -LiteralPath $x)){return $x}};return $null }
$Git=(Get-Command git.exe -ErrorAction SilentlyContinue).Source;if(-not$Git){throw 'git.exe fehlt; kein unsicherer Fallback.'};$Tor=Find-Tor;if(-not$Tor){throw 'tor.exe fehlt; kein unsicherer Clearnet-Fallback.'}
$Remote=(& $Git config --get remote.origin.url).Trim();if($Remote -notin @('https://github.com/BlackRabbitZ/OnionCall.git','git@github.com:BlackRabbitZ/OnionCall.git')){throw "Unerwartete Remote-URL: $Remote"}
$Tmp=Join-Path $env:TEMP ('onioncall-update-'+[guid]::NewGuid().ToString('N'));$Data=Join-Path $Tmp 'data';New-Item -ItemType Directory -Path $Data -Force|Out-Null;$Torrc=Join-Path $Tmp 'torrc';$Log=Join-Path $Tmp 'tor.log'
@"
DataDirectory $Data
SocksPort 127.0.0.1:$SocksPort
SafeSocks 1
TestSocks 1
SafeLogging 1
Log notice file $Log
"@|Set-Content -LiteralPath $Torrc -Encoding ASCII
$TP=Start-Process -FilePath $Tor -ArgumentList @('-f',$Torrc) -PassThru -WindowStyle Hidden
try{$deadline=(Get-Date).AddMinutes(3);do{Start-Sleep -Milliseconds 300;if($TP.HasExited){throw 'Tor wurde beim privaten Update beendet.'};$ready=Test-NetConnection -ComputerName 127.0.0.1 -Port $SocksPort -InformationLevel Quiet -WarningAction SilentlyContinue}until(($ready -and(Test-Path $Log)-and((Get-Content $Log -Raw)-match 'Bootstrapped 100%'))-or(Get-Date)-gt$deadline);if((Get-Date)-gt$deadline){throw 'Tor wurde nicht rechtzeitig bereit.'};Write-Host '[1/2] Git-Fetch ausschließlich über Tor …';& $Git -c "http.proxy=socks5h://127.0.0.1:$SocksPort" -c "https.proxy=socks5h://127.0.0.1:$SocksPort" fetch --tags --prune origin;if($LASTEXITCODE-ne0){throw 'Git-Fetch über Tor fehlgeschlagen.'};& $Git checkout main;if($LASTEXITCODE-ne0){throw 'git checkout main fehlgeschlagen.'};& $Git merge --ff-only origin/main;if($LASTEXITCODE-ne0){throw 'Fast-forward fehlgeschlagen.'};Write-Host '[2/2] Fertig. Kein Clearnet-Fallback.'}finally{if($TP -and -not$TP.HasExited){Stop-Process -Id $TP.Id -Force -ErrorAction SilentlyContinue};Remove-Item -LiteralPath $Tmp -Recurse -Force -ErrorAction SilentlyContinue}
