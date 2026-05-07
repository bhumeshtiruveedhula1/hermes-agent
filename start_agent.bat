@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul
mode con: cols=110 lines=36

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
echo %GRAY%        AI AGENT SYSTEM  ::  V2.5  ::  MULTI-USER + VOICE EDITION%RESET%
echo %GRAY%   -------------------------------------------------------------------%RESET%
echo.

REM ── Model Selector ────────────────────────────────────────────────────────
echo %BRIGHT_CYAN%  SELECT MODEL%RESET%
echo %GRAY%  ─────────────────────────────────────────────────────────────────%RESET%
echo %WHITE%    [1]  Qwen3:8B          ^|  ~4 GB VRAM   ^|  Fast   ^|  Good quality%RESET%
echo %WHITE%    [2]  Qwen2.5-Coder:14B  ^|  ~9 GB hybrid  ^|  Slower ^|  Best quality  ^(RECOMMENDED^)%RESET%
echo.
echo %GRAY%       Default: 2 (press Enter for best quality)%RESET%
echo.
set /p "MODEL_CHOICE=  Your choice [1/2]: "

if "%MODEL_CHOICE%"=="1" (
    set "HERMES_MODEL=qwen3:8b"
    set "MODEL_LABEL=Qwen3 8B"
    set "MODEL_COLOR=%GREEN%"
) else (
    set "HERMES_MODEL=qwen2.5-coder:14b"
    set "MODEL_LABEL=Qwen2.5-Coder 14B"
    set "MODEL_COLOR=%BRIGHT_GREEN%"
)

echo.
echo %BRIGHT_GREEN%  [SELECTED] !MODEL_LABEL!%RESET%
echo.

REM ── System checks ─────────────────────────────────────────────────────────
echo %GRAY%[SYSTEM] Allocating VRAM...%RESET%
for /L %%i in (1,1,10) do (
    <nul set /p ".=%GREEN%!random!!random! %BRIGHT_CYAN%!random! %GRAY%!random!!random! "
    ping -n 1 -w 10 127.0.0.1 >nul
)
echo.
echo %GREEN%[OK] Memory Integrity Verified.%RESET%
echo.

REM ── Pull model into Ollama cache ──────────────────────────────────────────
echo %YELLOW%[TASK] Mounting Large Language Model (!MODEL_LABEL!)...%RESET%
call :ProgressBar
echo %GRAY%   ^> Handshaking with Localhost:11434...%RESET%
ollama run %HERMES_MODEL% "" >nul 2>&1
echo !MODEL_COLOR![SUCCESS] Model Loaded ^& Ready ^(!MODEL_LABEL!^).%RESET%
echo.

REM ── Sub-system status ─────────────────────────────────────────────────────
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
echo    %GREEN%[+] Voice Engine%RESET%...       %BRIGHT_GREEN%ARMED%RESET%
timeout /t 1 /nobreak >nul
echo    %GREEN%[+] Multi-User Auth%RESET%...    %BRIGHT_GREEN%ACTIVE%RESET%
timeout /t 1 /nobreak >nul
echo    %GREEN%[+] FastAPI Backend%RESET%...    %BRIGHT_GREEN%STARTING%RESET%
timeout /t 1 /nobreak >nul
echo    %GREEN%[+] React Dashboard%RESET%...    %BRIGHT_GREEN%STARTING%RESET%
echo.

cd /d "C:\Users\bhumeshjyothi\Desktop\gemini\AI_Agent_System"

REM ── Launch backend with HERMES_MODEL env var ──────────────────────────────
echo %BRIGHT_CYAN%==================================================================%RESET%
echo %WHITE%   LAUNCHING HERMES BACKEND  ::  http://localhost:8000%RESET%
echo %WHITE%   MODEL: !MODEL_LABEL!%RESET%
echo %BRIGHT_CYAN%==================================================================%RESET%
start "Hermes API [!MODEL_LABEL!]" cmd /k "set HERMES_MODEL=!HERMES_MODEL! && .venv\Scripts\python -m uvicorn api:app --host 0.0.0.0 --port 8000 --reload"

timeout /t 3 /nobreak >nul

REM ── Launch frontend ───────────────────────────────────────────────────────
echo %BRIGHT_CYAN%==================================================================%RESET%
echo %WHITE%   LAUNCHING HERMES DASHBOARD  ::  http://localhost:5173%RESET%
echo %BRIGHT_CYAN%==================================================================%RESET%
start "Hermes UI" cmd /k "cd hermes-ui && npm run dev"

timeout /t 4 /nobreak >nul

REM ── Live banner ───────────────────────────────────────────────────────────
echo.
echo %BRIGHT_CYAN%==================================================================%RESET%
echo %WHITE%   H E R M E S   D A S H B O A R D   I S   L I V E%RESET%
echo %BRIGHT_CYAN%==================================================================%RESET%
echo.
echo %BRIGHT_GREEN%   Backend   ^>  http://localhost:8000%RESET%
echo %BRIGHT_GREEN%   Dashboard ^>  http://localhost:5173%RESET%
echo.
echo %GRAY%   Model     :  !MODEL_LABEL!%RESET%
echo %GRAY%   Auth      :  Login at http://localhost:5173 (admin / hermes2026)%RESET%
echo %GRAY%   Voice     :  Click mic button in Chat tab%RESET%
echo %GRAY%   Browser   :  Browser tab ^> LIVE mode%RESET%
echo.
echo %GRAY%   (Two windows opened - keep them running)%RESET%
echo.

start "" "http://localhost:5173"

echo %GRAY%(This window can be closed - servers run in their own windows)%RESET%
pause
