"""
Unit tests for exports/influxdb.py

Tests cover:
- InfluxDB client configuration
- Connection with token authentication
- Connection with username/password authentication
- Measurement configuration and validation
- Data point publishing
- Error handling
"""

import pytest
from unittest.mock import Mock, MagicMock, PropertyMock
from exports.influxdb import export_influxdb


class TestInfluxDBInitialization:
    """Test InfluxDB export initialization."""

    def test_create_instance(self):
        """Test that InfluxDB export can be instantiated."""
        export = export_influxdb()
        assert export is not None

    def test_instance_type(self):
        """Test that instance is correct type."""
        export = export_influxdb()
        assert isinstance(export, export_influxdb)

    def test_initial_attributes(self):
        """Test that initial attributes are set correctly."""
        export = export_influxdb()
        assert export.client is None
        assert export.write_api is None


class TestInfluxDBConfiguration:
    """Test InfluxDB export configuration."""

    def test_configure_with_token_auth(self, mocker):
        """Test configure() with token authentication."""
        export = export_influxdb()

        # Mock InfluxDB client
        mock_client_class = mocker.patch('exports.influxdb.influxdb_client.InfluxDBClient')
        mock_client = Mock()
        mock_client.url = 'http://localhost:8086'
        mock_client.org = 'myorg'
        mock_write_api = Mock()
        mock_client.write_api.return_value = mock_write_api
        mock_client_class.return_value = mock_client

        # Mock inverter
        mock_inverter = mocker.Mock()
        mock_inverter.validateRegister.return_value = True

        # Config with token
        config = {
            'url': 'http://localhost:8086',
            'token': 'mytoken',
            'org': 'myorg',
            'bucket': 'mybucket',
            'measurements': [
                {'register': 'total_active_power', 'point': 'power'}
            ]
        }

        # Configure
        result = export.configure(config, mock_inverter)

        # Verify
        assert result is True
        assert export.influxdb_config['url'] == 'http://localhost:8086'
        assert export.influxdb_config['token'] == 'mytoken'
        assert export.influxdb_config['org'] == 'myorg'
        assert export.influxdb_config['bucket'] == 'mybucket'
        mock_client_class.assert_called_once_with(
            url='http://localhost:8086',
            token='mytoken',
            org='myorg'
        )

    def test_configure_with_username_password_auth(self, mocker):
        """Test configure() with username/password authentication."""
        export = export_influxdb()

        # Mock InfluxDB client
        mock_client_class = mocker.patch('exports.influxdb.influxdb_client.InfluxDBClient')
        mock_client = Mock()
        mock_client.url = 'http://localhost:8086'
        mock_client.org = 'myorg'
        mock_write_api = Mock()
        mock_client.write_api.return_value = mock_write_api
        mock_client_class.return_value = mock_client

        # Mock inverter
        mock_inverter = mocker.Mock()
        mock_inverter.validateRegister.return_value = True

        # Config with username/password
        config = {
            'url': 'http://localhost:8086',
            'username': 'testuser',
            'password': 'testpass',
            'org': 'myorg',
            'bucket': 'mybucket',
            'measurements': [
                {'register': 'battery_voltage', 'point': 'voltage'}
            ]
        }

        # Configure
        result = export.configure(config, mock_inverter)

        # Verify
        assert result is True
        mock_client_class.assert_called_once_with(
            url='http://localhost:8086',
            token='testuser:testpass',
            org='myorg'
        )

    def test_configure_with_default_url(self, mocker):
        """Test that configure() uses default URL."""
        export = export_influxdb()

        # Mock InfluxDB client
        mock_client_class = mocker.patch('exports.influxdb.influxdb_client.InfluxDBClient')
        mock_client = Mock()
        mock_client.url = 'http://localhost:8086'
        mock_client.org = 'myorg'
        mock_write_api = Mock()
        mock_client.write_api.return_value = mock_write_api
        mock_client_class.return_value = mock_client

        # Mock inverter
        mock_inverter = mocker.Mock()
        mock_inverter.validateRegister.return_value = True

        # Config without URL
        config = {
            'token': 'mytoken',
            'org': 'myorg',
            'bucket': 'mybucket',
            'measurements': []
        }

        # Configure
        result = export.configure(config, mock_inverter)

        # Verify default URL was used
        assert result is True
        call_args = mock_client_class.call_args[1]
        assert call_args['url'] == 'http://localhost:8086'

    def test_configure_fails_without_org(self, mocker):
        """Test that configure() fails without org."""
        export = export_influxdb()

        # Config without org
        config = {
            'token': 'mytoken',
            'bucket': 'mybucket',
            'measurements': []
        }

        # Mock inverter
        mock_inverter = mocker.Mock()

        # Should fail
        result = export.configure(config, mock_inverter)

        assert result is False

    def test_configure_fails_without_bucket(self, mocker):
        """Test that configure() fails without bucket."""
        export = export_influxdb()

        # Config without bucket
        config = {
            'token': 'mytoken',
            'org': 'myorg',
            'measurements': []
        }

        # Mock inverter
        mock_inverter = mocker.Mock()

        # Should fail
        result = export.configure(config, mock_inverter)

        assert result is False

    def test_configure_fails_without_auth(self, mocker):
        """Test that configure() fails without authentication."""
        export = export_influxdb()

        # Config without token or username/password
        config = {
            'org': 'myorg',
            'bucket': 'mybucket',
            'measurements': []
        }

        # Mock inverter
        mock_inverter = mocker.Mock()

        # Should fail
        result = export.configure(config, mock_inverter)

        assert result is False

    def test_configure_validates_measurements(self, mocker):
        """Test that configure() validates measurement registers."""
        export = export_influxdb()

        # Mock InfluxDB client
        mock_client_class = mocker.patch('exports.influxdb.influxdb_client.InfluxDBClient')
        mock_client = Mock()
        mock_client.url = 'http://localhost:8086'
        mock_client.org = 'myorg'
        mock_write_api = Mock()
        mock_client.write_api.return_value = mock_write_api
        mock_client_class.return_value = mock_client

        # Mock inverter - first register valid, second invalid
        mock_inverter = mocker.Mock()
        mock_inverter.validateRegister.side_effect = [True, False]

        # Config with two measurements
        config = {
            'token': 'mytoken',
            'org': 'myorg',
            'bucket': 'mybucket',
            'measurements': [
                {'register': 'valid_register', 'point': 'valid'},
                {'register': 'invalid_register', 'point': 'invalid'}
            ]
        }

        # Configure
        result = export.configure(config, mock_inverter)

        # Should succeed but only include valid measurement
        assert result is True
        assert len(export.influxdb_measurements) == 1
        assert export.influxdb_measurements[0]['register'] == 'valid_register'

    def test_configure_handles_client_creation_error(self, mocker):
        """Test that configure() handles InfluxDB client creation errors."""
        export = export_influxdb()

        # Mock InfluxDB client to raise exception
        mocker.patch('exports.influxdb.influxdb_client.InfluxDBClient',
                    side_effect=Exception("Connection failed"))

        # Mock inverter
        mock_inverter = mocker.Mock()

        # Config
        config = {
            'token': 'mytoken',
            'org': 'myorg',
            'bucket': 'mybucket',
            'measurements': []
        }

        # Should handle error and return False
        result = export.configure(config, mock_inverter)

        assert result is False

    def test_configure_creates_write_api(self, mocker):
        """Test that configure() creates write API."""
        export = export_influxdb()

        # Mock InfluxDB client
        mock_client_class = mocker.patch('exports.influxdb.influxdb_client.InfluxDBClient')
        mock_client = Mock()
        mock_client.url = 'http://localhost:8086'
        mock_client.org = 'myorg'
        mock_write_api = Mock()
        mock_client.write_api.return_value = mock_write_api
        mock_client_class.return_value = mock_client

        # Mock SYNCHRONOUS constant
        mock_sync = mocker.patch('exports.influxdb.SYNCHRONOUS')

        # Mock inverter
        mock_inverter = mocker.Mock()
        mock_inverter.validateRegister.return_value = True

        # Config
        config = {
            'token': 'mytoken',
            'org': 'myorg',
            'bucket': 'mybucket',
            'measurements': []
        }

        # Configure
        export.configure(config, mock_inverter)

        # Verify write_api was created
        mock_client.write_api.assert_called_once_with(write_options=mock_sync)
        assert export.write_api == mock_write_api


