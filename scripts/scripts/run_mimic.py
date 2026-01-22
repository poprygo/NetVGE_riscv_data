#!/usr/bin/env python3
"""
MIMIC Execution Wrapper
Runs MIMIC tool for Hardware Trojan insertion
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime
import shutil


def load_config(config_file):
    """Load MIMIC configuration file"""
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        return config
    except Exception as e:
        print(f"Error loading config: {e}")
        sys.exit(1)


def validate_config(config):
    """Validate configuration parameters"""
    required_fields = ['input', 'seed_trojans', 'insertion_parameters', 'output']
    
    for field in required_fields:
        if field not in config:
            print(f"Error: Missing required field in config: {field}")
            return False
    
    # Check input netlist exists
    netlist = config['input'].get('netlist')
    if not netlist or not Path(netlist).exists():
        print(f"Error: Input netlist not found: {netlist}")
        return False
    
    # Check seed trojans directory
    seed_dir = config['seed_trojans'].get('directory')
    if not seed_dir or not Path(seed_dir).exists():
        print(f"Error: Seed trojans directory not found: {seed_dir}")
        return False
    
    return True


def check_mimic_tool():
    """Check if MIMIC tool is available"""
    # Try to find MIMIC executable
    mimic_paths = [
        'mimic',
        './mimic_tool/bin/mimic',
        '../mimic_tool/bin/mimic',
        os.path.expanduser('~/mimic/bin/mimic')
    ]
    
    for path in mimic_paths:
        if shutil.which(path):
            return path
    
    print("\nWarning: MIMIC tool not found in PATH")
    print("Expected locations:")
    for path in mimic_paths:
        print(f"  - {path}")
    print("\nOptions:")
    print("  1. Install MIMIC and add to PATH")
    print("  2. Use --use-simplified flag to use simplified implementation")
    print("  3. Specify MIMIC path with --mimic-path")
    
    return None


def run_mimic_tool(config_file, mimic_path='mimic', verbose=False):
    """Run actual MIMIC tool"""
    
    print(f"Running MIMIC tool...")
    print(f"  Config: {config_file}")
    print(f"  Tool: {mimic_path}")
    
    cmd = [mimic_path, '--config', config_file]
    if verbose:
        cmd.append('--verbose')
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )
        
        if verbose or result.returncode != 0:
            print(result.stdout)
            if result.stderr:
                print(result.stderr)
        
        if result.returncode != 0:
            print(f"Error: MIMIC execution failed with code {result.returncode}")
            return False
        
        print("✓ MIMIC execution complete")
        return True
        
    except Exception as e:
        print(f"Error running MIMIC: {e}")
        return False


def run_simplified_mimic(config, output_dir, num_insertions=10):
    """
    Simplified MIMIC implementation
    Use this if the actual MIMIC tool is not available
    """
    
    print("\n" + "="*50)
    print("RUNNING SIMPLIFIED MIMIC IMPLEMENTATION")
    print("="*50)
    print("\nNote: This is a placeholder implementation.")
    print("For actual Trojan insertion, you need the real MIMIC tool.")
    print("This will create dummy outputs to demonstrate the workflow.\n")
    
    # Load input netlist
    netlist_file = config['input']['netlist']
    print(f"Input netlist: {netlist_file}")
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Read seed trojans
    seed_dir = Path(config['seed_trojans']['directory'])
    seed_files = list(seed_dir.rglob('*.v'))
    print(f"Found {len(seed_files)} seed Trojan files")
    
    # Generate placeholder insertions
    metadata = {
        'timestamp': datetime.now().isoformat(),
        'config': config,
        'insertions': []
    }
    
    print(f"\nGenerating {num_insertions} Trojan insertions...")
    
    for i in range(1, num_insertions + 1):
        # Determine Trojan type
        trojan_types = ['comb', 'seq', 'temp']
        sizes = ['small', 'medium', 'large']
        
        trojan_type = trojan_types[i % len(trojan_types)]
        size = sizes[i % len(sizes)]
        
        # Create output filename
        top_module = config['input']['top_module']
        output_file = output_path / f"{top_module}_trojan_{i:03d}_{trojan_type}_{size}.v"
        
        # Copy original netlist (in real MIMIC, this would be modified)
        shutil.copy(netlist_file, output_file)
        
        # Add metadata
        insertion_metadata = {
            'id': i,
            'type': trojan_type,
            'size': size,
            'output_file': str(output_file),
            'trigger_signals': ['signal_A', 'signal_B'],
            'payload_type': 'leakage' if i % 2 == 0 else 'dos',
            'gates_added': (i % 50) + 10,
            'activation_probability': 10 ** (-(i % 6 + 1))
        }
        
        metadata['insertions'].append(insertion_metadata)
        
        print(f"  [{i:3d}/{num_insertions}] {output_file.name}")
    
    # Save metadata
    metadata_file = output_path / 'insertion_metadata.json'
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"\n✓ Generated {num_insertions} Trojan-inserted netlists")
    print(f"  Output directory: {output_dir}")
    print(f"  Metadata: {metadata_file}")
    
    print("\n" + "="*50)
    print("IMPORTANT: These are PLACEHOLDER outputs!")
    print("To get real Trojan insertions:")
    print("  1. Obtain MIMIC tool from University of Florida")
    print("  2. Run with: python scripts/run_mimic.py --config <config>")
    print("="*50 + "\n")
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description='Run MIMIC for Hardware Trojan insertion',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        '--config',
        required=True,
        help='MIMIC configuration JSON file'
    )
    
    parser.add_argument(
        '--mimic-path',
        default='mimic',
        help='Path to MIMIC executable'
    )
    
    parser.add_argument(
        '--use-simplified',
        action='store_true',
        help='Use simplified implementation (if MIMIC not available)'
    )
    
    parser.add_argument(
        '--num-insertions',
        type=int,
        default=10,
        help='Number of Trojan insertions (for simplified mode)'
    )
    
    parser.add_argument(
        '--output',
        help='Output directory (overrides config)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Verbose output'
    )
    
    args = parser.parse_args()
    
    # Load configuration
    print(f"Loading configuration: {args.config}")
    config = load_config(args.config)
    
    # Validate configuration
    if not validate_config(config):
        sys.exit(1)
    
    print("✓ Configuration valid")
    
    # Determine output directory
    output_dir = args.output or config['output']['directory']
    
    # Check if MIMIC tool is available
    if args.use_simplified:
        # Use simplified implementation
        success = run_simplified_mimic(config, output_dir, args.num_insertions)
    else:
        mimic_path = check_mimic_tool()
        
        if not mimic_path:
            print("\nMIMIC tool not found. Use --use-simplified to run placeholder implementation.")
            print("Or specify MIMIC path with --mimic-path")
            sys.exit(1)
        
        # Run actual MIMIC
        success = run_mimic_tool(args.config, mimic_path, args.verbose)
    
    if success:
        print("\n✓ MIMIC execution complete!")
        print(f"  Check output directory: {output_dir}")
        sys.exit(0)
    else:
        print("\n✗ MIMIC execution failed")
        sys.exit(1)


if __name__ == '__main__':
    main()
