@echo off
setlocal EnableExtensions
chcp 65001 >nul
title Instalar Monitor de Rede

cd /d "%~dp0"

set "APPNAME=MonitorRede"
set "DISPLAYNAME=Monitor de Rede"
set "INSTALLDIR=%LOCALAPPDATA%\MonitorRede"
set "EXE=%INSTALLDIR%\MonitorRede.exe"
set "ICON=%INSTALLDIR%\assets\monitor_rede.ico"

 echo ============================================================
 echo             MONITOR DE REDE - INSTALADOR
 echo ============================================================
 echo.

if not exist "dist\MonitorRede.exe" (
    echo ERRO: nao encontrei dist\MonitorRede.exe
    echo Execute primeiro GERAR_EXE.bat.
    echo.
    pause
    exit /b 1
)

if not exist "%INSTALLDIR%" mkdir "%INSTALLDIR%"
if not exist "%INSTALLDIR%\assets" mkdir "%INSTALLDIR%\assets"

copy /Y "dist\MonitorRede.exe" "%EXE%" >nul
if errorlevel 1 (
    echo ERRO ao copiar o executavel.
    pause
    exit /b 1
)

if exist "assets\monitor_rede.ico" copy /Y "assets\monitor_rede.ico" "%ICON%" >nul

REM Usa o caminho real da Area de Trabalho do Windows.
REM Isso funciona mesmo quando a Area de Trabalho esta no OneDrive.
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
 "$desktop=[Environment]::GetFolderPath('Desktop'); if(-not(Test-Path $desktop)){New-Item -ItemType Directory -Path $desktop -Force|Out-Null}; $shortcut=Join-Path $desktop 'Monitor de Rede.lnk'; $ws=New-Object -ComObject WScript.Shell; $s=$ws.CreateShortcut($shortcut); $s.TargetPath='%EXE%'; $s.WorkingDirectory='%INSTALLDIR%'; if(Test-Path '%ICON%'){$s.IconLocation='%ICON%,0'}else{$s.IconLocation='%EXE%,0'}; $s.Description='Monitor profissional de Wi-Fi, Ethernet e Internet'; $s.Save(); if(Test-Path $shortcut){Write-Host 'ATALHO_DESKTOP_OK'}else{Write-Host 'ATALHO_DESKTOP_ERRO'}"

REM Cria tambem o atalho no Menu Iniciar.
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
 "$start=[Environment]::GetFolderPath('Programs'); if(-not(Test-Path $start)){New-Item -ItemType Directory -Path $start -Force|Out-Null}; $shortcut=Join-Path $start 'Monitor de Rede.lnk'; $ws=New-Object -ComObject WScript.Shell; $s=$ws.CreateShortcut($shortcut); $s.TargetPath='%EXE%'; $s.WorkingDirectory='%INSTALLDIR%'; if(Test-Path '%ICON%'){$s.IconLocation='%ICON%,0'}else{$s.IconLocation='%EXE%,0'}; $s.Description='Monitor profissional de Wi-Fi, Ethernet e Internet'; $s.Save(); if(Test-Path $shortcut){Write-Host 'ATALHO_START_OK'}else{Write-Host 'ATALHO_START_ERRO'}"

echo.
echo ============================================================
echo                 INSTALACAO CONCLUIDA!
echo ============================================================
echo.
echo Programa: %EXE%
echo.
echo O atalho foi criado na Area de Trabalho e no Menu Iniciar.
echo Se o icone nao aparecer imediatamente, pressione F5 na Area de Trabalho.
echo.
start "" "%EXE%"

timeout /t 2 >nul
endlocal
