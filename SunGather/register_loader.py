#!/usr/bin/python3

"""
Register Loader Module

Loads register definitions from CSV format and scan ranges from YAML,
combining them into the structure expected by SungrowClient.
"""

import csv
import json
import logging
import os

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


def strip_inline_comment(value):
    """
    Strip inline YAML comments from a value.
    
    YAML allows inline comments starting with '#'. This function removes
    them from string values while preserving the actual content. This is
    useful for robustness when loading data that may have residual comments.
    
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


def simple_yaml_parse_scan_ranges(yaml_content):
    """
    Simple YAML parser for scan-ranges.yaml file.
    Only used when PyYAML is not available.
    """
    lines = yaml_content.split('\n')
    data = {
        'version': None,
        'vendor': None,
        'scan': []
    }
    
    current_scan_type = None
    current_scan_block = None
    
    for line in lines:
        stripped = line.strip()
        
        # Skip empty lines and comments
        if not stripped or stripped.startswith('#'):
            continue
        
        if stripped.startswith('version:'):
            data['version'] = stripped.split(':', 1)[1].strip()
        elif stripped.startswith('vendor:'):
            data['vendor'] = stripped.split(':', 1)[1].strip()
        elif stripped == 'scan:':
            continue
        elif stripped.startswith('- read:'):
            current_scan_type = 'read'
            current_scan_block = []
            data['scan'].append({'read': current_scan_block})
        elif stripped.startswith('- hold:'):
            current_scan_type = 'hold'
            current_scan_block = []
            data['scan'].append({'hold': current_scan_block})
        elif stripped.startswith('- start:'):
            val_str = strip_inline_comment(stripped.split(':', 1)[1].strip())
            start_val = int(val_str)
            if current_scan_block is not None:
                current_scan_block.append({'start': start_val})
        elif stripped.startswith('range:') and current_scan_block is not None:
            val_str = strip_inline_comment(stripped.split(':', 1)[1].strip())
            range_val = int(val_str)
            if current_scan_block:
                current_scan_block[-1]['range'] = range_val
    
    return data


def load_registers(csv_path, scan_yaml_path):
    """
    Load registers from CSV and scan ranges from YAML.
    
    Args:
        csv_path: Path to the CSV file containing register definitions
        scan_yaml_path: Path to the YAML file containing scan ranges
    
    Returns:
        dict: Combined structure matching original YAML format
    """
    logging.info(f"Loading registers from CSV: {csv_path}")
    
    registers = {"read": [], "hold": []}
    
    # Read CSV file
    try:
        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                register = parse_register_row(row)
                reg_type = row["type"]
                if reg_type in registers:
                    registers[reg_type].append(register)
                else:
                    logging.warning(f"Unknown register type: {reg_type} for register {row.get('name')}")
    except Exception as err:
        raise Exception(f"Failed to load CSV file {csv_path}: {err}")
    
    # Load scan ranges from YAML
    try:
        with open(scan_yaml_path, encoding="utf-8") as f:
            if YAML_AVAILABLE:
                scan_data = yaml.safe_load(f)
            else:
                # Use simple parser when PyYAML is not available
                scan_data = simple_yaml_parse_scan_ranges(f.read())
    except Exception as err:
        raise Exception(f"Failed to load scan ranges YAML {scan_yaml_path}: {err}")
    
    # Build final structure matching original YAML format
    result = {
        "version": scan_data.get("version"),
        "vendor": scan_data.get("vendor"),
        "registers": [
            {"read": registers["read"]},
            {"hold": registers["hold"]}
        ],
        "scan": scan_data.get("scan")
    }
    
    logging.info(f"Loaded {len(registers['read'])} read registers and {len(registers['hold'])} hold registers")
    
    return result


def parse_register_row(row):
    """
    Convert CSV row to register dictionary.
    
    Args:
        row: Dictionary representing one CSV row
    
    Returns:
        dict: Register definition
    """
    # Required fields - strip any residual inline comments for robustness
    register = {
        "name": strip_inline_comment(row["name"]),
        "level": int(strip_inline_comment(row["level"])),
        "address": int(strip_inline_comment(row["address"])),
        "datatype": strip_inline_comment(row["datatype"])
    }
    
    # Optional fields - only add if present and not empty
    if row.get("accuracy") and row["accuracy"].strip():
        register["accuracy"] = float(row["accuracy"])
    
    if row.get("unit") and row["unit"].strip():
        register["unit"] = strip_inline_comment(row["unit"])
    
    if row.get("models") and row["models"].strip():
        # Models are pipe-delimited in CSV
        register["models"] = [m.strip() for m in row["models"].split("|") if m.strip()]
    
    if row.get("datarange") and row["datarange"].strip():
        # Datarange is stored as JSON string in CSV
        try:
            register["datarange"] = json.loads(row["datarange"])
        except json.JSONDecodeError as err:
            logging.warning(f"Failed to parse datarange JSON for {row['name']}: {err}")
    
    if row.get("mask") and row["mask"].strip():
        register["mask"] = int(row["mask"])
    
    if row.get("default") and row["default"].strip():
        register["default"] = strip_inline_comment(row["default"])
    
    if row.get("smart_meter") and row["smart_meter"].strip():
        # Only set if explicitly true
        if row["smart_meter"].lower() == "true":
            register["smart_meter"] = True
    
    return register


def get_scan_ranges_path(csv_path):
    """
    Get the corresponding scan-ranges.yaml path for a given CSV path.
    
    Args:
        csv_path: Path to the CSV file
    
    Returns:
        str: Path to the scan-ranges.yaml file
    """
    # Replace filename with scan-ranges.yaml, keep directory
    directory = os.path.dirname(csv_path)
    return os.path.join(directory, "scan-ranges.yaml")