class TestInfluxDBPublishing:
    """Test InfluxDB data publishing."""

    def test_publish_writes_data_points(self, mocker):
        """Test that publish() writes data points to InfluxDB."""
        export = export_influxdb()

        # Setup InfluxDB config
        export.influxdb_config = {
            'bucket': 'mybucket',
            'org': 'myorg'
        }
        export.influxdb_measurements = [
            {'register': 'total_active_power', 'point': 'power'}
        ]

        # Mock client and write_api
        mock_client = Mock()
        mock_client.org = 'myorg'
        mock_write_api = Mock()
        export.client = mock_client
        export.write_api = mock_write_api

        # Mock Point class
        mock_point_class = mocker.patch('exports.influxdb.influxdb_client.Point')
        mock_point = Mock()
        mock_point.tag.return_value = mock_point
        mock_point.field.return_value = mock_point
        mock_point_class.return_value = mock_point

        # Mock inverter
        mock_inverter = Mock()
        mock_inverter.validateLatestScrape.return_value = True
        mock_inverter.getRegisterValue.return_value = 3500
        mock_inverter.getInverterModel.return_value = "SH5.0RS"

        # Publish
        result = export.publish(mock_inverter)

        # Verify
        assert result is True
        mock_write_api.write.assert_called_once()
        call_args = mock_write_api.write.call_args[0]
        assert call_args[0] == 'mybucket'
        assert call_args[1] == 'myorg'

    def test_publish_handles_string_values(self, mocker):
        """Test that publish() handles string register values."""
        export = export_influxdb()

        # Setup
        export.influxdb_config = {
            'bucket': 'mybucket',
            'org': 'myorg'
        }
        export.influxdb_measurements = [
            {'register': 'device_type', 'point': 'info'}
        ]

        # Mock client
        mock_client = Mock()
        mock_client.org = 'myorg'
        mock_write_api = Mock()
        export.client = mock_client
        export.write_api = mock_write_api

        # Mock Point
        mock_point_class = mocker.patch('exports.influxdb.influxdb_client.Point')
        mock_point = Mock()
        mock_point.tag.return_value = mock_point
        mock_point.field.return_value = mock_point
        mock_point_class.return_value = mock_point

        # Mock inverter - return string value
        mock_inverter = Mock()
        mock_inverter.validateLatestScrape.return_value = True
        mock_inverter.getRegisterValue.return_value = "SH5.0RS"
        mock_inverter.getInverterModel.return_value = "SH5.0RS"

        # Publish
        result = export.publish(mock_inverter)

        # Verify string was kept as-is
        assert result is True
        mock_point.field.assert_called_once_with('device_type', 'SH5.0RS')

    def test_publish_handles_numeric_values(self, mocker):
        """Test that publish() converts numeric values to float."""
        export = export_influxdb()

        # Setup
        export.influxdb_config = {
            'bucket': 'mybucket',
            'org': 'myorg'
        }
        export.influxdb_measurements = [
            {'register': 'battery_voltage', 'point': 'voltage'}
        ]

        # Mock client
        mock_client = Mock()
        mock_client.org = 'myorg'
        mock_write_api = Mock()
        export.client = mock_client
        export.write_api = mock_write_api

        # Mock Point
        mock_point_class = mocker.patch('exports.influxdb.influxdb_client.Point')
        mock_point = Mock()
        mock_point.tag.return_value = mock_point
        mock_point.field.return_value = mock_point
        mock_point_class.return_value = mock_point

        # Mock inverter - return int value
        mock_inverter = Mock()
        mock_inverter.validateLatestScrape.return_value = True
        mock_inverter.getRegisterValue.return_value = 52
        mock_inverter.getInverterModel.return_value = "SH5.0RS"

        # Publish
        result = export.publish(mock_inverter)

        # Verify int was converted to float
        assert result is True
        mock_point.field.assert_called_once_with('battery_voltage', 52.0)

    def test_publish_skips_missing_register(self, mocker):
        """Test that publish() skips if register missing from scrape."""
        export = export_influxdb()

        # Setup
        export.influxdb_config = {'bucket': 'mybucket'}
        export.influxdb_measurements = [
            {'register': 'missing_register', 'point': 'test'}
        ]

        # Mock inverter - register not in latest scrape
        mock_inverter = Mock()
        mock_inverter.validateLatestScrape.return_value = False

        # Publish should fail
        result = export.publish(mock_inverter)

        assert result is False

    def test_publish_handles_write_errors(self, mocker):
        """Test that publish() handles write errors gracefully."""
        export = export_influxdb()

        # Setup
        export.influxdb_config = {
            'bucket': 'mybucket',
            'org': 'myorg'
        }
        export.influxdb_measurements = [
            {'register': 'total_active_power', 'point': 'power'}
        ]

        # Mock client with write_api that raises exception
        mock_client = Mock()
        mock_client.org = 'myorg'
        mock_write_api = Mock()
        mock_write_api.write.side_effect = Exception("Write failed")
        export.client = mock_client
        export.write_api = mock_write_api

        # Mock Point
        mock_point_class = mocker.patch('exports.influxdb.influxdb_client.Point')
        mock_point = Mock()
        mock_point.tag.return_value = mock_point
        mock_point.field.return_value = mock_point
        mock_point_class.return_value = mock_point

        # Mock inverter
        mock_inverter = Mock()
        mock_inverter.validateLatestScrape.return_value = True
        mock_inverter.getRegisterValue.return_value = 3500
        mock_inverter.getInverterModel.return_value = "SH5.0RS"

        # Publish should handle error
        result = export.publish(mock_inverter)

        assert result is False

    def test_publish_multiple_measurements(self, mocker):
        """Test that publish() handles multiple measurements."""
        export = export_influxdb()

        # Setup with multiple measurements
        export.influxdb_config = {
            'bucket': 'mybucket',
            'org': 'myorg'
        }
        export.influxdb_measurements = [
            {'register': 'total_active_power', 'point': 'power'},
            {'register': 'battery_voltage', 'point': 'voltage'}
        ]

        # Mock client
        mock_client = Mock()
        mock_client.org = 'myorg'
        mock_write_api = Mock()
        export.client = mock_client
        export.write_api = mock_write_api

        # Mock Point
        mock_point_class = mocker.patch('exports.influxdb.influxdb_client.Point')
        mock_point = Mock()
        mock_point.tag.return_value = mock_point
        mock_point.field.return_value = mock_point
        mock_point_class.return_value = mock_point

        # Mock inverter
        mock_inverter = Mock()
        mock_inverter.validateLatestScrape.return_value = True
        # getRegisterValue is called twice per measurement (type check + value)
        mock_inverter.getRegisterValue.side_effect = [3500, 3500, 52.4, 52.4]
        mock_inverter.getInverterModel.return_value = "SH5.0RS"

        # Publish
        result = export.publish(mock_inverter)

        # Verify both measurements were processed
        assert result is True
        assert mock_point_class.call_count == 2
        mock_point_class.assert_any_call('power')
        mock_point_class.assert_any_call('voltage')

    def test_publish_tags_inverter_model(self, mocker):
        """Test that publish() tags data points with inverter model."""
        export = export_influxdb()

        # Setup
        export.influxdb_config = {
            'bucket': 'mybucket',
            'org': 'myorg'
        }
        export.influxdb_measurements = [
            {'register': 'total_active_power', 'point': 'power'}
        ]

        # Mock client
        mock_client = Mock()
        mock_client.org = 'myorg'
        mock_write_api = Mock()
        export.client = mock_client
        export.write_api = mock_write_api

        # Mock Point
        mock_point_class = mocker.patch('exports.influxdb.influxdb_client.Point')
        mock_point = Mock()
        mock_point.tag.return_value = mock_point
        mock_point.field.return_value = mock_point
        mock_point_class.return_value = mock_point

        # Mock inverter
        mock_inverter = Mock()
        mock_inverter.validateLatestScrape.return_value = True
        mock_inverter.getRegisterValue.return_value = 3500
        mock_inverter.getInverterModel.return_value = "SH5.0RS"

        # Publish
        export.publish(mock_inverter)

        # Verify tag was set
        mock_point.tag.assert_called_once_with("inverter", "SH5.0RS")
        mock_inverter.getInverterModel.assert_called_once_with(True)
