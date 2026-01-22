#!/usr/bin/env python3
"""
Trojan Insertion Validation Script
Validates Trojan-inserted netlists through simulation
"""

import argparse
import subprocess
import sys
from pathlib import Path
import json
from datetime import datetime


def run_simulation(netlist, testbench, output_vcd=None, defines=None):
    """Run Icarus Verilog simulation"""
    
    print(f"Simulating {netlist}...")
    
    # Compile
    compile_cmd = ['iverilog', '-o', 'sim.out', testbench, netlist]
    
    # Add defines
    if defines:
        for key, value in defines.items():
            compile_cmd.extend(['-D', f'{key}={value}'])
    
    try:
        result = subprocess.run(
            compile_cmd,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print("Compilation failed:")
            print(result.stderr)
            return None
        
        # Run simulation
        sim_cmd = ['vvp', 'sim.out']
        if output_vcd:
            sim_cmd.extend(['-lxt2', output_vcd])
        
        result = subprocess.run(
            sim_cmd,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print("Simulation failed:")
            print(result.stderr)
            return None
        
        # Cleanup
        Path('sim.out').unlink(missing_ok=True)
        
        return result.stdout
        
    except Exception as e:
        print(f"Error during simulation: {e}")
        return None


def compare_outputs(original_output, trojaned_output):
    """Compare simulation outputs"""
    
    # Simple comparison - can be enhanced
    original_lines = original_output.strip().split('\n')
    trojaned_lines = trojaned_output.strip().split('\n')
    
    if len(original_lines) != len(trojaned_lines):
        return False, f"Line count mismatch: {len(original_lines)} vs {len(trojaned_lines)}"
    
    differences = []
    for i, (orig, troj) in enumerate(zip(original_lines, trojaned_lines)):
        if orig != troj:
            differences.append((i+1, orig, troj))
    
    if not differences:
        return True, "Outputs match"
    else:
        return False, f"{len(differences)} differences found"


def validate_no_trigger(original_netlist, trojaned_netlist, testbench):
    """Validate that without trigger, behavior is identical"""
    
    print("\n=== Validation: No-Trigger Behavior ===")
    
    # Simulate original
    original_output = run_simulation(original_netlist, testbench)
    if original_output is None:
        return False
    
    # Simulate trojaned (without trigger)
    trojaned_output = run_simulation(
        trojaned_netlist,
        testbench,
        defines={'TRIGGER_ACTIVE': '0'}
    )
    if trojaned_output is None:
        return False
    
    # Compare
    match, msg = compare_outputs(original_output, trojaned_output)
    
    if match:
        print("✓ No-trigger behavior matches original")
        return True
    else:
        print(f"✗ No-trigger behavior differs: {msg}")
        return False


def validate_with_trigger(trojaned_netlist, testbench):
    """Validate that with trigger, Trojan activates"""
    
    print("\n=== Validation: Trigger Activation ===")
    
    # Simulate without trigger
    output_no_trigger = run_simulation(
        trojaned_netlist,
        testbench,
        defines={'TRIGGER_ACTIVE': '0'}
    )
    if output_no_trigger is None:
        return False
    
    # Simulate with trigger
    output_with_trigger = run_simulation(
        trojaned_netlist,
        testbench,
        defines={'TRIGGER_ACTIVE': '1'}
    )
    if output_with_trigger is None:
        return False
    
    # Compare - they should differ
    match, msg = compare_outputs(output_no_trigger, output_with_trigger)
    
    if not match:
        print("✓ Trigger causes behavior change (Trojan active)")
        return True
    else:
        print("✗ Trigger does not change behavior (Trojan may be inactive)")
        return False


def analyze_netlist_size(netlist):
    """Analyze netlist to count gates, nets, etc."""
    
    try:
        with open(netlist, 'r') as f:
            content = f.read()
        
        # Simple analysis - count module instantiations
        lines = content.split('\n')
        
        stats = {
            'lines': len(lines),
            'modules': content.count('module '),
            'wires': content.count('wire '),
            'inputs': content.count('input '),
            'outputs': content.count('output '),
            'gate_instances': 0
        }
        
        # Count gate instances (very rough)
        for line in lines:
            line = line.strip()
            if line and not line.startswith('//') and not line.startswith('module') \
               and not line.startswith('input') and not line.startswith('output') \
               and not line.startswith('wire') and not line.startswith('endmodule'):
                if '(' in line and ')' in line:
                    stats['gate_instances'] += 1
        
        return stats
        
    except Exception as e:
        print(f"Error analyzing netlist: {e}")
        return None


def calculate_overhead(original_stats, trojaned_stats):
    """Calculate area overhead"""
    
    if not original_stats or not trojaned_stats:
        return None
    
    overhead = {}
    for key in ['lines', 'wires', 'gate_instances']:
        if key in original_stats and key in trojaned_stats:
            orig = original_stats[key]
            troj = trojaned_stats[key]
            if orig > 0:
                overhead[key] = {
                    'original': orig,
                    'trojaned': troj,
                    'increase': troj - orig,
                    'percentage': ((troj - orig) / orig) * 100
                }
    
    return overhead


def main():
    parser = argparse.ArgumentParser(
        description='Validate Trojan-inserted netlists',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        '--original',
        required=True,
        help='Original (clean) gate-level netlist'
    )
    
    parser.add_argument(
        '--trojaned',
        required=True,
        help='Trojan-inserted gate-level netlist'
    )
    
    parser.add_argument(
        '--testbench',
        required=True,
        help='Verilog testbench for simulation'
    )
    
    parser.add_argument(
        '--skip-no-trigger',
        action='store_true',
        help='Skip no-trigger validation'
    )
    
    parser.add_argument(
        '--skip-with-trigger',
        action='store_true',
        help='Skip with-trigger validation'
    )
    
    parser.add_argument(
        '--output-report',
        help='Save validation report to JSON file'
    )
    
    args = parser.parse_args()
    
    # Check files exist
    for f in [args.original, args.trojaned, args.testbench]:
        if not Path(f).exists():
            print(f"Error: File not found: {f}")
            sys.exit(1)
    
    print("="*50)
    print("Trojan Insertion Validation")
    print("="*50)
    print(f"Original: {args.original}")
    print(f"Trojaned: {args.trojaned}")
    print(f"Testbench: {args.testbench}")
    
    # Analyze netlist sizes
    print("\n=== Netlist Analysis ===")
    original_stats = analyze_netlist_size(args.original)
    trojaned_stats = analyze_netlist_size(args.trojaned)
    
    if original_stats and trojaned_stats:
        overhead = calculate_overhead(original_stats, trojaned_stats)
        if overhead:
            print("\nOverhead Analysis:")
            for key, data in overhead.items():
                print(f"  {key}:")
                print(f"    Original: {data['original']}")
                print(f"    Trojaned: {data['trojaned']}")
                print(f"    Increase: +{data['increase']} ({data['percentage']:.2f}%)")
    
    # Run validations
    results = {
        'timestamp': datetime.now().isoformat(),
        'files': {
            'original': args.original,
            'trojaned': args.trojaned,
            'testbench': args.testbench
        },
        'statistics': {
            'original': original_stats,
            'trojaned': trojaned_stats,
            'overhead': overhead
        },
        'validations': {}
    }
    
    success = True
    
    if not args.skip_no_trigger:
        no_trigger_ok = validate_no_trigger(
            args.original,
            args.trojaned,
            args.testbench
        )
        results['validations']['no_trigger'] = no_trigger_ok
        success = success and no_trigger_ok
    
    if not args.skip_with_trigger:
        with_trigger_ok = validate_with_trigger(
            args.trojaned,
            args.testbench
        )
        results['validations']['with_trigger'] = with_trigger_ok
        success = success and with_trigger_ok
    
    # Save report
    if args.output_report:
        with open(args.output_report, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nReport saved: {args.output_report}")
    
    # Summary
    print("\n" + "="*50)
    if success:
        print("✓ All validations passed")
        sys.exit(0)
    else:
        print("✗ Some validations failed")
        sys.exit(1)


if __name__ == '__main__':
    main()
