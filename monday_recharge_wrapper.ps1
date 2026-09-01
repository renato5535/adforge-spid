# AdForge — wrapper da automação de recarga de segunda-feira
$ErrorActionPreference = "Stop"
$adforge  = Join-Path $env:USERPROFILE ".adforge"
$logsDir  = Join-Path $adforge "logs"
$schedLog = Join-Path $logsDir "monday_recharge.log"
New-Item -ItemType Directory -Force -Path $logsDir | Out-Null

function Write-Log($msg) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    [System.IO.File]::AppendAllText($schedLog, "$ts  $msg`n", [System.Text.Encoding]::UTF8)
}

Write-Log "=== monday_recharge_auto START ==="
$py314 = "C:\Users\User\AppData\Local\Programs\Python\Python314\python.exe"
$py    = if (Test-Path $py314) { $py314 } else { (Get-Command python).Source }
$script = Join-Path $adforge "monday_recharge_auto.py"

$env:PYTHONUTF8       = "1"
$env:PYTHONIOENCODING = "utf-8"

Write-Log "Python: $py"
try {
    & $py $script
    Write-Log "Finalizado exit=$LASTEXITCODE"
} catch {
    Write-Log "ERRO: $($_.Exception.Message)"
    exit 1
}
