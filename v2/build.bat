@echo off
setlocal enabledelayedexpansion

echo ============================================================
echo  State Farm EFT Formatter - Build Script
echo ============================================================
echo.

REM ── 1. Install dependencies ─────────────────────────────────
echo [1/2] Installing dependencies...
python -m pip install customtkinter pdfplumber reportlab pypdf
if !errorlevel! neq 0 (
    echo.
    echo ERROR: pip install failed. See output above.
    goto :error
)

echo.

REM ── 2. Build with PyInstaller ───────────────────────────────
echo [2/2] Building executable...
python -m PyInstaller -y --onedir --noconsole ^
    --collect-all pdfplumber ^
    --collect-all customtkinter ^
    --name StateFarmFormatter ^
    main.py
if !errorlevel! neq 0 (
    echo.
    echo ERROR: PyInstaller build failed. See output above.
    goto :error
)

echo.
echo ============================================================
echo  BUILD COMPLETE
echo  Output: dist\StateFarmFormatter\StateFarmFormatter.exe
echo ============================================================
goto :end

:error
echo.
echo ============================================================
echo  BUILD FAILED  -  check the output above for details
echo ============================================================

:end
echo.
pause
