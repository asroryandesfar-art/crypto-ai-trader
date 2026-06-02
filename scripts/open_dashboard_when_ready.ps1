param(
    [string]$Root
)

$ErrorActionPreference = "SilentlyContinue"
if ([string]::IsNullOrWhiteSpace($Root)) {
    $Root = Split-Path -Parent $PSScriptRoot
}

$dashboardUrl = "http://127.0.0.1:8501"
$launcherHtml = Join-Path $Root "START_CRYPTO_AI.html"

if (Test-Path $launcherHtml) {
    Start-Process $launcherHtml
}

$ready = $false
$healthUrls = @(
    "$dashboardUrl/_stcore/health",
    "$dashboardUrl/healthz",
    "$dashboardUrl/"
)

for ($i = 0; $i -lt 45; $i++) {
    foreach ($url in $healthUrls) {
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 2
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
                $ready = $true
                break
            }
        } catch {
        }
    }
    if ($ready) {
        break
    }
    Start-Sleep -Seconds 1
}

Start-Process $dashboardUrl
