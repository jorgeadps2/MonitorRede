@echo off
setlocal
cd /d "%~dp0"

if not exist "dist\MonitorRede.exe" (
    echo Nao encontrei dist\MonitorRede.exe
    echo Execute GERAR_EXE.bat primeiro.
    pause
    exit /b 1
)

set "EXE=%CD%\dist\MonitorRede.exe"
set "ICON=%CD%\assets\monitor_rede.ico"
set "SHORTCUT=%USERPROFILE%\Desktop\Monitor de Rede.lnk"

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
 "$ws=New-Object -ComObject WScript.Shell; $s=$ws.CreateShortcut('%SHORTCUT%'); $s.TargetPath='%EXE%'; $s.WorkingDirectory='%CD%'; $s.IconLocation='%ICON%,0'; $s.Description='Monitor profissional de Wi-Fi, Ethernet e Internet'; $s.Save()"

echo.
echo Atalho criado na Area de Trabalho.
echo.
pause
endlocal
