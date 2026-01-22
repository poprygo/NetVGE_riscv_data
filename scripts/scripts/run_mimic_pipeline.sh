#!/bin/bash

###############################################################################
#
# MIMIC Pipeline Execution Script
# 
# Complete workflow for automatic Hardware Trojan insertion
# Based on Cruz et al. "Automatic Hardware Trojan Insertion using Machine Learning"
#
###############################################################################

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default parameters
NETLIST=""
OUTPUT_DIR="trojans/mimic_output"
NUM_TROJANS=10
SEED=42
USE_SYNTHETIC=true
MODEL_FILE=""
HIERARCHICAL=false
SAMPLE_RATE=""

# Function to print colored messages
print_info() {
    echo -e "${BLUE}ℹ ${NC}$1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_header() {
    echo ""
    echo "═══════════════════════════════════════════════════════════════════════════"
    echo "$1"
    echo "═══════════════════════════════════════════════════════════════════════════"
    echo ""
}

# Usage information
usage() {
    cat << EOF
Usage: $0 --netlist <netlist.v> [OPTIONS]

REQUIRED:
  --netlist FILE          Input gate-level Verilog netlist

OPTIONS:
  --output DIR            Output directory (default: trojans/mimic_output)
  --num-trojans N         Number of Trojans to insert (default: 10)
  --model FILE            Pre-trained model file (.pkl)
  --seed N                Random seed for reproducibility (default: 42)
  --hierarchical          Use hierarchical processing for large designs
  --sample-rate FLOAT     Sample rate for large designs (e.g., 0.1 for 10%)
  --help                  Show this help message

EXAMPLES:
  # Basic usage with PicoRV32
  $0 --netlist riscv_designs/picorv32/picorv32.v --num-trojans 20

  # Large design with sampling
  $0 --netlist riscv_designs/cva6/core/cva6.sv \\
     --num-trojans 50 \\
     --hierarchical \\
     --sample-rate 0.05

  # Use pre-trained model
  $0 --netlist synthesis/netlists/design.v \\
     --model trojans/models/insertion_model.pkl \\
     --num-trojans 100

EOF
    exit 1
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --netlist)
            NETLIST="$2"
            shift 2
            ;;
        --output)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --num-trojans)
            NUM_TROJANS="$2"
            shift 2
            ;;
        --model)
            MODEL_FILE="$2"
            shift 2
            ;;
        --seed)
            SEED="$2"
            shift 2
            ;;
        --hierarchical)
            HIERARCHICAL=true
            shift
            ;;
        --sample-rate)
            SAMPLE_RATE="$2"
            shift 2
            ;;
        --help)
            usage
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

# Validate required parameters
if [ -z "$NETLIST" ]; then
    print_error "Error: --netlist is required"
    usage
fi

if [ ! -f "$NETLIST" ]; then
    print_error "Error: Netlist file not found: $NETLIST"
    exit 1
fi

# Print configuration
print_header "MIMIC: Automatic Hardware Trojan Insertion Pipeline"

print_info "Configuration:"
echo "  Input netlist:      $NETLIST"
echo "  Output directory:   $OUTPUT_DIR"
echo "  Number of Trojans:  $NUM_TROJANS"
echo "  Random seed:        $SEED"
echo "  Model file:         ${MODEL_FILE:-<train new>}"
echo "  Hierarchical:       $HIERARCHICAL"
echo "  Sample rate:        ${SAMPLE_RATE:-<full>}"
echo ""

# Check environment
print_info "Checking environment..."

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    print_warning "Virtual environment not activated"
    print_info "Activating virtual environment..."
    
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
    
    if [ -f "$PROJECT_ROOT/venv/bin/activate" ]; then
        source "$PROJECT_ROOT/venv/bin/activate"
        print_success "Virtual environment activated"
    else
        print_error "Virtual environment not found at $PROJECT_ROOT/venv"
        print_info "Run: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
        exit 1
    fi
fi

# Check Python version
PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
print_success "Python version: $PYTHON_VERSION"

