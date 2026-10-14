$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$backendPython = Join-Path $projectRoot 'console-backend\.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $backendPython)) {
    throw 'Create console-backend\.venv using Python 3.11 and install console-backend\requirements-dev.txt first. See LOCAL_DEVELOPMENT.md.'
}
if (-not (Test-Path -LiteralPath (Join-Path $projectRoot 'ai-interview-coach\node_modules\vite'))) {
    throw 'Run npm ci in ai-interview-coach first.'
}
foreach ($port in @(8000, 5173)) {
    if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) {
        throw "Port $port is already in use. Stop the previous local server before launching this script."
    }
}
$apiProcess = Start-Process -FilePath $backendPython -ArgumentList 'local_server.py' -WorkingDirectory (Join-Path $projectRoot 'console-backend') -WindowStyle Hidden -PassThru
try {
    $ready = $false
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        if ($apiProcess.HasExited) { throw 'Backend exited during startup. Run console-backend\.venv\Scripts\python.exe console-backend\local_server.py to view the error.' }
        try {
            $null = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/health' -TimeoutSec 1
            $ready = $true
            break
        } catch { Start-Sleep -Milliseconds 500 }
    }
    if (-not $ready) { throw 'Backend did not become ready.' }
    Write-Host 'API: http://127.0.0.1:8000/docs'
    Write-Host 'App: http://127.0.0.1:5173 — create an account to begin.'
    Write-Host 'Press Ctrl+C to stop both servers.'
    Push-Location (Join-Path $projectRoot 'ai-interview-coach')
    try { & npm.cmd run dev } finally { Pop-Location }
} finally {
    if (-not $apiProcess.HasExited) { Stop-Process -Id $apiProcess.Id }
}
