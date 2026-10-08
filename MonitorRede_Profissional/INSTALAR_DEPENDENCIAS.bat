@echo off
setlocal
title Monitor de Rede - Preparar ambiente
cd /d "%~dp0"

where py >nul 2>&1
if %errorlevel%==0 (set "PY=py") else (set "PY=python")

echo Instalando PyInstaller e Pillow...
%PY% -m pip install --upgrade pyinstaller pillow

if errorlevel 1 (
    echo.
    echo Falha na instalacao.
    pause
    exit /b 1
)

echo.
echo Ambiente preparado.
pause
endlocal
