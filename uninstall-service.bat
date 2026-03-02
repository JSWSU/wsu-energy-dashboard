@echo off
set SERVICE_NAME=WSUReviewServer
echo Stopping %SERVICE_NAME%...
nssm stop %SERVICE_NAME%
echo Removing %SERVICE_NAME%...
nssm remove %SERVICE_NAME% confirm
echo Service removed.
