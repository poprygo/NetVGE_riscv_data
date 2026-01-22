#!/usr/bin/env python3
"""
Automatic Trojan Inserter
Inserts Hardware Trojans into gate-level netlists
Based on MIMIC methodology
"""

import argparse
import json
import random
from pathlib import Path
from datetime import datetime


class TrojanType:
    """Types of Trojan triggers and payloads"""
    
    TRIGGERS = {
        'combinational': 'Rare combination of signals',
        'sequential': 'Sequence of events (FSM)',
        'counter': 'Counter-based trigger'
    }
    
    PAYLOADS = {
        'leakage': 'Leak internal state to output',
        'dos': 'Denial of service (disable functionality)',
        'corruption': 'Corrupt output or state'
    }


class TrojanInserter:
    """Insert Hardware Trojans into netlists"""
    
    def __init__(self, netlist_file, output_dir):
        self.netlist_file = netlist_file
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Read original netlist
        with open(netlist_file, 'r') as f:
            self.netlist_content = f.read()
        
        # Extract module name
        import re
        match = re.search(r'module\s+(\w+)', self.netlist_content)
        self.module_name = match.group(1) if match else 'design'
        
        self.trojan_counter = 0
    
    def insert_trojan(self, target_nets, trigger_type, payload_type, metadata=None):
        """
        Insert a Trojan into the netlist
        
        Args:
            target_nets: List of (net_name, score) tuples
            trigger_type: Type of trigger (combinational/sequential/counter)
            payload_type: Type of payload (leakage/dos/corruption)
            metadata: Additional metadata about the Trojan
        
        Returns:
            Path to Trojan-inserted netlist
        """
        self.trojan_counter += 1
        
        print(f"\nInserting Trojan #{self.trojan_counter}")
        print(f"  Trigger: {trigger_type}")
        print(f"  Payload: {payload_type}")
        print(f"  Target nets: {len(target_nets)}")
        
        # Select specific nets for trigger and payload
        trigger_nets = target_nets[:min(3, len(target_nets))]  # Use top 3 for trigger
        payload_net = target_nets[0] if target_nets else None  # Use top 1 for payload
        
        print(f"  Trigger nets: {[n[0] for n in trigger_nets]}")
        if payload_net:
            print(f"  Payload net: {payload_net[0]}")
        
        # Generate Trojan logic
        trojan_verilog = self._generate_trojan_logic(
            trigger_nets, payload_net, trigger_type, payload_type
        )
        
        # Insert into netlist
        modified_netlist = self._insert_into_netlist(trojan_verilog)
        
        # Save modified netlist
        output_file = self.output_dir / f"{self.module_name}_trojan_{self.trojan_counter:03d}_{trigger_type}_{payload_type}.v"
        
        with open(output_file, 'w') as f:
            f.write(modified_netlist)
        
        print(f"  Saved: {output_file}")
        
        # Save metadata
        trojan_metadata = {
            'id': self.trojan_counter,
            'original_netlist': str(self.netlist_file),
            'output_file': str(output_file),
            'trigger_type': trigger_type,
            'payload_type': payload_type,
            'trigger_nets': [n[0] for n in trigger_nets],
            'trigger_scores': [n[1] for n in trigger_nets],
            'payload_net': payload_net[0] if payload_net else None,
            'payload_score': payload_net[1] if payload_net else None,
            'timestamp': datetime.now().isoformat(),
            'estimated_gates': self._estimate_trojan_size(trigger_type, payload_type)
        }
        
        if metadata:
            trojan_metadata.update(metadata)
        
        return output_file, trojan_metadata
    
    def _generate_trojan_logic(self, trigger_nets, payload_net, trigger_type, payload_type):
        """Generate Verilog code for Trojan logic"""
        
        lines = []
        lines.append("\n  // === INSERTED TROJAN START ===")
        lines.append(f"  // Trigger: {trigger_type}, Payload: {payload_type}")
        lines.append(f"  // Inserted: {datetime.now().isoformat()}")
        
        trigger_signal = f"trojan_trigger_{self.trojan_counter}"
        payload_signal = f"trojan_payload_{self.trojan_counter}"
        
        # Generate trigger logic
        if trigger_type == 'combinational':
            # Rare combination of signals
            lines.append(f"\n  // Combinational trigger: rare combination")
            trigger_expr = ' & '.join([f"({net[0]})" for net in trigger_nets])
            lines.append(f"  wire {trigger_signal};")
            lines.append(f"  assign {trigger_signal} = {trigger_expr};")
        
        elif trigger_type == 'sequential':
            # Simple FSM-based trigger
            lines.append(f"\n  // Sequential trigger: FSM")
            lines.append(f"  reg [1:0] trojan_state_{self.trojan_counter};")
            lines.append(f"  wire {trigger_signal};")
            lines.append(f"\n  always @(posedge clk or posedge rst) begin")
            lines.append(f"    if (rst)")
            lines.append(f"      trojan_state_{self.trojan_counter} <= 2'b00;")
            lines.append(f"    else begin")
            lines.append(f"      case (trojan_state_{self.trojan_counter})")
            lines.append(f"        2'b00: if ({trigger_nets[0][0]}) trojan_state_{self.trojan_counter} <= 2'b01;")
            if len(trigger_nets) > 1:
                lines.append(f"        2'b01: if ({trigger_nets[1][0]}) trojan_state_{self.trojan_counter} <= 2'b10;")
            if len(trigger_nets) > 2:
                lines.append(f"        2'b10: if ({trigger_nets[2][0]}) trojan_state_{self.trojan_counter} <= 2'b11;")
            lines.append(f"        default: trojan_state_{self.trojan_counter} <= 2'b00;")
            lines.append(f"      endcase")
            lines.append(f"    end")
            lines.append(f"  end")
            lines.append(f"  assign {trigger_signal} = (trojan_state_{self.trojan_counter} == 2'b11);")
        
        elif trigger_type == 'counter':
            # Counter-based trigger (rare activation)
            lines.append(f"\n  // Counter-based trigger: rare event")
            lines.append(f"  reg [15:0] trojan_counter_{self.trojan_counter};")
            lines.append(f"  wire {trigger_signal};")
            lines.append(f"\n  always @(posedge clk or posedge rst) begin")
            lines.append(f"    if (rst)")
            lines.append(f"      trojan_counter_{self.trojan_counter} <= 16'h0000;")
            lines.append(f"    else if ({trigger_nets[0][0]})")
            lines.append(f"      trojan_counter_{self.trojan_counter} <= trojan_counter_{self.trojan_counter} + 1;")
            lines.append(f"  end")
            lines.append(f"  assign {trigger_signal} = (trojan_counter_{self.trojan_counter} == 16'hFFFF);")
        
        # Generate payload logic
        if payload_net:
            lines.append(f"\n  // Payload: {payload_type}")
            
            if payload_type == 'leakage':
                # Leak internal state to a new output or modify existing output
                lines.append(f"  wire {payload_signal};")
                lines.append(f"  assign {payload_signal} = {trigger_signal} ? {payload_net[0]} : 1'b0;")
                lines.append(f"  // Note: Connect {payload_signal} to an output for leakage")
            
            elif payload_type == 'dos':
                # Disable functionality by forcing signal to 0
                lines.append(f"  wire {payload_signal};")
                lines.append(f"  assign {payload_signal} = {trigger_signal} ? 1'b0 : {payload_net[0]};")
                lines.append(f"  // Note: Replace {payload_net[0]} with {payload_signal} in the design")
            
            elif payload_type == 'corruption':
                # Corrupt signal by flipping it
                lines.append(f"  wire {payload_signal};")
                lines.append(f"  assign {payload_signal} = {trigger_signal} ? ~{payload_net[0]} : {payload_net[0]};")
                lines.append(f"  // Note: Replace {payload_net[0]} with {payload_signal} in the design")
        
        lines.append("  // === INSERTED TROJAN END ===\n")
        
        return '\n'.join(lines)
    
    def _insert_into_netlist(self, trojan_verilog):
        """Insert Trojan Verilog into the netlist"""
        
        # Find insertion point (before endmodule)
        import re
        
        # Find the last endmodule
        match = re.search(r'(endmodule)', self.netlist_content)
        
        if match:
            pos = match.start()
            modified = (
                self.netlist_content[:pos] +
                trojan_verilog + '\n' +
                self.netlist_content[pos:]
            )
        else:
            # If no endmodule found, append at the end
            modified = self.netlist_content + '\n' + trojan_verilog
        
        return modified
    
    def _estimate_trojan_size(self, trigger_type, payload_type):
        """Estimate number of gates added by Trojan"""
        
        size = 0
        
        # Trigger gates
        if trigger_type == 'combinational':
            size += 5  # AND gates
        elif trigger_type == 'sequential':
            size += 15  # FSM + logic
        elif trigger_type == 'counter':
            size += 20  # Counter + comparator
        
        # Payload gates
        if payload_type in ['leakage', 'dos', 'corruption']:
            size += 5  # Mux or logic gates
        
        # Add some randomness
        size += random.randint(-2, 5)
        
        return max(size, 3)


