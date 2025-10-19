# SunGather Tests

This directory contains unit tests for the SunGather project.

## Running Tests

### Activate virtual environment:
```bash
source venv/bin/activate
```

You should see `(venv)` in your prompt.

### Install test dependencies:
```bash
pip install -r requirements-dev.txt
```

### Run all tests:
```bash
pytest
```

### Run tests with coverage report:
```bash
pytest --cov=SunGather --cov-report=html
```

### Run specific test file:
```bash
pytest tests/test_sungather.py
```

### Run specific test class:
```bash
pytest tests/exports/test_mqtt.py::TestMQTTConfiguration
```

### Run specific test:
```bash
pytest tests/exports/test_mqtt.py::TestMQTTConfiguration::test_placeholder
```

## Test Organization

```
tests/
├── conftest.py              # Shared fixtures and test configuration
├── test_sungather.py        # Tests for main sungather.py module
└── exports/                 # Export plugin tests
    ├── test_console.py      # Console export tests
    ├── test_mqtt.py         # MQTT export tests
    ├── test_influxdb.py     # InfluxDB export tests
    └── test_webserver.py    # Webserver export tests
```

## Writing Tests

### Using fixtures:

Fixtures are defined in `conftest.py` and automatically available to all tests:

```python
def test_mqtt_configure(mock_mqtt_config, mocker):
    """Test MQTT configuration."""
    export = export_mqtt()
    result = export.configure(mock_mqtt_config, mock_inverter)
    assert result == True
```

### Using mocks:

The `mocker` fixture from pytest-mock provides mocking capabilities:

```python
def test_connection_failure(mocker):
    """Test handling of connection failures."""
    mock_client = mocker.patch('paho.mqtt.client.Client')
    mock_client.return_value.connect.side_effect = Exception("Connection refused")

    # Your test code here
```

### Test markers:

Use markers to categorize tests:

```python
@pytest.mark.unit
def test_fast_unit_test():
    """Fast unit test with no external dependencies."""
    pass

@pytest.mark.slow
def test_slow_integration():
    """Slow integration test."""
    pass
```

Run only unit tests:
```bash
pytest -m unit
```

## Coverage Reports

After running tests with coverage, open the HTML report:
```bash
open htmlcov/index.html
```

## Continuous Integration

Tests run automatically on GitHub Actions for:
- All pull requests
- Pushes to `main` and `develop` branches
- Python versions: 3.9, 3.10, 3.11, 3.12

Coverage reports are uploaded to Codecov and stored as artifacts.
