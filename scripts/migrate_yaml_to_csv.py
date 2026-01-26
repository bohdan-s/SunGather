#!/usr/bin/python3

"""
Migration Script: YAML to CSV

Converts the existing registers-sungrow.yaml file to the new CSV format
and creates a separate scan-ranges.yaml file.
"""

import yaml
import csv
import json
import sys
import os


def strip_inline_comment(value):
    """
    Strip inline YAML comments from a value.
    
    YAML allows inline comments starting with '#'. This function removes
    them from string values while preserving the actual content.
    
    Args:
        value: String value that may contain an inline comment
    
    Returns:
        str: Value with inline comment removed, or original value if not a string
    """
    if not isinstance(value, str):
        return value
    if not value:
        return value
    # Remove inline comment (text after #)
    if '#' in value:
        value = value.split('#')[0].strip()
    return value


def migrate(yaml_path, csv_path, scan_yaml_path):
    """
    Migrate from YAML register file to CSV + scan-ranges YAML.
    
    Args:
        yaml_path: Path to input YAML file
        csv_path: Path to output CSV file
        scan_yaml_path: Path to output scan-ranges YAML file
    """
    print(f"Loading YAML from: {yaml_path}")
    
    # Load the YAML file
    try:
        with open(yaml_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception as err:
        print(f"Error loading YAML: {err}")
        sys.exit(1)
    
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
            
            # Process all registers
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
        sys.exit(1)
    
    # Write scan ranges YAML
    print(f"Writing scan ranges to: {scan_yaml_path}")
    try:
        scan_data = {
            "version": data.get("version"),
            "vendor": data.get("vendor"),
            "scan": data.get("scan")
        }
        
        with open(scan_yaml_path, "w", encoding="utf-8") as f:
            yaml.dump(scan_data, f, default_flow_style=False, allow_unicode=True)
        
        print(f"  Version: {scan_data.get('version')}")
        print(f"  Vendor: {scan_data.get('vendor')}")
    except Exception as err:
        print(f"Error writing scan ranges YAML: {err}")
        sys.exit(1)
    
    print("\nMigration completed successfully!")


def convert_register_to_row(reg_type, reg):
    """
    Convert a register dictionary to a CSV row.
    
    Args:
        reg_type: "read" or "hold"
        reg: Register dictionary from YAML
    
    Returns:
        dict: CSV row dictionary
    """
    # Strip inline comments from string fields
    name = strip_inline_comment(reg.get("name", ""))
    datatype = strip_inline_comment(reg.get("datatype", ""))
    unit = strip_inline_comment(reg.get("unit", "")) if "unit" in reg else ""
    default = strip_inline_comment(reg.get("default", "")) if "default" in reg else ""
    
    row = {
        "type": reg_type,
        "name": name,
        "level": reg.get("level", ""),
        "address": reg.get("address", ""),
        "datatype": datatype,
        "accuracy": "",
        "unit": unit,
        "models": "",
        "datarange": "",
        "mask": "",
        "default": default,
        "smart_meter": ""
    }
    
    # Optional fields
    if "accuracy" in reg:
        row["accuracy"] = reg["accuracy"]
    
    if "models" in reg:
        # Convert list to pipe-delimited string
        row["models"] = "|".join(reg["models"])
    
    if "datarange" in reg:
        # Convert datarange to JSON string
        # Need to ensure proper formatting for CSV
        row["datarange"] = json.dumps(reg["datarange"], ensure_ascii=False)
    
    if "mask" in reg:
        row["mask"] = reg["mask"]
    
    if "smart_meter" in reg and reg["smart_meter"]:
        row["smart_meter"] = "true"
    
    return row


def main():
    """Main entry point for the migration script."""
    
    # Default paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    sungather_dir = os.path.join(project_root, "SunGather")
    
    yaml_path = os.path.join(sungather_dir, "registers-sungrow.yaml")
    csv_path = os.path.join(sungather_dir, "registers-sungrow.csv")
    scan_yaml_path = os.path.join(sungather_dir, "scan-ranges.yaml")
    
    # Allow command-line arguments to override
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
    
    # Check if input file exists
    if not os.path.exists(yaml_path):
        print(f"Error: Input file not found: {yaml_path}")
        sys.exit(1)
    
    # Run migration
    migrate(yaml_path, csv_path, scan_yaml_path)


if __name__ == "__main__":
    main()
