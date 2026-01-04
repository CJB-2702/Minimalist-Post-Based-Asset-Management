#!/bin/bash
set -e

echo "=== EBAMS Container Starting ==="
echo "Running cleanup script..."

# Run the cleanup script
python z_clear_data.py

echo "Cleanup complete. Starting application..."
echo ""

# Start the Flask application
exec python app.py

