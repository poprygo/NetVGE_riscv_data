# RISC-V Hardware Trojan Dataset - MULTI-CORE DESIGNS

**Generated:** January 19, 2026  
**Package Version:** 2.0
**Total Size:** 6.1 MB

---

## 📊 **Executive Summary**

This package contains **10 pairs** of CVA6 RISC-V processor designs with **verified Hardware Trojans**.

### **Key Statistics:**
- **Design Range:** 105,200 - 189,360 gates per design
- **File Sizes:** 230 KB - 413 KB per file
- **Line Counts:** 5,955 - 10,699 lines per design
- **Total Gates:** 2.8 million gates across all designs
- **Verification:** Complete structural, functional, and malicious behavior proofs

---

## 📁 **Package Structure**

```
riscv_dataset/
├── TrojanFree/              # 10 clean CVA6 designs
│   ├── cva6_5core_clean_001.v  (5,955 lines, ~105K gates)
│   ├── cva6_5core_clean_002.v  (5,955 lines, ~105K gates)
│   ├── cva6_5core_clean_003.v  (5,955 lines, ~105K gates)
│   ├── cva6_5core_clean_004.v  (5,955 lines, ~105K gates)
│   ├── cva6_7core_clean_005.v  (8,327 lines, ~147K gates)
│   ├── cva6_7core_clean_006.v  (8,327 lines, ~147K gates)
│   ├── cva6_7core_clean_007.v  (8,327 lines, ~147K gates)
│   ├── cva6_9core_clean_008.v  (10,699 lines, ~189K gates)
│   ├── cva6_9core_clean_009.v  (10,699 lines, ~189K gates)
│   └── cva6_9core_clean_010.v  (10,699 lines, ~189K gates)
│
├── TrojanInserted/          # 10 Trojanized versions
│   ├── cva6_5core_trojan_001_counter_leakage.v
│   ├── cva6_5core_trojan_002_counter_dos.v
│   ├── cva6_5core_trojan_003_combinational_leakage.v
│   ├── cva6_5core_trojan_004_counter_corruption.v
│   ├── cva6_7core_trojan_005_counter_dos.v
│   ├── cva6_7core_trojan_006_combinational_leakage.v
│   ├── cva6_7core_trojan_007_combinational_corruption.v
│   ├── cva6_9core_trojan_008_counter_leakage.v
│   ├── cva6_9core_trojan_009_combinational_dos.v
│   └── cva6_9core_trojan_010_combinational_leakage.v
│
├── Proofs/
│   ├── comparison/          # Structural verification (30 files)
│   │   ├── diff_001.txt - diff_010.txt
│   │   ├── trojan_location_001.txt - trojan_location_010.txt
│   │   └── malicious_analysis_001.txt - malicious_analysis_010.txt
│   │
│   └── functional_simulation/
│       ├── SIMULATION_PROOF.log     # Actual simulation results
│       └── final_proof.vvp          # Compiled simulation
```

---

## 🔍 **Design Details**

### **5-Core Designs (4 designs, ~105K gates each)**

| Design | Trigger | Payload | File Size | Lines | Gates |
|--------|---------|---------|-----------|-------|-------|
| 001 | Counter | Leakage | 230 KB | 5,955 | 105,200 |
| 002 | Counter | DoS | 230 KB | 5,955 | 105,200 |
| 003 | Combinational | Leakage | 230 KB | 5,955 | 105,200 |
| 004 | Counter | Corruption | 230 KB | 5,955 | 105,200 |

**Method:** 5× full CVA6 core (1,178 lines each) inlined with renamed signals

### **7-Core Designs (3 designs, ~147K gates each)**

| Design | Trigger | Payload | File Size | Lines | Gates |
|--------|---------|---------|-----------|-------|-------|
| 005 | Counter | DoS | 321 KB | 8,327 | 147,280 |
| 006 | Combinational | Leakage | 321 KB | 8,327 | 147,280 |
| 007 | Combinational | Corruption | 321 KB | 8,327 | 147,280 |