def insert_multiple_trojans(netlist_file, target_nets, num_trojans, output_dir, config=None):
    """
    Insert multiple Trojans with different types
    
    Args:
        netlist_file: Input gate-level netlist
        target_nets: List of (net_name, score) tuples
        num_trojans: Number of Trojans to insert
        output_dir: Output directory
        config: Configuration dict
    
    Returns:
        List of (output_file, metadata) tuples
    """
    print(f"\nInserting {num_trojans} Trojans into {netlist_file}")
    
    inserter = TrojanInserter(netlist_file, output_dir)
    
    results = []
    
    trigger_types = ['combinational', 'sequential', 'counter']
    payload_types = ['leakage', 'dos', 'corruption']
    
    for i in range(num_trojans):
        # Select random trigger and payload types
        trigger_type = random.choice(trigger_types)
        payload_type = random.choice(payload_types)
        
        # Select nets for this Trojan (rotate through top nets)
        start_idx = (i * 10) % max(1, len(target_nets) - 10)
        trojan_nets = target_nets[start_idx:start_idx + 10]
        
        if not trojan_nets:
            print(f"Warning: Not enough target nets for Trojan {i+1}")
            continue
        
        # Insert Trojan
        try:
            output_file, metadata = inserter.insert_trojan(
                trojan_nets, trigger_type, payload_type
            )
            results.append((output_file, metadata))
        except Exception as e:
            print(f"Error inserting Trojan {i+1}: {e}")
    
    # Save all metadata
    metadata_file = Path(output_dir) / 'insertion_metadata.json'
    with open(metadata_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'original_netlist': str(netlist_file),
            'num_trojans': len(results),
            'insertions': [m for _, m in results]
        }, f, indent=2)
    
    print(f"\n✓ Inserted {len(results)} Trojans")
    print(f"  Output directory: {output_dir}")
    print(f"  Metadata: {metadata_file}")
    
    return results


