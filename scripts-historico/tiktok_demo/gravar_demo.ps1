# Gravador de demo TikTok -- ffmpeg + Flask
# Uso: & "$env:USERPROFILE\.adforge\tiktok_demo\gravar_demo.ps1"
# Le TIKTOK_CLIENT_SECRET de ~/.adforge/.env

param(
    [Parameter(Mandatory=$false)]
    [string]$ClientSecret
)

# Carregar .env se secret nao foi passado como parametro
if (-not $ClientSecret) {
    $envFile = "$env:USERPROFILE\.adforge\.env"
    if (Test-Path $envFile) {
        Get-Content $envFile | Where-Object { $_ -match "^TIKTOK_CLIENT_SECRET=" } | ForEach-Object {
            $ClientSecret = ($_ -split "=", 2)[1].Trim('"').Trim("'")
        }
    }
}

if (-not $ClientSecret -or $ClientSecret -eq "PREENCHER_AQUI") {
    Write-Error "CLIENT_SECRET nao encontrado. Adicione TIKTOK_CLIENT_SECRET ao ~/.adforge/.env"
    exit 1
}

$ffmpeg  = (Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages" -Recurse -Filter "ffmpeg.exe" -ErrorAction SilentlyContinue | Select-Object -First 1).FullName
$desktop = [Environment]::GetFolderPath("Desktop")
$output  = "$desktop\tiktok-demo-final.mp4"
$demoDir = "$env:USERPROFILE\.adforge\tiktok_demo"

if (-not $ffmpeg) {
    Write-Error "ffmpeg nao encontrado. Instale via: winget install Gyan.FFmpeg"
    exit 1
}

Write-Host "`nTikTok Demo -- Iniciando gravacao" -ForegroundColor Cyan
Write-Host "   Saida: $output" -ForegroundColor Gray
Write-Host ""
Write-Host "PASSOS DURANTE A GRAVACAO:" -ForegroundColor Yellow
Write-Host "  1. Abra http://localhost:8080 no Chrome"
Write-Host "  2. Clique em 'Autorizar no TikTok'"
Write-Host "  3. Faca login com a Sandbox Test Account"
Write-Host "  4. Autorize os scopes video.publish + user.info.basic"
Write-Host "  5. Aguarde a pagina de resultado aparecer"
Write-Host "  6. Pressione Ctrl+C neste terminal para parar a gravacao"
Write-Host ""

# Instalar Flask se necessario
pip show flask 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Instalando Flask..." -ForegroundColor Yellow
    pip install flask requests -q
}

# Iniciar ffmpeg em background (120s max)
Write-Host "Iniciando gravacao de tela (120s max)..." -ForegroundColor Cyan
$ffmpegProc = Start-Process -FilePath $ffmpeg `
    -ArgumentList "-f gdigrab -framerate 25 -i desktop -c:v libx264 -preset ultrafast -pix_fmt yuv420p -t 120 -y `"$output`"" `
    -PassThru -WindowStyle Hidden

Start-Sleep -Seconds 2

# Iniciar Flask
Write-Host "Iniciando servidor Flask em http://localhost:8080" -ForegroundColor Green
$env:TIKTOK_CLIENT_SECRET = $ClientSecret
Set-Location $demoDir
python demo_server.py

# Encerrar ffmpeg quando Flask terminar
if (-not $ffmpegProc.HasExited) {
    $ffmpegProc | Stop-Process -Force
}

Write-Host "`nGravacao salva em: $output" -ForegroundColor Green
Write-Host "   Verifique o video antes de submeter ao TikTok." -ForegroundColor Gray
