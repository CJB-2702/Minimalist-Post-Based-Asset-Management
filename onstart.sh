#!/bin/bash
set -euo pipefail

# Base paths
APP_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$APP_DIR"

PIDFILE="$APP_DIR/asset-management.pid"
LOGDIR="$APP_DIR/logs"
mkdir -p "$LOGDIR"
LOGFILE="$LOGDIR/server_$(date +%Y%m%d).log"

echo "Starting asset-management from $APP_DIR"

# If a PID file exists, stop the previous process cleanly
if [ -f "$PIDFILE" ]; then
	OLDPID=$(cat "$PIDFILE" 2>/dev/null || true)
	if [ -n "$OLDPID" ] && ps -p "$OLDPID" > /dev/null 2>&1; then
		echo "Stopping existing process $OLDPID"
		kill "$OLDPID" || true
		sleep 5
		if ps -p "$OLDPID" > /dev/null 2>&1; then
			echo "Force killing $OLDPID"
			kill -9 "$OLDPID" || true
		fi
	fi
	rm -f "$PIDFILE" || true
fi

# Run data cleanup (tolerate failures)
echo "Running data cleanup"
python3.14 z_clear_data.py || true

echo "Waiting 10 seconds..."
sleep 10

# Activate virtual environment
if [ -f "venv/bin/activate" ]; then
	# shellcheck disable=SC1091
	source venv/bin/activate
else
	echo "Warning: virtualenv not found at venv/bin/activate"
fi

# Start the application as a background process and record PID
echo "Starting application, logging to $LOGFILE"
nohup python3.14 app.py >> "$LOGFILE" 2>&1 &
NEWPID=$!
echo "$NEWPID" > "$PIDFILE"
echo "Application started with PID $NEWPID"

# Short pause then show the last lines of the log for quick feedback
sleep 2
tail -n 50 "$LOGFILE"

exit 0