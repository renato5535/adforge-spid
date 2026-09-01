# AdForge Bot — wrapper do scheduler (Task Scheduler)
# Executa python bot.py --once: processa updates pendentes e sai.
# Agendado a cada 2 minutos (07:00-23:00). Latência máxima: 2min.
$ErrorActionPreference = "Stop"
$adforge   = Join-Path $env:USERPROFILE ".adforge"
$botDir    = Join-Path $adforge "bot"
$logsDir   = Join-Path $adforge "bot"
$schedLog  = Join-Path $logsDir "bot_scheduler.log"
$envFile   = Join-Path $adforge ".env"

function Write-Log($msg) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "$ts  $msg`n"
    [System.IO.File]::AppendAllText($schedLog, $line, [System.Text.Encoding]::UTF8)
}

# 1) Python disponível?
$py = (Get-Command python -ErrorAction SilentlyContinue)
if (-not $py) { $py = (Get-Command py -ErrorAction SilentlyContinue) }
if (-not $py) {
    Write-Log "ERRO: Python não encontrado no PATH. Abortando."
    exit 1
}

# 2) .env presente?
if (-not (Test-Path -LiteralPath $envFile)) {
    Write-Log "ERRO: $envFile ausente. Abortando."
    exit 1
}

# 3) UTF-8 no Python
$env:PYTHONUTF8       = "1"
$env:PYTHONIOENCODING = "utf-8"

# 4) Executa bot --once (processa updates pendentes e sai em ~2s)
$botPy = Join-Path $botDir "bot.py"
try {
    & $py.Source $botPy --once
    $code = $LASTEXITCODE
    if ($code -ne 0) {
        Write-Log "bot.py --once saiu com código $code"
    }
    exit $code
} catch {
    Write-Log "ERRO: $($_.Exception.Message)"
    exit 1
}
