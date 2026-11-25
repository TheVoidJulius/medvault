$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  MedVault AI — Medical Record Database Launcher" -ForegroundColor Cyan
Write-Host "  Team: Pushkar Panwar (2501730022) & Saksham Singh (2501730270)" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$Root\backend'; .\.venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 8000 --reload"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$Root\frontend'; npm run dev"

Write-Host "`n[+] Backend API & Swagger Docs: http://127.0.0.1:8000/docs" -ForegroundColor Green
Write-Host "[+] Frontend Web Application:   http://localhost:5173" -ForegroundColor Green
