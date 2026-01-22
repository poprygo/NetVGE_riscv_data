# MIMIC Pipeline - Complete Guide

This directory contains scripts to reproduce the **MIMIC (Machine learning for Insertion of Malicious Implants in Circuits)** methodology for automatic Hardware Trojan insertion.

## 📋 Overview

The MIMIC pipeline implements the methodology from:
> Cruz et al., "Automatic Hardware Trojan Insertion using Machine Learning"

**Pipeline Steps:**
1. **Feature Extraction** → Extract structural & testability features from netlists
2. **Model Training** → Train ML model to identify vulnerable nets
3. **Net Scoring** → Score nets by suitability for Trojan insertion
4. **Trojan Insertion** → Automatically insert Trojans into netlists

  
## 🚀 Quick Start

## 📥 Download RISC-V Core Designs


### Download Fresh Copies

**PicoRV32**:
```bash
cd riscv_designs/
git clone https://github.com/YosysHQ/picorv32.git
cd picorv32
# Main file: picorv32.v
```
- **GitHub:** https://github.com/YosysHQ/picorv32

**Ibex**:
```bash
cd riscv_designs/
git clone https://github.com/lowRISC/ibex.git
cd ibex
# Main files in: rtl/
```
- **GitHub:** https://github.com/lowRISC/ibex


**CVA6 (formerly Ariane)**:
```bash
cd riscv_designs/
git clone https://github.com/openhwgroup/cva6.git
cd cva6
# Main file: core/cva6.sv
```
- **GitHub:** https://github.com/openhwgroup/cva6
- 
### Option 1: Complete Pipeline (Recommended)

Run the entire MIMIC pipeline in one command:

```bash
cd /Users/yaroslavpopryho/Study/UIC/Research/MIMIC

# Activate virtual environment
source venv/bin/activate

# Run complete pipeline
python scripts/mimic_pipeline.py \
  --netlist synthesis/netlists/picorv32_gl.v \
  --output trojans/mimic_output/ \
  --num-trojans 10 \
  --synthetic
```

This will:
- Extract features from the netlist
- Train an ML model (using synthetic data)
- Score all nets
- Insert 10 Trojans with different types

### Option 2: Step-by-Step Execution

Run each step individually for more control:

```bash
# Step 1: Feature Extraction
python scripts/feature_extraction.py \
  --netlist synthesis/netlists/picorv32_gl.v \
  --output trojans/features.json

# Step 2: Train Model
python scripts/train_insertion_model.py \
  --output trojans/insertion_model.pkl \
  --synthetic

# Step 3: Score Nets
python scripts/train_insertion_model.py \
  --model trojans/insertion_model.pkl \
  --features trojans/features.json \
  --predict \
  --top-k 100 \
  --output trojans/target_nets.json

# Step 4: Insert Trojans
python scripts/trojan_inserter.py \
  --netlist synthesis/netlists/picorv32_gl.v \
  --target-nets trojans/target_nets.json \
  --num-trojans 10 \
  --output trojans/inserted/
```

---

## 📂 Scripts Description

### Core Pipeline Scripts

| Script | Purpose | Key Features |
|--------|---------|--------------|
| **`mimic_pipeline.py`** | End-to-end pipeline | Orchestrates all steps |
| **`feature_extraction.py`** | Extract netlist features | SCOAP + structural features |
| **`train_insertion_model.py`** | Train ML model | Random Forest / Gradient Boosting |
| **`trojan_inserter.py`** | Insert Trojans | Multiple trigger/payload types |
| **`netlist_parser.py`** | Parse Verilog netlists | Extract nets, gates, connections |

### Validation & Testing

| Script | Purpose |
|--------|---------|
| **`validate_insertion.py`** | Verify Trojan insertion |
| **`verify_trojans.py`** | Check Trojan markers |
| **`generate_dataset.py`** | Create ML detector datasets |

### Utilities

| Script | Purpose |
|--------|---------|
| **`setup.sh`** | Environment setup |
| **`test_pipeline.sh`** | Run pipeline tests |
| **`run_mimic.py`** | MIMIC tool wrapper (if available) |

---

## 🔧 Detailed Usage

### 1. Feature Extraction

Extract features from a gate-level netlist:

```bash
python scripts/feature_extraction.py \
  --netlist <netlist.v> \
  --output <features.json> \
  [--hierarchical]        # For large designs
  [--sample-rate 0.1]     # Sample 10% of nets
```

**Features Extracted:**
- **Structural:** Fan-in, fan-out, gate type, logic depth
- **Testability (SCOAP):** 
  - CC0/CC1: Controllability to 0/1
  - CO: Observability
- **Combined:** Testability scores, vulnerability metrics

**Output:** JSON file with features for each net

```json
{
  "net_name_1": {
    "fan_in": 3,
    "fan_out": 5,
    "logic_depth": 12,
    "cc0": 15,
    "cc1": 18,
    "co": 25,
    "testability_score": 0.72,
    "vulnerability_score": 0.85
  },
  ...
}
```

### 2. Model Training

Train an ML model to identify vulnerable nets:

```bash
python scripts/train_insertion_model.py \
  --output <model.pkl> \
  --synthetic              # Use synthetic training data
  [--model-type rf]        # 'rf' or 'lgbm'
  [--trusthub-dir <dir>]   # If Trust-Hub available
```

**Model Types:**
- **Random Forest** (`rf`): Robust, interpretable
- **LightGBM** (`lgbm`): Fast, accurate (if available)

**Training Data:**
- **Synthetic:** Generated data simulating vulnerable nets
- **Trust-Hub:** Real Trojan locations (if dataset available)

**Output:** Trained model file (`.pkl`)

### 3. Net Scoring & Selection