def main():
    parser = argparse.ArgumentParser(
        description='Insert Hardware Trojans into gate-level netlist',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        '--netlist',
        required=True,
        help='Input gate-level Verilog netlist'
    )
    
    parser.add_argument(
        '--target-nets',
        required=True,
        help='JSON file with scored target nets'
    )
    
    parser.add_argument(
        '--num-trojans',
        type=int,
        default=10,
        help='Number of Trojans to insert'
    )
    
    parser.add_argument(
        '--output',
        required=True,
        help='Output directory for Trojan-inserted netlists'
    )
    
    parser.add_argument(
        '--seed',
        type=int,
        default=42,
        help='Random seed for reproducibility'
    )
    
    args = parser.parse_args()
    
    random.seed(args.seed)
    
    # Load target nets
    with open(args.target_nets, 'r') as f:
        target_nets_data = json.load(f)
    
    # Convert to list of tuples
    if isinstance(target_nets_data, list):
        # Assume format: [(net_name, score), ...]
        target_nets = target_nets_data
    elif isinstance(target_nets_data, dict) and 'target_nets' in target_nets_data:
        target_nets = target_nets_data['target_nets']
    else:
        raise ValueError("Invalid target nets format")
    
    print(f"Loaded {len(target_nets)} target nets")
    
    # Insert Trojans
    results = insert_multiple_trojans(
        args.netlist,
        target_nets,
        args.num_trojans,
        args.output
    )
    
    print("\n✓ Trojan insertion complete!")
    
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
