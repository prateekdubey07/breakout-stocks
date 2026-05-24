# BreakoutStocks — start backend + frontend in separate windows
$root = Split-Path -Parent $MyInvocation.MyCommand.Path

# Backend
Start-Process powershell -ArgumentList "-NoExit", "-Command", "
    Set-Location '$root\backend'
    Write-Host '=== BreakoutStocks Backend ===' -ForegroundColor Cyan
    pip install -r requirements.txt --quiet
    uvicorn main:app --reload --port 8000
" -WindowStyle Normal

Start-Sleep -Seconds 3

# Frontend
Start-Process powershell -ArgumentList "-NoExit", "-Command", "
    Set-Location '$root\frontend'
    Write-Host '=== BreakoutStocks Frontend ===' -ForegroundColor Green
    npm install --silent
    npm run dev
" -WindowStyle Normal

Write-Host ""
Write-Host "Starting BreakoutStocks..." -ForegroundColor Yellow
Write-Host "  Backend  -> http://localhost:8000" -ForegroundColor Cyan
Write-Host "  Frontend -> http://localhost:3000" -ForegroundColor Green
Write-Host ""
Write-Host "Close the two terminal windows to stop." -ForegroundColor Gray

Start-Sleep -Seconds 5
Start-Process "http://localhost:3000"
