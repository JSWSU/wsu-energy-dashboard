@echo off
REM Refresh the Processes page register (data\processes.json) from the SOP library and publish it.
REM Reads sops\INDEX.md, README.txt and last-run.log in each process folder. Publishes only
REM names, cadence, owner, dates and result words. Safe to run any time.
cd /d "%~dp0"
py export_processes_json.py --push
echo.
echo Page: https://jswsu.github.io/wsu-energy-dashboard/processes.html  (hard refresh: Ctrl+Shift+R, allow about 60 seconds)
pause
