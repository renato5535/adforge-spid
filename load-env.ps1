# AdForge env loader — le ~/.adforge/.env e injeta as variaveis no processo atual.
# Este arquivo NAO contem segredos. Seguro para versionar/inspecionar.
$envFile = Join-Path $HOME '.adforge/.env'
if (Test-Path $envFile) {
    Get-Content -LiteralPath $envFile | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith('#') -and $line.Contains('=')) {
            $idx = $line.IndexOf('=')
            $key = $line.Substring(0, $idx).Trim()
            $val = $line.Substring($idx + 1).Trim()
            if ($key) { Set-Item -Path "Env:$key" -Value $val }
        }
    }
}
