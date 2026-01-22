#!/usr/bin/env python3
"""
RISC-V Synthesis Script
Synthesizes RTL to gate-level netlist using Yosys
"""

import argparse
import os
import subprocess
import sys
import json
from pathlib import Path
from datetime import datetime


def check_tools():
    """Check if required tools are available"""
    tools = {
        'yosys': 'Yosys synthesis tool',
        'iverilog': 'Icarus Verilog (for validation)'
    }
    
    missing = []
    for tool, description in tools.items():
        if subprocess.run(['which', tool], capture_output=True).returncode != 0:
            missing.append(f"{tool} ({description})")
    
    if missing:
        print("Error: Missing required tools:")
        for tool in missing:
            print(f"  - {tool}")
        sys.exit(1)


def create_synthesis_script(rtl_files, top_module, lib_file, output_file):
    """Create Yosys synthesis TCL script"""
    
    script = f"""
# Synthesis script for {top_module}
# Generated: {datetime.now().isoformat()}

# Read standard cell library
read_liberty {lib_file}

# Read RTL files
"""
    
    if isinstance(rtl_files, list):
        for rtl in rtl_files:
            script += f"read_verilog {rtl}\n"
    else:
        script += f"read_verilog {rtl_files}\n"
    
    script += f"""
# Set hierarchy
hierarchy -top {top_module}
hierarchy -check

# High-level synthesis
proc
opt
fsm
opt
memory
opt

# Technology-independent optimization
techmap
opt

# Technology mapping with liberty
dfflibmap -liberty {lib_file}
abc -liberty {lib_file}

# Clean up
clean

# Final optimization
opt_clean -purge

# Statistics
stat

# Write gate-level netlist
write_verilog -noattr {output_file}

# Write statistics to JSON
stat -json > {output_file}.stat.json
"""
    
    return script


def run_synthesis(rtl_files, top_module, lib_file, output_file, script_file=None):
    """Run Yosys synthesis"""
    
    print(f"Synthesizing {top_module}...")
    print(f"  RTL: {rtl_files}")
    print(f"  Library: {lib_file}")
    print(f"  Output: {output_file}")
    
    # Create synthesis script
    script = create_synthesis_script(rtl_files, top_module, lib_file, output_file)
    
    # Save script if requested
    if script_file:
        script_path = Path(script_file)
        script_path.parent.mkdir(parents=True, exist_ok=True)
        with open(script_file, 'w') as f:
            f.write(script)
        print(f"  Script saved: {script_file}")
    
    # Create temporary script file
    temp_script = Path(output_file).parent / f"temp_synth_{top_module}.tcl"
    with open(temp_script, 'w') as f:
        f.write(script)
    
    # Run Yosys
    try:
        log_file = f"{output_file}.log"
        cmd = ['yosys', '-s', str(temp_script)]
        
        with open(log_file, 'w') as log:
            result = subprocess.run(
                cmd,
                stdout=log,
                stderr=subprocess.STDOUT,
                text=True
            )
        
        if result.returncode != 0:
            print(f"Error: Synthesis failed. Check log: {log_file}")
            return False
        
        print(f"  Synthesis complete!")
        print(f"  Log: {log_file}")
        
        # Cleanup temp script
        if not script_file:
            temp_script.unlink()
        
        return True
        
    except Exception as e:
        print(f"Error running Yosys: {e}")
        return False


def validate_netlist(netlist_file, lib_verilog=None):
    """Validate gate-level netlist with iverilog"""
    
    print(f"\nValidating netlist {netlist_file}...")
    
    cmd = ['iverilog', '-o', '/dev/null', netlist_file]
    if lib_verilog:
        cmd.append(lib_verilog)
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print("Validation warnings/errors:")
            print(result.stderr)
            return False
        
        print("  Netlist validation: OK")
        return True
        
    except Exception as e:
        print(f"Error validating netlist: {e}")
        return False


def parse_statistics(stat_file):
    """Parse Yosys statistics JSON"""
    
    if not Path(stat_file).exists():
        return None
    
    try:
        with open(stat_file, 'r') as f:
            stats = json.load(f)
        
        # Extract key metrics
        modules = stats.get('modules', {})
        if modules:
            top_module = list(modules.keys())[0]
            module_stats = modules[top_module]
            
            return {
                'module': top_module,
                'num_wires': module_stats.get('num_wires', 0),
                'num_cells': module_stats.get('num_cells_by_type', {}).get('$abstract', 0),
                'num_cells_total': sum(module_stats.get('num_cells_by_type', {}).values()),
                'cell_types': module_stats.get('num_cells_by_type', {})
            }
    except Exception as e:
        print(f"Error parsing statistics: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description='Synthesize RISC-V RTL to gate-level netlist',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        '--rtl',
        required=True,
        nargs='+',
        help='RTL Verilog file(s)'
    )
    
    parser.add_argument(
        '--top',
        required=True,
        help='Top module name'
    )
    
    parser.add_argument(
        '--lib',
        required=True,
        help='Standard cell Liberty library file (.lib)'
    )
    
    parser.add_argument(
        '--lib-verilog',
        help='Standard cell Verilog file (.v) for validation'
    )
    
    parser.add_argument(
        '--output',
        required=True,
        help='Output gate-level netlist file'
    )
    
    parser.add_argument(
        '--save-script',
        help='Save synthesis script to this file'
    )
    
    parser.add_argument(
        '--no-validate',
        action='store_true',
        help='Skip netlist validation'
    )
    
    args = parser.parse_args()
    
    # Check tools
    check_tools()
    
    # Check inputs exist
    for rtl in args.rtl:
        if not Path(rtl).exists():
            print(f"Error: RTL file not found: {rtl}")
            sys.exit(1)
    
    if not Path(args.lib).exists():
        print(f"Error: Library file not found: {args.lib}")
        sys.exit(1)
    
    # Create output directory
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    
    # Run synthesis
    success = run_synthesis(
        rtl_files=args.rtl,
        top_module=args.top,
        lib_file=args.lib,
        output_file=args.output,
        script_file=args.save_script
    )
    
    if not success:
        sys.exit(1)
    
    # Parse and display statistics
    stat_file = f"{args.output}.stat.json"
    stats = parse_statistics(stat_file)
    if stats:
        print("\nSynthesis Statistics:")
        print(f"  Module: {stats['module']}")
        print(f"  Wires: {stats['num_wires']}")
        print(f"  Cells: {stats['num_cells_total']}")
        print(f"  Cell types: {len(stats['cell_types'])}")
    
    # Validate netlist
    if not args.no_validate:
        validate_success = validate_netlist(args.output, args.lib_verilog)
        if not validate_success:
            print("\nWarning: Netlist validation failed")
    
    print("\n✓ Synthesis complete!")
    print(f"  Output: {args.output}")


if __name__ == '__main__':
    main()
