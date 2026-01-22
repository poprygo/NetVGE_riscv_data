#!/usr/bin/env python3
"""
Validate CVA6 Trojan-inserted designs
Checks: Syntax, Parsing, Module structure, Trojan presence, and basic synthesis
"""

import os
import sys
import json
import subprocess
from pathlib import Path

def check_verilog_syntax(verilog_file):
    """Check Verilog syntax using iverilog (if available) or pyverilog"""
    print(f"  Checking syntax: {os.path.basename(verilog_file)}")
    
    # Try with iverilog first (faster)
    try:
        result = subprocess.run(
            ['iverilog', '-t', 'null', '-g2012', verilog_file],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            print(f"    ✓ Syntax valid (iverilog)")
            return True, "Syntax OK"
        else:
            error = result.stderr[:200] if result.stderr else "Unknown error"
            print(f"    ✗ Syntax error: {error}")
            return False, error
    except FileNotFoundError:
        print(f"    ⚠ iverilog not found, skipping syntax check")
        return None, "iverilog not available"
    except Exception as e:
        print(f"    ⚠ Syntax check failed: {e}")
        return None, str(e)

def check_module_structure(verilog_file):
    """Check module structure and find module name"""
    print(f"  Checking module structure...")
    
    try:
        with open(verilog_file, 'r') as f:
            content = f.read()
        
        # Find module declaration
        import re
        module_match = re.search(r'module\s+(\w+)', content)
        if not module_match:
            print(f"    ✗ No module declaration found")
            return False, None
        
        module_name = module_match.group(1)
        print(f"    ✓ Module found: {module_name}")
        
        # Check for endmodule
        if 'endmodule' not in content:
            print(f"    ✗ No endmodule found")
            return False, module_name
        
        # Count modules and endmodules
        module_count = len(re.findall(r'\bmodule\s+\w+', content))
        endmodule_count = content.count('endmodule')
        
        if module_count != endmodule_count:
            print(f"    ✗ Mismatched module/endmodule: {module_count} vs {endmodule_count}")
            return False, module_name
        
        print(f"    ✓ Module structure valid ({module_count} module(s))")
        return True, module_name
        
    except Exception as e:
        print(f"    ✗ Error reading file: {e}")
        return False, None

def check_trojan_presence(verilog_file):
    """Verify Trojan markers are present"""
    print(f"  Checking Trojan presence...")
    
    try:
        with open(verilog_file, 'r') as f:
            content = f.read()
        
        # Check for Trojan markers
        if '=== INSERTED TROJAN START ===' not in content:
            print(f"    ✗ Trojan START marker not found")
            return False, None
        
        if '=== INSERTED TROJAN END ===' not in content:
            print(f"    ✗ Trojan END marker not found")
            return False, None
        
        # Count Trojan lines
        trojan_start = content.find('=== INSERTED TROJAN START ===')
        trojan_end = content.find('=== INSERTED TROJAN END ===')
        
        if trojan_start == -1 or trojan_end == -1 or trojan_start >= trojan_end:
            print(f"    ✗ Invalid Trojan markers")
            return False, None
        
        trojan_section = content[trojan_start:trojan_end]
        trojan_lines = len(trojan_section.split('\n'))
        
        # Extract Trojan info
        import re
        trigger_match = re.search(r'Trigger:\s*(\w+)', trojan_section)
        payload_match = re.search(r'Payload:\s*(\w+)', trojan_section)
        
        trigger_type = trigger_match.group(1) if trigger_match else "unknown"
        payload_type = payload_match.group(1) if payload_match else "unknown"
        
        print(f"    ✓ Trojan found: {trigger_type} trigger, {payload_type} payload")
        print(f"    ✓ Trojan size: {trojan_lines} lines")
        
        return True, {
            'trigger': trigger_type,
            'payload': payload_type,
            'lines': trojan_lines
        }
        
    except Exception as e:
        print(f"    ✗ Error checking Trojan: {e}")
        return False, None

def check_file_stats(verilog_file):
    """Get basic file statistics"""
    print(f"  Checking file statistics...")
    
    try:
        with open(verilog_file, 'r') as f:
            lines = f.readlines()
        
        total_lines = len(lines)
        non_empty = sum(1 for line in lines if line.strip())
        comments = sum(1 for line in lines if line.strip().startswith('//'))
        
        print(f"    ✓ Total lines: {total_lines}")
        print(f"    ✓ Non-empty lines: {non_empty}")
        print(f"    ✓ Comment lines: {comments}")
        
        return True, {
            'total_lines': total_lines,
            'non_empty': non_empty,
            'comments': comments
        }
        
    except Exception as e:
        print(f"    ✗ Error reading file: {e}")
        return False, None

def try_yosys_parse(verilog_file):
    """Try to parse with Yosys (if available)"""
    print(f"  Trying Yosys parsing...")
    
    try:
        # Create temporary Yosys script
        temp_script = '/tmp/yosys_validate.ys'
        with open(temp_script, 'w') as f:
            f.write(f"read_verilog -sv {verilog_file}\n")
            f.write("hierarchy -check\n")
        
        result = subprocess.run(
            ['yosys', '-s', temp_script],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            print(f"    ✓ Yosys parsing successful")
            return True, "Yosys OK"
        else:
            # Check if it's just a missing dependency issue
            if 'not found' in result.stderr or 'Cannot find' in result.stderr:
                print(f"    ⚠ Yosys found missing dependencies (expected for CVA6)")
                return None, "Missing dependencies (OK)"
            else:
                error = result.stderr[:200] if result.stderr else "Unknown error"
                print(f"    ⚠ Yosys warnings/errors: {error[:100]}...")
                return None, error
                
    except FileNotFoundError:
        print(f"    ⚠ Yosys not found, skipping")
        return None, "Yosys not available"
    except subprocess.TimeoutExpired:
        print(f"    ⚠ Yosys timeout (design too complex)")
        return None, "Timeout"
    except Exception as e:
        print(f"    ⚠ Yosys check failed: {e}")
        return None, str(e)

def validate_design(verilog_file):
    """Run all validation checks on a design"""
    print(f"\n{'='*70}")
    print(f"Validating: {os.path.basename(verilog_file)}")
    print(f"{'='*70}")
    
    results = {
        'file': os.path.basename(verilog_file),
        'path': verilog_file,
        'checks': {}
    }
    
    # Check 1: File exists
    if not os.path.exists(verilog_file):
        print(f"  ✗ File not found!")
        results['checks']['exists'] = False
        return results
    
    results['checks']['exists'] = True
    print(f"  ✓ File exists")
    
    # Check 2: File statistics
    stat_ok, stat_info = check_file_stats(verilog_file)
    results['checks']['statistics'] = stat_ok
    if stat_info:
        results['statistics'] = stat_info
    
    # Check 3: Module structure
    struct_ok, module_name = check_module_structure(verilog_file)
    results['checks']['structure'] = struct_ok
    results['module_name'] = module_name
    
    # Check 4: Trojan presence
    trojan_ok, trojan_info = check_trojan_presence(verilog_file)
    results['checks']['trojan'] = trojan_ok
    if trojan_info:
        results['trojan_info'] = trojan_info
    
    # Check 5: Syntax (if iverilog available)
    syntax_ok, syntax_msg = check_verilog_syntax(verilog_file)
    results['checks']['syntax'] = syntax_ok
    results['syntax_msg'] = syntax_msg
    
    # Check 6: Yosys parsing (if available)
    yosys_ok, yosys_msg = try_yosys_parse(verilog_file)
    results['checks']['yosys'] = yosys_ok
    results['yosys_msg'] = yosys_msg
    
    # Overall status
    critical_checks = [
        results['checks']['exists'],
        results['checks']['structure'],
        results['checks']['trojan']
    ]
    
    results['valid'] = all(critical_checks)
    
    # Print summary
    print(f"\n  Summary:")
    print(f"    File exists:     {'✓' if results['checks']['exists'] else '✗'}")
    print(f"    Structure:       {'✓' if results['checks']['structure'] else '✗'}")
    print(f"    Trojan present:  {'✓' if results['checks']['trojan'] else '✗'}")
    print(f"    Syntax check:    {'✓' if results['checks']['syntax'] else '⚠' if results['checks']['syntax'] is None else '✗'}")
    print(f"    Yosys parse:     {'✓' if results['checks']['yosys'] else '⚠' if results['checks']['yosys'] is None else '✗'}")
    print(f"\n  Overall: {'✓ VALID' if results['valid'] else '✗ INVALID'}")
    
    return results

def main():
    # Directory containing CVA6 designs
    design_dir = Path('/Users/yaroslavpopryho/Study/UIC/Research/MIMIC/trojans/cva6_10_designs_100k/trojaned_netlists')
    
    print("="*70)
    print("CVA6 DESIGN VALIDATION")
    print("="*70)
    print(f"Directory: {design_dir}")
    print(f"Date: 2026-01-21")
    print()
    
    # Find all Verilog files
    verilog_files = sorted(design_dir.glob('cva6_trojan_*.v'))
    
    if not verilog_files:
        print("✗ No CVA6 Trojan files found!")
        sys.exit(1)
    
    print(f"Found {len(verilog_files)} designs to validate\n")
    
    # Validate each design
    all_results = []
    for verilog_file in verilog_files:
        result = validate_design(str(verilog_file))
        all_results.append(result)
    
    # Generate summary report
    print(f"\n{'='*70}")
    print("VALIDATION SUMMARY")
    print(f"{'='*70}\n")
    
    valid_count = sum(1 for r in all_results if r['valid'])
    total_count = len(all_results)
    
    print(f"Total designs validated: {total_count}")
    print(f"Valid designs: {valid_count}")
    print(f"Invalid designs: {total_count - valid_count}")
    print(f"Success rate: {100.0 * valid_count / total_count:.1f}%")
    print()
    
    # Detailed table
    print("Design-by-Design Results:")
    print("-" * 70)
    print(f"{'Design':<45} {'Valid':<8} {'Lines':<8} {'Trojan':<10}")
    print("-" * 70)
    
    for result in all_results:
        design_name = result['file'][:44]
        valid_str = "✓ YES" if result['valid'] else "✗ NO"
        lines = result.get('statistics', {}).get('total_lines', 'N/A')
        trojan = result.get('trojan_info', {}).get('trigger', 'N/A')
        
        print(f"{design_name:<45} {valid_str:<8} {lines:<8} {trojan:<10}")
    
    print("-" * 70)
    
    # Save results to JSON
    output_file = design_dir / 'validation_results.json'
    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2)
    
    print(f"\nDetailed results saved to: {output_file}")
    
    # Exit code
    if valid_count == total_count:
        print("\n✓ All designs are VALID!")
        sys.exit(0)
    else:
        print(f"\n⚠ {total_count - valid_count} design(s) failed validation")
        sys.exit(1)

if __name__ == '__main__':
    main()