# Check required packages
print_info "Checking required packages..."
REQUIRED_PACKAGES="numpy pandas scikit-learn pyverilog"
for pkg in $REQUIRED_PACKAGES; do
    if python -c "import ${pkg//-/_}" 2>/dev/null; then
        print_success "  $pkg"
    else
        print_warning "  $pkg (missing)"
        print_info "Installing $pkg..."
        pip install $pkg -q
    fi
done

echo ""

# Build command
CMD="python scripts/mimic_pipeline.py"
CMD="$CMD --netlist $NETLIST"
CMD="$CMD --output $OUTPUT_DIR"
CMD="$CMD --num-trojans $NUM_TROJANS"
CMD="$CMD --seed $SEED"

if [ -n "$MODEL_FILE" ]; then
    CMD="$CMD --model $MODEL_FILE"
fi

if [ "$USE_SYNTHETIC" = true ]; then
    CMD="$CMD --synthetic"
fi

# Add hierarchical and sampling options if specified
if [ "$HIERARCHICAL" = true ]; then
    print_info "Using hierarchical processing for large design"
fi

if [ -n "$SAMPLE_RATE" ]; then
    print_info "Using sample rate: $SAMPLE_RATE"
fi

# Run pipeline
print_header "STEP 1/4: Feature Extraction"
print_info "Extracting features from netlist..."
print_info "This may take several minutes for large designs..."

START_TIME=$(date +%s)

# Execute pipeline
print_info "Executing: $CMD"
echo ""

if $CMD; then
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    MINUTES=$((DURATION / 60))
    SECONDS=$((DURATION % 60))
    
    print_header "✅ PIPELINE COMPLETE"
    
    print_success "Execution time: ${MINUTES}m ${SECONDS}s"
    echo ""
    
    print_info "Output files:"
    echo "  📁 $OUTPUT_DIR/"
    echo "     ├── netlist_features.json        (Extracted features)"
    echo "     ├── insertion_model.pkl          (Trained ML model)"
    echo "     ├── target_nets.json             (Scored nets)"
    echo "     ├── pipeline_summary.json        (Pipeline metadata)"
    echo "     └── trojaned_netlists/           (Trojan-inserted designs)"
    echo "         ├── design_trojan_001_*.v"
    echo "         ├── design_trojan_002_*.v"
    echo "         ├── ..."
    echo "         └── insertion_metadata.json  (Trojan metadata)"
    echo ""
    
    # Count actual Trojans
    TROJAN_COUNT=$(ls -1 $OUTPUT_DIR/trojaned_netlists/*.v 2>/dev/null | wc -l | xargs)
    print_success "Generated $TROJAN_COUNT Trojan-inserted designs"
    
    echo ""
    print_info "Next steps:"
    echo "  1. Validate insertions:"
    echo "     python scripts/validate_insertion.py \\"
    echo "       --original $NETLIST \\"
    echo "       --trojaned $OUTPUT_DIR/trojaned_netlists/ \\"
    echo "       --metadata $OUTPUT_DIR/trojaned_netlists/insertion_metadata.json"
    echo ""
    echo "  2. Generate ML detector dataset:"
    echo "     python scripts/generate_dataset.py \\"
    echo "       --clean-dir <clean_designs/> \\"
    echo "       --trojaned-dir $OUTPUT_DIR/trojaned_netlists/ \\"
    echo "       --output ml_detector_testing/datasets/dataset.csv"
    echo ""
    echo "  3. Test your ML detector on the new dataset"
    echo ""
    
    print_header "🎉 SUCCESS!"
    
    exit 0
else
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    
    print_header "❌ PIPELINE FAILED"
    
    print_error "Execution failed after ${DURATION}s"
    print_info "Check logs above for error details"
    echo ""
    
    print_info "Common issues:"
    echo "  • Netlist too large → Use --hierarchical and --sample-rate"
    echo "  • Invalid Verilog → Check netlist syntax"
    echo "  • Missing dependencies → Run: pip install -r requirements.txt"
    echo ""
    
    exit 1
fi
