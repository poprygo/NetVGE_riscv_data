#!/bin/bash
# MIMIC Environment Setup Script

set -e

echo "======================================"
echo "MIMIC Environment Setup"
echo "======================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Project root
MIMIC_ROOT="/Users/yaroslavpopryho/Study/UIC/Research/MIMIC"
cd "$MIMIC_ROOT"

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to print status
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $2"
    else
        echo -e "${RED}✗${NC} $2"
    fi
}

# Check Python
echo "Checking Python installation..."
if command_exists python3; then
    PYTHON_VERSION=$(python3 --version)
    print_status 0 "Python found: $PYTHON_VERSION"
else
    print_status 1 "Python 3 not found. Please install Python 3.7+"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo ""
    echo "Creating Python virtual environment..."
    python3 -m venv venv
    print_status $? "Virtual environment created"
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source venv/bin/activate
print_status $? "Virtual environment activated"

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip > /dev/null 2>&1
print_status $? "pip upgraded"

# Install Python dependencies
echo ""
echo "Installing Python dependencies..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt > /dev/null 2>&1
    print_status $? "Python dependencies installed"
else
    print_status 1 "requirements.txt not found"
fi

# Check for synthesis tools
echo ""
echo "Checking for synthesis tools..."

if command_exists yosys; then
    YOSYS_VERSION=$(yosys -V 2>/dev/null | head -1 || echo "unknown")
    print_status 0 "Yosys found: $YOSYS_VERSION"
else
    print_status 1 "Yosys not found. Install with: brew install yosys (macOS) or apt-get install yosys (Linux)"
fi

# Check for simulation tools
echo ""
echo "Checking for simulation tools..."

if command_exists iverilog; then
    IVERILOG_VERSION=$(iverilog -v 2>&1 | head -1)
    print_status 0 "Icarus Verilog found"
else
    print_status 1 "Icarus Verilog not found. Install with: brew install icarus-verilog (macOS) or apt-get install iverilog (Linux)"
fi

if command_exists verilator; then
    VERILATOR_VERSION=$(verilator --version | head -1)
    print_status 0 "Verilator found: $VERILATOR_VERSION"
else
    echo -e "${YELLOW}⚠${NC} Verilator not found (optional but recommended)"
fi

# Create directory structure
echo ""
echo "Setting up directory structure..."
mkdir -p docs
mkdir -p riscv_designs
mkdir -p synthesis/{scripts,libs,netlists}
mkdir -p trojans/{seed_trojans,mimic_config,inserted,metadata}
mkdir -p validation/{testbenches,simulation,equivalence}
mkdir -p ml_detector_testing/{datasets,features,models,results}
mkdir -p scripts
print_status 0 "Directory structure created"

# Make scripts executable
echo ""
echo "Making scripts executable..."
chmod +x scripts/*.sh 2>/dev/null || true
chmod +x scripts/*.py 2>/dev/null || true
print_status 0 "Scripts made executable"

# Create environment file
echo ""
echo "Creating environment configuration..."
cat > .env << EOF
# MIMIC Environment Configuration
export MIMIC_ROOT="$MIMIC_ROOT"
export PATH="\$MIMIC_ROOT/mimic_tool/bin:\$PATH"
export PYTHONPATH="\$MIMIC_ROOT:\$PYTHONPATH"

# Tool paths
export YOSYS_PATH=$(which yosys 2>/dev/null || echo "not-found")
export IVERILOG_PATH=$(which iverilog 2>/dev/null || echo "not-found")
export VERILATOR_PATH=$(which verilator 2>/dev/null || echo "not-found")

# Standard cell library
export STD_CELL_LIB="\$MIMIC_ROOT/synthesis/libs/freepdk-45nm/stdcells.lib"

# Output directories
export NETLIST_DIR="\$MIMIC_ROOT/synthesis/netlists"
export TROJAN_DIR="\$MIMIC_ROOT/trojans/inserted"
EOF
print_status 0 "Environment file created (.env)"
