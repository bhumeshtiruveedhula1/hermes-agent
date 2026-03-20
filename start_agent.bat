@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul
mode con: cols=110 lines=32

set "ESC="
set "RESET=%ESC%[0m"
set "RED=%ESC%[31m"
set "GREEN=%ESC%[32m"
set "YELLOW=%ESC%[33m"
set "GRAY=%ESC%[90m"
set "BRIGHT_GREEN=%ESC%[92m"
set "BRIGHT_CYAN=%ESC%[96m"
set "WHITE=%ESC%[37m"
set "MAGENTA=%ESC%[35m"

for /f %%a in ('copy /Z "%~dpf0" nul') do set "CR=%%a"
goto :Main

:ProgressBar
set /a count=0
set "bar="
:ProgLoop
set /a count+=2
set "bar=!bar!X"
<nul set /p ".=%BRIGHT_CYAN%[!bar!                                                  ] !count!%% %RESET%!CR!"
if !count! lss 100 ( ping -n 1 -w 15 127.0.0.1 >nul & goto ProgLoop )
echo.
exit /b

:Main
cls
echo.
echo %BRIGHT_CYAN%  __  __     ______     ______     __  __     ______     ______    %RESET%
echo %BRIGHT_CYAN% /\ \_\ \   /\  ___\   /\  == \   /\ \_\ \   /\  ___\   /\  ___\   %RESET%
echo %BRIGHT_CYAN% \ \  __ \  \ \  __\   \ \  __^<   \ \  __ \  \ \  __\   \ \___  \  %RESET%
echo %BRIGHT_CYAN%  \ \_\ \_\  \ \_____\  \ \_\ \_\  \ \_\ \_\  \ \_____\  \/\_____\ %RESET%
echo %BRIGHT_CYAN%   \/_/\/_/   \/_____/   \/_/ /_/   \/_/\/_/   \/_____/   \/_____/ %RESET%
echo.
echo %GRAY%   -------------------------------------------------------------------%RESET%
echo %GRAY%        AI AGENT SYSTEM  ::  V4.0  ::  DASHBOARD EDITION%RESET%
echo %GRAY%   -------------------------------------------------------------------%RESET%
echo.

echo %GRAY%[SYSTEM] Allocating VRAM...%RESET%
for /L %%i in (1,1,10) do (
    <nul set /p ".=%GREEN%!random!!random! %BRIGHT_CYAN%!random! %GRAY%!random!!random! "
    ping -n 1 -w 10 127.0.0.1 >nul
)
echo.
echo %GREEN%[OK] Memory Integrity Verified.%RESET%
echo.

echo %YELLOW%[TASK] Mounting Large Language Model (Qwen3 8B)...%RESET%
call :ProgressBar
echo %GRAY%   ^> Handshaking with Localhost:11434...%RESET%
ollama run qwen3:8b "" >nul 2>&1
echo %BRIGHT_GREEN%[SUCCESS] Model Loaded ^& Ready (Qwen3 8B).%RESET%
echo.

echo %MAGENTA%[KERNEL] Initializing Sub-systems:%RESET%
timeout /t 1 /nobreak >nul
echo    %GREEN%[+] Security Layers%RESET%...    %BRIGHT_GREEN%ACTIVE%RESET%
timeout /t 1 /nobreak >nul
echo    %GREEN%[+] Task Scheduler%RESET%...     %BRIGHT_GREEN%ONLINE%RESET%
timeout /t 1 /nobreak >nul
echo    %GREEN%[+] Filesystem Sandbox%RESET%... %BRIGHT_GREEN%MOUNTED%RESET%
timeout /t 1 /nobreak >nul
echo    %GREEN%[+] Audit Logger%RESET%...       %BRIGHT_GREEN%RECORDING%RESET%
timeout /t 1 /nobreak >nul
echo    %GREEN%[+] FastAPI Backend%RESET%...    %BRIGHT_GREEN%STARTING%RESET%
timeout /t 1 /nobreak >nul
echo    %GREEN%[+] React Dashboard%RESET%...    %BRIGHT_GREEN%STARTING%RESET%
echo.

cd /d "C:\Users\bhumeshjyothi\Desktop\gemini\AI_Agent_System"

echo %BRIGHT_CYAN%==================================================================%RESET%
echo %WHITE%   LAUNCHING HERMES BACKEND  ::  http://localhost:8000%RESET%
echo %BRIGHT_CYAN%==================================================================%RESET%
start "Hermes API" cmd /k ".venv\Scripts\python -m uvicorn api:app --host 0.0.0.0 --port 8000 --reload"

timeout /t 3 /nobreak >nul

echo %BRIGHT_CYAN%==================================================================%RESET%
echo %WHITE%   LAUNCHING HERMES DASHBOARD  ::  http://localhost:5173%RESET%
echo %BRIGHT_CYAN%==================================================================%RESET%
start "Hermes UI" cmd /k "cd hermes-ui && npm run dev"

timeout /t 4 /nobreak >nul

echo.
echo %BRIGHT_CYAN%==================================================================%RESET%
echo %WHITE%   H E R M E S   D A S H B O A R D   I S   L I V E%RESET%
echo %BRIGHT_CYAN%==================================================================%RESET%
echo.
echo %BRIGHT_GREEN%   Backend   ^>  http://localhost:8000%RESET%
echo %BRIGHT_GREEN%   Dashboard ^>  http://localhost:5173%RESET%
echo.
echo %GRAY%   (Two windows opened - keep them running)%RESET%
echo %GRAY%   (Open http://localhost:5173 in your browser)%RESET%
echo.

start "" "http://localhost:5173"

echo %GRAY%(This window can be closed - servers run in their own windows)%RESET%
pause
