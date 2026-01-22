#!/usr/bin/env python3
"""
Trojan Verification Script
Verifies that Trojans were successfully inserted into netlists
"""

import argparse
import json
import re
from pathlib import Path
from collections import Counter


def verify_single_netlist(netlist_file):
    """Verify a single netlist for Trojan presence"""
    
    with open(netlist_file, 'r') as f:
        content = f.read()
    
    # Check for Trojan markers
    has_start_marker = '=== INSERTED TROJAN START ===' in content
    has_end_marker = '=== INSERTED TROJAN END ===' in content
    
    # Count Trojan markers
    num_trojans = content.count('=== INSERTED TROJAN START ===')
    
    # Extract Trojan info
    trojans_found = []
    
    # Pattern to extract trigger and payload types
    pattern = r'// Trigger: (\w+), Payload: (\w+)'
    matches = re.findall(pattern, content)
    
    for trigger, payload in matches:
        trojans_found.append({
            'trigger_type': trigger,
            'payload_type': payload
        })
    
    # Count lines and gates
    lines = content.split('\n')
    total_lines = len(lines)
    
    # Estimate additional gates (rough count)
    trojan_section = False
    trojan_lines = 0
    for line in lines:
        if '=== INSERTED TROJAN START ===' in line:
            trojan_section = True
        elif '=== INSERTED TROJAN END ===' in line:
            trojan_section = False
        elif trojan_section:
            trojan_lines += 1
    
    return {
        'file': netlist_file.name,
        'has_trojan': has_start_marker and has_end_marker,
        'num_trojans': num_trojans,
        'trojans': trojans_found,
        'total_lines': total_lines,
        'trojan_lines': trojan_lines,
        'trojan_percentage': (trojan_lines / total_lines * 100) if total_lines > 0 else 0
    }


def verify_directory(directory):
    """Verify all netlists in a directory"""
    
    dir_path = Path(directory)
    
    if not dir_path.exists():
        print(f"Error: Directory not found: {directory}")
        return None
    
    # Find all .v files
    netlist_files = list(dir_path.glob('*.v'))
    
    if not netlist_files:
        print(f"No .v files found in {directory}")
        return None
    
    results = []
    for netlist_file in netlist_files:
        result = verify_single_netlist(netlist_file)
        results.append(result)
    
    return results


def analyze_metadata(metadata_file):
    """Analyze insertion metadata"""
    
    if not Path(metadata_file).exists():
        return None
    
    with open(metadata_file, 'r') as f:
        metadata = json.load(f)
    
    # Extract statistics
    stats = {
        'total_trojans': metadata.get('num_trojans', 0),
        'trigger_types': Counter(),
        'payload_types': Counter(),
        'gate_sizes': [],
        'files': []
    }
    
    for insertion in metadata.get('insertions', []):
        stats['trigger_types'][insertion['trigger_type']] += 1
        stats['payload_types'][insertion['payload_type']] += 1
        stats['gate_sizes'].append(insertion.get('estimated_gates', 0))
        stats['files'].append(insertion['output_file'])
    
    if stats['gate_sizes']:
        stats['avg_gate_size'] = sum(stats['gate_sizes']) / len(stats['gate_sizes'])
        stats['min_gate_size'] = min(stats['gate_sizes'])
        stats['max_gate_size'] = max(stats['gate_sizes'])
    
    return stats


def print_report(results, metadata_stats=None):
    """Print verification report"""
    
    print("="*70)
    print("TROJAN VERIFICATION REPORT")
    print("="*70)
    
    # Overall statistics
    total_files = len(results)
    files_with_trojans = sum(1 for r in results if r['has_trojan'])
    total_trojans = sum(r['num_trojans'] for r in results)
    
    print(f"\nOverall:")
    print(f"  Total files checked: {total_files}")
    print(f"  Files with Trojans: {files_with_trojans}")
    print(f"  Total Trojans found: {total_trojans}")
    print(f"  Success rate: {files_with_trojans/total_files*100:.1f}%")
    
    # Per-file details
    print(f"\nPer-File Details:")
    for r in results:
        status = "✓" if r['has_trojan'] else "✗"
        print(f"\n  {status} {r['file']}")
        print(f"      Trojans: {r['num_trojans']}")
        print(f"      Total lines: {r['total_lines']}")
        print(f"      Trojan lines: {r['trojan_lines']} ({r['trojan_percentage']:.1f}%)")
        
        if r['trojans']:
            print(f"      Types:")
            for t in r['trojans']:
                print(f"        - {t['trigger_type']} trigger, {t['payload_type']} payload")
    
    # Metadata analysis
    if metadata_stats:
        print(f"\n" + "="*70)
        print("METADATA ANALYSIS")
        print("="*70)
        
        print(f"\nTotal Trojans (from metadata): {metadata_stats['total_trojans']}")
        
        print(f"\nTrigger Type Distribution:")
        for trigger, count in metadata_stats['trigger_types'].items():
            pct = count / metadata_stats['total_trojans'] * 100
            print(f"  {trigger:15s}: {count:3d} ({pct:5.1f}%)")
        
        print(f"\nPayload Type Distribution:")
        for payload, count in metadata_stats['payload_types'].items():
            pct = count / metadata_stats['total_trojans'] * 100
            print(f"  {payload:15s}: {count:3d} ({pct:5.1f}%)")
        
        if 'avg_gate_size' in metadata_stats:
            print(f"\nGate Size Statistics:")
            print(f"  Average: {metadata_stats['avg_gate_size']:.1f} gates")
            print(f"  Range: {metadata_stats['min_gate_size']}-{metadata_stats['max_gate_size']} gates")
    
    print("\n" + "="*70)


