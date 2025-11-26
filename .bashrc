# Asset Management App Environment Setup
# Source this file to activate the virtual environment and set Flask variables

# Function to activate virtual environment if it exists
activate_venv() {
    if [ -d "venv" ]; then
        source venv/bin/activate
        echo "Virtual environment activated for Asset Management System"
    fi
}

# Activate virtual environment
activate_venv

# Set Flask environment variables
export FLASK_APP=run.py
export FLASK_ENV=development
export PYTHONPATH="${PYTHONPATH}:$(pwd)"


if [ -d "venv" ]; then source venv/bin/activate; fi
