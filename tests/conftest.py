"""
Shared pytest fixtures for SunGather tests.

This file is automatically discovered by pytest and makes fixtures
available to all test files.
"""

import pytest
import sys
from pathlib import Path

# Add SunGather directory to Python path for imports
sungather_dir = Path(__file__).parent.parent / "SunGather"
sys.path.insert(0, str(sungather_dir))


# Fixture: Mock inverter configuration
@pytest.fixture
def mock_inverter_config():
    """Standard inverter configuration for testing."""
    return {
        'host': '192.168.1.100',
        'port': 502,
        'timeout': 10,
        'retries': 3,
        'slave': 0x01,
        'scan_interval': 30,
        'connection': 'modbus',
        'model': 'SH5.0RS',
        'smart_meter': False,
        'use_local_time': False,
        'log_console': 'WARNING',
        'log_file': 'OFF',
        'level': 1
    }


# Fixture: Mock register data
@pytest.fixture
def mock_register_data():
    """Sample register data returned from inverter."""
    return {
        'device_type_code': 'SH5.0RS',
        'serial_number': '12345678',
        'total_active_power': 3500,
        'meter_power': -200,  # Negative = exporting to grid
        'load_power': 1500,
        'battery_voltage': 52.4,
        'battery_current': 10.5,
        'battery_power': 550,
        'daily_export_energy': 15.2,
        'timestamp': '2025-10-19 10:30:00'
    }


# Fixture: Mock MQTT export configuration
@pytest.fixture
def mock_mqtt_config():
    """Standard MQTT export configuration for testing."""
    return {
        'name': 'mqtt',
        'enabled': True,
        'host': 'localhost',
        'port': 1883,
        'topic': 'SunGather/12345678',
        'username': None,
        'password': None,
        'homeassistant': False
    }


# Fixture: Mock InfluxDB export configuration
@pytest.fixture
def mock_influxdb_config():
    """Standard InfluxDB export configuration for testing."""
    return {
        'name': 'influxdb',
        'enabled': True,
        'url': 'http://localhost:8086',
        'token': 'test-token',
        'org': 'test-org',
        'bucket': 'sungather',
        'measurements': [
            {'register': 'total_active_power', 'point': 'power'},
            {'register': 'battery_voltage', 'point': 'battery'}
        ]
    }


# Fixture: Mock webserver export configuration
@pytest.fixture
def mock_webserver_config():
    """Standard webserver export configuration for testing."""
    return {
        'name': 'webserver',
        'enabled': True,
        'port': 8080
    }