**Method:** 7× full CVA6 core inlined with renamed signals

### **9-Core Designs (3 designs, ~189K gates each)**

| Design | Trigger | Payload | File Size | Lines | Gates |
|--------|---------|---------|-----------|-------|-------|
| 008 | Counter | Leakage | 413 KB | 10,699 | 189,360 |
| 009 | Combinational | DoS | 413 KB | 10,699 | 189,360 |
| 010 | Combinational | Leakage | 413 KB | 10,699 | 189,360 |

**Method:** 9× full CVA6 core inlined with renamed signals

---

## 🔒 **Trojan Mechanisms**

### **Trigger Types:**

#### **1. Counter-Based (Sequential)**
```verilog
reg [15:0] trojan_counter;
always @(posedge clk_i or posedge rst_ni) begin
  if (rst_ni)
    trojan_counter <= 16'h0000;
  else if (boot_addr_i[0])
    trojan_counter <= trojan_counter + 1;
end
assign trojan_trigger = (trojan_counter == 16'hFFFF);
```
- Activates after ~65,535 cycles
- Rare event (low activation probability)
- Stealthy (difficult to trigger in testing)

#### **2. Combinational (Rare Condition)**
```verilog
wire trojan_trigger;
assign trojan_trigger = boot_addr_i[0] & boot_addr_i[1] & boot_addr_i[2];
```
- Activates when all conditions met simultaneously
- Extremely rare in normal operation
- Zero state overhead

### **Payload Types:**

#### **1. Data Leakage**
```verilog
wire trojan_payload;
assign trojan_payload = trojan_trigger ? boot_addr_i[0] : 1'b0;
```
**Effect:** Internal data exposed to external observer

#### **2. Denial of Service (DoS)**
```verilog
wire trojan_payload;
assign trojan_payload = trojan_trigger ? 1'b0 : boot_addr_i[0];
```
**Effect:** Critical operations blocked

#### **3. Data Corruption**
```verilog
wire trojan_payload;
assign trojan_payload = trojan_trigger ? ~boot_addr_i[0] : boot_addr_i[0];
```
**Effect:** Signals inverted causing incorrect execution

---

##  **Verification & Proofs**

### **1. Structural Verification (EDA Tool: `diff`)**

**Location:** `Proofs/comparison/diff_*.txt`

Each diff file shows:
- Exact lines changed between clean and Trojaned designs
- 12-20 lines modified per design
- Trojan markers clearly visible

**Example:** Design 001 has 20 lines different, all within the Trojan block.

### **2. Trojan Location Analysis**

**Location:** `Proofs/comparison/trojan_location_*.txt`

Each file contains:
- Exact line numbers of Trojan insertion
- Complete Trojan code listing
- Size analysis

**Example:**
```
Design 001: Trojan at lines 5955-5972 (18 lines)
Design 010: Trojan at lines 10699-10708 (10 lines)
```

### **3. Malicious Behavior Analysis**

**Location:** `Proofs/comparison/malicious_analysis_*.txt`

Each analysis includes:
- Trigger mechanism description
- Payload effect documentation
- Complete attack scenario walkthrough
- Stealth characteristics
- Impact assessment

### **4. Functional Simulation**

**Location:** `Proofs/functional_simulation/SIMULATION_PROOF.log`

**Proven via Icarus Verilog simulation:**

 **Counter reaches 65,535 and triggers**
```
Counter: 65535 (0xffff) → Trigger: 1
```

 **Payload leaks data when triggered**
```
Dormant: trigger=0, payload=0
Active:  trigger=1, payload=1 (DATA LEAKED!)
```

**Signal corruption (inversion)**
```
Original:  1 (should commit)
Corrupted: 0 (INVERTED - drops instruction!)
```

 **Denial of Service (blocking)**
```
System wants: 1 (issue instruction)
System gets:  0 (BLOCKED!)
```

---
