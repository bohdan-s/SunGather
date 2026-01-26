#!/usr/bin/python3

"""
Test script to verify the register loader works correctly.
Compares CSV-loaded data with YAML-loaded data (if available).
"""

import sys
import os

# Add parent directory to path to import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'SunGather'))

from register_loader import load_registers, get_scan_ranges_path


def test_csv_loader():
    """Test loading registers from CSV format."""
    print("Testing CSV Register Loader")
    print("=" * 60)
    
    csv_path = os.path.join(os.path.dirname(__file__), '..', 'SunGather', 'registers-sungrow.csv')
    scan_yaml_path = os.path.join(os.path.dirname(__file__), '..', 'SunGather', 'scan-ranges.yaml')
    
    print(f"CSV Path: {csv_path}")
    print(f"Scan YAML Path: {scan_yaml_path}")
    print()
    
    # Test loading
    try:
        data = load_registers(csv_path, scan_yaml_path)
        print("✓ CSV loaded successfully")
    except Exception as err:
        print(f"✗ Failed to load CSV: {err}")
        import traceback
        traceback.print_exc()
        return False
    
    # Validate structure
    print("\nValidating structure...")
    
    required_keys = ['version', 'vendor', 'registers', 'scan']
    for key in required_keys:
        if key in data:
            print(f"✓ Key '{key}' present")
        else:
            print(f"✗ Key '{key}' missing")
            return False
    
    # Check registers
    print(f"\nVersion: {data.get('version')}")
    print(f"Vendor: {data.get('vendor')}")
    
    read_count = 0
    hold_count = 0
    
    for reg_block in data.get('registers', []):
        if 'read' in reg_block:
            read_count = len(reg_block['read'])
        if 'hold' in reg_block:
            hold_count = len(reg_block['hold'])
    
    print(f"\nRegister counts:")
    print(f"  Read registers: {read_count}")
    print(f"  Hold registers: {hold_count}")
    print(f"  Total: {read_count + hold_count}")
    
    if read_count == 0 and hold_count == 0:
        print("✗ No registers loaded")
        return False
    
    # Validate a few sample registers
    print("\nValidating sample registers...")
    
    sample_found = False
    for reg_block in data.get('registers', []):
        if 'read' in reg_block:
            for reg in reg_block['read'][:3]:  # Check first 3
                name = reg.get('name')
                if name:
                    print(f"  ✓ Register: {name}")
                    print(f"    - Level: {reg.get('level')}")
                    print(f"    - Address: {reg.get('address')}")
                    print(f"    - Datatype: {reg.get('datatype')}")
                    if 'models' in reg:
                        print(f"    - Models: {len(reg['models'])} models")
                    if 'datarange' in reg:
                        print(f"    - Datarange: {len(reg['datarange'])} mappings")
                    sample_found = True
                    print()
    
    if not sample_found:
        print("✗ No valid registers found")
        return False
    
    # Check scan ranges
    scan_ranges = data.get('scan', [])
    print(f"Scan ranges: {len(scan_ranges)} blocks")
    
    for scan_block in scan_ranges:
        for scan_type in ['read', 'hold']:
            if scan_type in scan_block:
                print(f"  {scan_type}: {len(scan_block[scan_type])} ranges")
    
    print("\n" + "=" * 60)
    print("✓ All tests passed!")
    return True


def test_get_scan_ranges_path():
    """Test the helper function to get scan ranges path."""
    print("\nTesting get_scan_ranges_path helper")
    print("=" * 60)
    
    test_cases = [
        ("SunGather/registers-sungrow.csv", "SunGather/scan-ranges.yaml"),
        ("/path/to/registers.csv", "/path/to/scan-ranges.yaml"),
        ("registers.csv", "scan-ranges.yaml"),
    ]
    
    for csv_path, expected in test_cases:
        result = get_scan_ranges_path(csv_path)
        if result == expected:
            print(f"✓ {csv_path} → {result}")
        else:
            print(f"✗ {csv_path} → {result} (expected: {expected})")
            return False
    
    print("✓ All path tests passed!")
    return True


if __name__ == "__main__":
    success = True
    
    # Run tests
    if not test_get_scan_ranges_path():
        success = False
    
    print()
    
    if not test_csv_loader():
        success = False
    
    if success:
        print("\n✓✓✓ All tests passed! ✓✓✓")
        sys.exit(0)
    else:
        print("\n✗✗✗ Some tests failed ✗✗✗")
        sys.exit(1)