def check_design_size(netlist_file):
    """Check the size of a design (number of nets, gates, etc.)"""
    
    print(f"\nAnalyzing design size: {netlist_file}")
    
    with open(netlist_file, 'r') as f:
        content = f.read()
    
    lines = content.split('\n')
    
    # Count various elements
    stats = {
        'total_lines': len(lines),
        'modules': content.count('module '),
        'inputs': content.count('input '),
        'outputs': content.count('output '),
        'wires': content.count('wire '),
        'regs': content.count('reg '),
        'assigns': content.count('assign '),
        'always_blocks': content.count('always '),
    }
    
    # Estimate gates (very rough)
    # Count gate instantiations (lines with parentheses that aren't module definitions)
    gate_estimate = 0
    for line in lines:
        line = line.strip()
        if line and '(' in line and ')' in line:
            if not line.startswith('//') and not line.startswith('module'):
                if not line.startswith('input') and not line.startswith('output'):
                    if not line.startswith('wire') and not line.startswith('reg'):
                        gate_estimate += 1
    
    stats['estimated_gates'] = gate_estimate
    
    # Estimate nets (wires + inputs + outputs + regs)
    stats['estimated_nets'] = stats['wires'] + stats['inputs'] + stats['outputs'] + stats['regs']
    
    print(f"\nDesign Statistics:")
    print(f"  Total lines: {stats['total_lines']:,}")
    print(f"  Modules: {stats['modules']}")
    print(f"  Inputs: {stats['inputs']}")
    print(f"  Outputs: {stats['outputs']}")
    print(f"  Wires: {stats['wires']:,}")
    print(f"  Registers: {stats['regs']:,}")
    print(f"  Estimated nets: {stats['estimated_nets']:,}")
    print(f"  Assign statements: {stats['assigns']:,}")
    print(f"  Always blocks: {stats['always_blocks']:,}")
    print(f"  Estimated gates: {stats['estimated_gates']:,}")
    
    # Size classification
    if stats['estimated_nets'] < 1000:
        size_class = "SMALL"
    elif stats['estimated_nets'] < 10000:
        size_class = "MEDIUM"
    elif stats['estimated_nets'] < 100000:
        size_class = "LARGE"
    else:
        size_class = "VERY LARGE"
    
    print(f"\n  Size Classification: {size_class}")
    
    if stats['estimated_nets'] > 100000:
        print("\n  ⚠️  WARNING: Very large design!")
        print("     - Feature extraction may take several minutes")
        print("     - Consider using --num-trojans < 100 initially")
        print("     - May need 16GB+ RAM")
    
    return stats


def main():
    parser = argparse.ArgumentParser(
        description='Verify Trojan insertion in netlists',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        '--directory',
        help='Directory with Trojaned netlists'
    )
    
    parser.add_argument(
        '--netlist',
        help='Single netlist file to check'
    )
    
    parser.add_argument(
        '--metadata',
        help='Metadata JSON file to analyze'
    )
    
    parser.add_argument(
        '--check-size',
        help='Check design size of a netlist'
    )
    
    args = parser.parse_args()
    
    if args.check_size:
        check_design_size(args.check_size)
        return 0
    
    if args.directory:
        # Verify directory
        results = verify_directory(args.directory)
        
        if not results:
            return 1
        
        # Look for metadata in the directory
        metadata_file = Path(args.directory) / 'insertion_metadata.json'
        metadata_stats = None
        
        if metadata_file.exists():
            metadata_stats = analyze_metadata(metadata_file)
        elif args.metadata:
            metadata_stats = analyze_metadata(args.metadata)
        
        print_report(results, metadata_stats)
    
    elif args.netlist:
        # Verify single file
        result = verify_single_netlist(Path(args.netlist))
        print_report([result])
    
    else:
        print("Error: Must specify --directory, --netlist, or --check-size")
        return 1
    
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
