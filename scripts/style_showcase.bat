@echo off
chcp 65001 >nul
cd /d "%~dp0.."
setlocal enabledelayedexpansion

:: ============================================
::  Widget style showcase - one-click launcher
::  Lives in scripts\; run from anywhere (double-click is fine).
::  Equivalent to: python scripts\style_showcase.py
::  Extra args are forwarded, e.g. style_showcase.bat --selftest
:: ============================================

:: Prefer the bundled Python in the repo root; fall back to py / python
:: (the script itself re-execs into the bundled interpreter when present).
set "PYCMD="
if exist "%~dp0..\ballontrans_pylibs_win\python.exe" set PYCMD="%~dp0..\ballontrans_pylibs_win\python.exe"

if not defined PYCMD (
    where py >nul 2>nul
    if !ERRORLEVEL! == 0 set "PYCMD=py -3"
)
if not defined PYCMD (
    where python >nul 2>nul
    if !ERRORLEVEL! == 0 set "PYCMD=python"
)

if not defined PYCMD (
    echo [ERROR] Python not found. Expected ballontrans_pylibs_win\python.exe
    pause
    exit /b 1
)

%PYCMD% "%~dp0style_showcase.py" %*
set "EXIT_CODE=!ERRORLEVEL!"
if not "!EXIT_CODE!" == "0" (
    echo.
    echo [ERROR] Showcase exited with code !EXIT_CODE! - see the log above.
    pause
)
exit /b !EXIT_CODE!
