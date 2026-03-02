@echo off
REM Install WSU Review Server as a Windows Service using NSSM
REM Prerequisites: NSSM must be on PATH (download from https://nssm.cc/)

set SERVICE_NAME=WSUReviewServer
set SCRIPT_DIR=%~dp0

echo Installing %SERVICE_NAME%...

nssm install %SERVICE_NAME% "C:\Strawberry\perl\bin\perl.exe" "%SCRIPT_DIR%review-server.pl"
nssm set %SERVICE_NAME% AppDirectory "%SCRIPT_DIR%"
nssm set %SERVICE_NAME% AppStdout "%SCRIPT_DIR%logs\service-stdout.log"
nssm set %SERVICE_NAME% AppStderr "%SCRIPT_DIR%logs\service-stderr.log"
nssm set %SERVICE_NAME% AppStdoutCreationDisposition 4
nssm set %SERVICE_NAME% AppStderrCreationDisposition 4
nssm set %SERVICE_NAME% AppRotateFiles 1
nssm set %SERVICE_NAME% AppRotateSeconds 86400
nssm set %SERVICE_NAME% AppRotateBytes 10485760
nssm set %SERVICE_NAME% AppRestartDelay 5000
nssm set %SERVICE_NAME% Description "WSU Facilities Services - Construction Document Review Server"

if not exist "%SCRIPT_DIR%logs" mkdir "%SCRIPT_DIR%logs"

echo.
echo Service installed. Start with: nssm start %SERVICE_NAME%
echo Configure with: nssm edit %SERVICE_NAME%
