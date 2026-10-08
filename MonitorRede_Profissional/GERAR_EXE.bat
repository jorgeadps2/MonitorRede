@echo off
setlocal
title Monitor de Rede - Gerar EXE
cd /d "%~dp0"

echo ============================================================
echo        MONITOR DE REDE - GERADOR DO EXECUTAVEL
echo ============================================================
echo.

where py >nul 2>&1
if %errorlevel%==0 (
    set "PY=py"
) else (
    set "PY=python"
)

echo [1/5] Verificando Python...
%PY% --version
if errorlevel 1 (
    echo.
    echo ERRO: Python nao foi encontrado.
    pause
    exit /b 1
)

echo.
echo [2/5] Instalando/atualizando dependencias...
%PY% -m pip install --upgrade pyinstaller pillow
if errorlevel 1 (
    echo.
    echo ERRO ao instalar dependencias.
    pause
    exit /b 1
)

echo.
echo [3/5] Testando o codigo...
%PY% -m py_compile monitor_rede_final.py
if errorlevel 1 (
    echo.
    echo ERRO: o codigo possui erro de sintaxe.
    pause
    exit /b 1
)

echo.
echo [4/5] Limpando builds anteriores...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo.
echo [5/5] Gerando EXE...
%PY% -m PyInstaller --noconfirm --clean --onefile --windowed --name "MonitorRede" --icon "assets\monitor_rede.ico" --add-data "assets;assets" monitor_rede_final.py

if errorlevel 1 (
    echo.
    echo ERRO: o PyInstaller nao conseguiu gerar o EXE.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  CONCLUIDO!
echo ============================================================
echo.
echo EXE:
echo %CD%\dist\MonitorRede.exe
echo.
echo O executavel ja inclui o icone e a tela de abertura.
echo.
pause
endlocal
