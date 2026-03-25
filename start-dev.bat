@echo off
taskkill /F /IM node.exe 2>nul
timeout /t 2 /nobreak >nul
start "π-Optimized Dev Server" cmd /k "cd /d C:\Users\Dipak.Mandlik\Desktop\π-optimized && npm run dev"
timeout /t 8 /nobreak >nul
curl -s -o nul -w "Server status: %%{http_code}\n" http://localhost:3000
pause
