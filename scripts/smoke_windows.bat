@echo off
setlocal

echo ================================================================================
echo  Running QHome AI Agent Smoke Tests (Windows CMD)
echo ================================================================================

set "ROOT=%~dp0.."

echo Checking Python availability...
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Python is required but not installed.
    exit /b 1
)

echo.
echo Running Full Quality Check...
python "%ROOT%\scripts\run_full_quality_check.py"
if %ERRORLEVEL% neq 0 (
    echo.
    echo [X] Quality Check Failed!
    exit /b 1
)

echo.
echo Running a mock workflow to verify end-to-end routing...
python "%ROOT%\run.py" run --ticket-id="damaged-ceramic-delivery"

echo.
echo ================================================================================
echo  Smoke test completed successfully!
echo ================================================================================
