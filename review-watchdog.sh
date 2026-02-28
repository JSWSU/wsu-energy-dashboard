#!/bin/bash
# review-watchdog.sh — Restart review server if it's not running.
# Schedule via Windows Task Scheduler every 2 minutes.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PIDFILE="$SCRIPT_DIR/review-server.pid"
LOGFILE="$SCRIPT_DIR/watchdog.log"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOGFILE"; }

# Check PID file exists
if [ ! -f "$PIDFILE" ]; then
    log "No PID file found. Starting server."
    cd "$SCRIPT_DIR"
    nohup perl review-server.pl >> server.log 2>&1 &
    log "Server started with PID $!"
    exit 0
fi

PID=$(cat "$PIDFILE")

# Check if process is alive (Windows: tasklist; Unix: kill -0)
if tasklist //FI "PID eq $PID" 2>/dev/null | grep -q "$PID"; then
    # Server is running
    exit 0
fi

# Server is dead — restart
log "Server PID $PID is not running. Restarting."
rm -f "$PIDFILE"
cd "$SCRIPT_DIR"
nohup perl review-server.pl >> server.log 2>&1 &
log "Server restarted with PID $!"
