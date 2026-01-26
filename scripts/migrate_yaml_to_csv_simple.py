#!/usr/bin/python3

"""
Simplified Migration Script: YAML to CSV

Converts registers-sungrow.yaml to CSV format without requiring PyYAML dependency.
Uses a simple parser for the specific YAML structure.
"""

import csv
import json
import sys
import os
import re


def strip_inline_comment(value):
    """
    Strip inline YAML comments from a value.
    
    YAML allows inline comments starting with '#'. This function removes
    them from string values while preserving the actual content.
    
    Args:
        value: String value that may contain an inline comment
    
    Returns:
        str: Value with inline comment removed
    """
    if not value:
        return value
    # Remove inline comment (text after #) but be careful with quoted strings
    # If the value has a # character, split and take only the part before it
    if '#' in value:
        value = value.split('#')[0].strip()
    return value


def simple_yaml_parse(yaml_content):
    """
    Simple YAML parser for the specific structure of registers-sungrow.yaml.
    This is not a general-purpose YAML parser but works for this file format.
    """
    lines = yaml_content.split('\n')
    data = {
        'version': None,
        'vendor': None,
        'registers': [],
        'scan': []
    }
    
    current_reg_type = None
    current_register = None
    current_datarange = None
    current_scan_type = None
    current_scan_block = None
    in_scan = False
    in_registers = False
    indent_stack = []
    
    for line in lines:
        stripped = line.strip()
        
        # Skip empty lines and comments
        if not stripped or stripped.startswith('#'):
            continue
        
        # Get indentation level
        indent = len(line) - len(line.lstrip())
        
        # Top-level metadata
        if stripped.startswith('version:'):
            data['version'] = stripped.split(':', 1)[1].strip()
        elif stripped.startswith('vendor:'):
            data['vendor'] = stripped.split(':', 1)[1].strip()
        elif line.startswith('registers:') or stripped == 'registers:':
            in_scan = False
            in_registers = True
        elif line.startswith('scan:') or stripped == 'scan:':
            # Save last register before switching to scan mode
            if current_register is not None and current_reg_type and in_registers:
                data['registers'][-1][current_reg_type].append(current_register)
                current_register = None
            in_scan = True
            in_registers = False
        elif in_scan:
            # Parse scan section
            if stripped.startswith('- read:'):
                current_scan_type = 'read'
                current_scan_block = []
                data['scan'].append({'read': current_scan_block})
            elif stripped.startswith('- hold:'):
                current_scan_type = 'hold'
                current_scan_block = []
                data['scan'].append({'hold': current_scan_block})
            elif stripped.startswith('- start:'):
                # Extract value and remove inline comments
                val_str = stripped.split(':', 1)[1].strip()
                # Remove inline comments
                if '#' in val_str:
                    val_str = val_str.split('#')[0].strip()
                start_val = int(val_str)
                if current_scan_block is not None:
                    current_scan_block.append({'start': start_val})
            elif stripped.startswith('range:') and current_scan_block is not None:
                # Extract value and remove inline comments
                val_str = stripped.split(':', 1)[1].strip()
                # Remove inline comments
                if '#' in val_str:
                    val_str = val_str.split('#')[0].strip()
                range_val = int(val_str)
                if current_scan_block:
                    current_scan_block[-1]['range'] = range_val
        elif in_registers:
            # Parse registers section
            if stripped.startswith('- read:'):
                current_reg_type = 'read'
                data['registers'].append({'read': []})
            elif stripped.startswith('- hold:'):
                current_reg_type = 'hold'
                data['registers'].append({'hold': []})
            elif stripped.startswith('- name:'):
                # New register
                if current_register is not None and current_reg_type:
                    data['registers'][-1][current_reg_type].append(current_register)
                current_register = {}
                current_datarange = None
                name_val = strip_inline_comment(stripped.split(':', 1)[1].strip()).strip('"\'')
                current_register['name'] = name_val
            elif current_register is not None:
                if stripped.startswith('level:'):
                    val_str = strip_inline_comment(stripped.split(':', 1)[1].strip())
                    current_register['level'] = int(val_str)
                elif stripped.startswith('address:'):
                    val_str = strip_inline_comment(stripped.split(':', 1)[1].strip())
                    current_register['address'] = int(val_str)
                elif stripped.startswith('datatype:'):
                    current_register['datatype'] = strip_inline_comment(stripped.split(':', 1)[1].strip()).strip('"\'')
                elif stripped.startswith('accuracy:'):
                    val = strip_inline_comment(stripped.split(':', 1)[1].strip())
                    current_register['accuracy'] = float(val) if val else None
                elif stripped.startswith('unit:'):
                    current_register['unit'] = strip_inline_comment(stripped.split(':', 1)[1].strip()).strip('"\'')
                elif stripped.startswith('models:'):
                    # Parse list format: ["model1","model2"]
                    models_str = stripped.split(':', 1)[1].strip()
                    if models_str.startswith('['):
                        # Remove brackets and split
                        models_str = models_str.strip('[]')
                        models = [m.strip().strip('"\',') for m in models_str.split(',') if m.strip()]
                        current_register['models'] = models
                elif stripped.startswith('datarange:'):
                    current_datarange = []
                    current_register['datarange'] = current_datarange
                elif current_datarange is not None:
                    if stripped.startswith('- response:'):
                        # Parse response line
                        resp_val = stripped.split(':', 1)[1].strip()
                        # Convert hex values
                        if resp_val.startswith('0x'):
                            resp_val = int(resp_val, 16)
                        else:
                            resp_val = int(resp_val)
                        current_datarange.append({'response': resp_val})
                    elif stripped.startswith('value:'):
                        val = strip_inline_comment(stripped.split(':', 1)[1].strip()).strip('"\'')
                        if current_datarange:
                            current_datarange[-1]['value'] = val
                elif stripped.startswith('mask:'):
                    val_str = strip_inline_comment(stripped.split(':', 1)[1].strip())
                    current_register['mask'] = int(val_str)
                elif stripped.startswith('default:'):
                    current_register['default'] = strip_inline_comment(stripped.split(':', 1)[1].strip()).strip('"\'')
                elif stripped.startswith('smart_meter:'):
                    val = strip_inline_comment(stripped.split(':', 1)[1].strip()).lower()
                    current_register['smart_meter'] = (val == 'true')
    
    # Add last register if still in registers mode
    if current_register is not None and current_reg_type and in_registers:
        data['registers'][-1][current_reg_type].append(current_register)
    
    return data