Score nets and select top candidates:

```bash
python scripts/train_insertion_model.py \
  --model <model.pkl> \
  --features <features.json> \
  --predict \
  --top-k 100 \
  --output <target_nets.json>
```

**Output:** Ranked list of nets suitable for Trojan insertion

```json
{
  "num_nets": 100,
  "target_nets": [
    ["net_name_1", 0.95],
    ["net_name_2", 0.89],
    ...
  ]
}
```

### 4. Trojan Insertion

Insert Trojans into the netlist:

```bash
python scripts/trojan_inserter.py \
  --netlist <netlist.v> \
  --target-nets <target_nets.json> \
  --num-trojans 10 \
  --output <output_dir/> \
  [--seed 42]             # For reproducibility
```

**Trojan Types:**

**Triggers:**
- **Combinational:** Rare combination of signals (e.g., `A & B & C`)
- **Sequential:** FSM-based sequence detector
- **Counter:** Counter reaches threshold (rare event)

**Payloads:**
- **Leakage:** Leak internal state to output
- **DoS:** Disable functionality (force signals to 0)
- **Corruption:** Flip/corrupt critical signals

**Output:**
- Multiple Trojan-inserted netlists (`.v` files)
- Metadata file (`insertion_metadata.json`)

```json
{
  "timestamp": "2026-01-21T...",
  "original_netlist": "picorv32_gl.v",
  "num_trojans": 10,
  "insertions": [
    {
      "id": 1,
      "trigger_type": "counter",
      "payload_type": "leakage",
      "trigger_nets": ["net_A", "net_B"],
      "payload_net": "critical_signal",
      "estimated_gates": 25,
      "output_file": "picorv32_trojan_001_counter_leakage.v"
    },
    ...
  ]
}
```

---

## 🎯 Example: Complete Workflow

### Using PicoRV32

```bash
#!/bin/bash

# 1. Synthesize PicoRV32 to gate-level netlist (if not done)
cd /Users/yaroslavpopryho/Study/UIC/Research/MIMIC
source venv/bin/activate

# 2. Run complete MIMIC pipeline
python scripts/mimic_pipeline.py \
  --netlist riscv_designs/picorv32/picorv32.v \
  --output trojans/picorv32_mimic/ \
  --num-trojans 20 \
  --synthetic \
  --seed 42

# 3. Validate insertions
python scripts/validate_insertion.py \
  --original riscv_designs/picorv32/picorv32.v \
  --trojaned trojans/picorv32_mimic/trojaned_netlists/ \
  --metadata trojans/picorv32_mimic/trojaned_netlists/insertion_metadata.json

# 4. Generate ML detector dataset
python scripts/generate_dataset.py \
  --clean-dir riscv_designs/picorv32/ \
  --trojaned-dir trojans/picorv32_mimic/trojaned_netlists/ \
  --output ml_detector_testing/datasets/picorv32_dataset.csv
```

### Using CVA6 (Large Design)

For large designs, use hierarchical processing:

```bash
python scripts/mimic_pipeline.py \
  --netlist riscv_designs/cva6/core/cva6.sv \
  --output trojans/cva6_mimic/ \
  --num-trojans 50 \
  --synthetic \
  --seed 42 \
  --hierarchical \
  --sample-rate 0.05
```

---

## 📊 Understanding the Output

### Directory Structure

After running the pipeline:

```
trojans/mimic_output/
├── netlist_features.json        # Extracted features
├── insertion_model.pkl           # Trained ML model
├── target_nets.json              # Scored nets
├── pipeline_summary.json         # Pipeline metadata
└── trojaned_netlists/            # Inserted Trojans
    ├── design_trojan_001_counter_leakage.v
    ├── design_trojan_002_combinational_dos.v
    ├── ...
    └── insertion_metadata.json   # Trojan metadata
```

### Trojan Markers in Netlist

Each Trojan is marked in the Verilog code:

```verilog
module design(...);
  // Original design logic
  ...
  
  // === INSERTED TROJAN START ===
  // Trigger: counter, Payload: leakage
  // Inserted: 2026-01-21T...
  
  // Counter-based trigger: rare event
  reg [15:0] trojan_counter_1;
  wire trojan_trigger_1;
  
  always @(posedge clk or posedge rst) begin
    if (rst)
      trojan_counter_1 <= 16'h0000;
    else if (rare_net)
      trojan_counter_1 <= trojan_counter_1 + 1;
  end
  assign trojan_trigger_1 = (trojan_counter_1 == 16'hFFFF);
  
  // Payload: leakage
  wire trojan_payload_1;
  assign trojan_payload_1 = trojan_trigger_1 ? internal_signal : 1'b0;
  // === INSERTED TROJAN END ===
  
  // Rest of design
  ...
endmodule
```

---

## 🔬 Validation

### Verify Trojan Insertion

```bash
python scripts/validate_insertion.py \
  --original <original.v> \
  --trojaned <trojaned_dir/> \
  --metadata <metadata.json>
```

### Verify Trojan Details

```bash
python scripts/verify_trojans.py \
  --design <trojaned.v>
```

**Extracts:**
- Trojan type (trigger/payload)
- Location (line numbers)
- Signals used
- Estimated size

---

---


## 📚 References

1. Cruz et al., "Automatic Hardware Trojan Insertion using Machine Learning", HOST 2018
2. SCOAP: Sandia Controllability/Observability Analysis Program
3. Trust-Hub: Benchmarks for Hardware Trojan research

---

## 🤝 Contributing

To extend the pipeline:

1. **Add new feature extractors** → Edit `feature_extraction.py`
2. **Add new Trojan types** → Edit `trojan_inserter.py`
3. **Improve ML model** → Edit `train_insertion_model.py`