def migrate(yaml_path, csv_path, scan_yaml_path):
    """Migrate from YAML register file to CSV + scan-ranges YAML."""
    print(f"Loading YAML from: {yaml_path}")
    
    try:
        with open(yaml_path, encoding="utf-8") as f:
            yaml_content = f.read()
    except Exception as err:
        print(f"Error loading YAML: {err}")
        sys.exit(1)
    
    # Parse YAML
    data = simple_yaml_parse(yaml_content)
    
    # Write CSV file
    print(f"Writing CSV to: {csv_path}")
    try:
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            fieldnames = [
                "type", "name", "level", "address", "datatype",
                "accuracy", "unit", "models", "datarange",
                "mask", "default", "smart_meter"
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            read_count = 0
            hold_count = 0
            
            for reg_block in data.get("registers", []):
                for reg_type in ["read", "hold"]:
                    if reg_type in reg_block:
                        for reg in reg_block[reg_type]:
                            row = convert_register_to_row(reg_type, reg)
                            writer.writerow(row)
                            
                            if reg_type == "read":
                                read_count += 1
                            else:
                                hold_count += 1
            
            print(f"  Wrote {read_count} read registers and {hold_count} hold registers")
    except Exception as err:
        print(f"Error writing CSV: {err}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Write scan ranges YAML
    print(f"Writing scan ranges to: {scan_yaml_path}")
    try:
        with open(scan_yaml_path, "w", encoding="utf-8") as f:
            f.write(f"version: {data.get('version')}\n")
            f.write(f"vendor: {data.get('vendor')}\n")
            f.write("scan:\n")
            for scan_block in data.get('scan', []):
                for scan_type in ['read', 'hold']:
                    if scan_type in scan_block:
                        f.write(f"  - {scan_type}:\n")
                        for range_item in scan_block[scan_type]:
                            f.write(f"    - start: {range_item['start']}\n")
                            f.write(f"      range: {range_item['range']}\n")
        
        print(f"  Version: {data.get('version')}")
        print(f"  Vendor: {data.get('vendor')}")
    except Exception as err:
        print(f"Error writing scan ranges YAML: {err}")
        sys.exit(1)
    
    print("\nMigration completed successfully!")


def convert_register_to_row(reg_type, reg):
    """Convert a register dictionary to a CSV row."""
    row = {
        "type": reg_type,
        "name": reg.get("name", ""),
        "level": reg.get("level", ""),
        "address": reg.get("address", ""),
        "datatype": reg.get("datatype", ""),
        "accuracy": "",
        "unit": "",
        "models": "",
        "datarange": "",
        "mask": "",
        "default": "",
        "smart_meter": ""
    }
    
    if "accuracy" in reg and reg["accuracy"] is not None:
        row["accuracy"] = reg["accuracy"]
    
    if "unit" in reg:
        row["unit"] = reg["unit"]
    
    if "models" in reg:
        row["models"] = "|".join(reg["models"])
    
    if "datarange" in reg:
        row["datarange"] = json.dumps(reg["datarange"], ensure_ascii=False)
    
    if "mask" in reg:
        row["mask"] = reg["mask"]
    
    if "default" in reg:
        row["default"] = reg["default"]
    
    if "smart_meter" in reg and reg["smart_meter"]:
        row["smart_meter"] = "true"
    
    return row


def main():
    """Main entry point for the migration script."""
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    sungather_dir = os.path.join(project_root, "SunGather")
    
    yaml_path = os.path.join(sungather_dir, "registers-sungrow.yaml")
    csv_path = os.path.join(sungather_dir, "registers-sungrow.csv")
    scan_yaml_path = os.path.join(sungather_dir, "scan-ranges.yaml")
    
    if len(sys.argv) > 1:
        yaml_path = sys.argv[1]
    if len(sys.argv) > 2:
        csv_path = sys.argv[2]
    if len(sys.argv) > 3:
        scan_yaml_path = sys.argv[3]
    
    print("YAML to CSV Migration Script")
    print("=" * 50)
    print(f"Input:  {yaml_path}")
    print(f"Output: {csv_path}")
    print(f"Output: {scan_yaml_path}")
    print("=" * 50)
    print()
    
    if not os.path.exists(yaml_path):
        print(f"Error: Input file not found: {yaml_path}")
        sys.exit(1)
    
    migrate(yaml_path, csv_path, scan_yaml_path)


if __name__ == "__main__":
    main()
