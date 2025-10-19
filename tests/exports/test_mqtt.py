"""
Unit tests for exports/mqtt.py

Tests cover:
- MQTT client configuration
- Connection handling
- Message publishing
- Home Assistant discovery
- Error handling
"""

import pytest
import json
from unittest.mock import Mock, MagicMock, PropertyMock
from exports.mqtt import export_mqtt


class TestMQTTInitialization:
    """Test MQTT export initialization."""

    def test_create_instance(self):
        """Test that MQTT export can be instantiated."""
        export = export_mqtt()
        assert export is not None

    def test_instance_type(self):
        """Test that instance is correct type."""
        export = export_mqtt()
        assert isinstance(export, export_mqtt)

    def test_initial_attributes(self):
        """Test that initial attributes are set correctly."""
        export = export_mqtt()
        assert export.mqtt_client is None
        assert export.sensor_topic is None
        assert export.mqtt_queue == []
        assert export.ha_discovery_published is False
        assert len(export.ha_variables) > 0  # Long list of HA variables


class TestMQTTConfiguration:
    """Test MQTT export configuration."""

    def test_configure_with_minimal_config(self, mocker):
        """Test configure() with minimal required configuration."""
        export = export_mqtt()

        # Mock MQTT client
        mock_client_class = mocker.patch('exports.mqtt.mqtt.Client')
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Mock inverter
        mock_inverter = mocker.Mock()
        mock_inverter.getInverterModel.return_value = "SH5.0RS"
        mock_inverter.getSerialNumber.return_value = "12345678"

        # Minimal config
        config = {'host': 'localhost'}

        # Configure
        result = export.configure(config, mock_inverter)

        # Verify
        assert result is True
        assert export.mqtt_config['host'] == 'localhost'
        assert export.mqtt_config['port'] == 1883  # Default
        assert export.mqtt_config['client_id'] == '12345678'
        assert export.mqtt_config['topic'] == 'SunGather/12345678'

    def test_configure_without_host_fails(self, mocker):
        """Test that configure() fails without host."""
        export = export_mqtt()

        # Mock inverter
        mock_inverter = mocker.Mock()
        mock_inverter.getInverterModel.return_value = "SH5.0RS"
        mock_inverter.getSerialNumber.return_value = "12345678"

        # Config without host
        config = {}

        # Should fail
        result = export.configure(config, mock_inverter)

        assert result is False

    def test_configure_custom_settings(self, mocker):
        """Test configure() with custom settings."""
        export = export_mqtt()

        # Mock MQTT client
        mock_client_class = mocker.patch('exports.mqtt.mqtt.Client')
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Mock inverter
        mock_inverter = mocker.Mock()
        mock_inverter.getInverterModel.return_value = "SH5.0RS"
        mock_inverter.getSerialNumber.return_value = "12345678"

        # Custom config
        config = {
            'host': '192.168.1.100',
            'port': 1884,
            'client_id': 'my_client',
            'topic': 'my/topic',
            'username': 'user',
            'password': 'pass'
        }

        # Configure
        result = export.configure(config, mock_inverter)

        # Verify
        assert result is True
        assert export.mqtt_config['host'] == '192.168.1.100'
        assert export.mqtt_config['port'] == 1884
        assert export.mqtt_config['client_id'] == 'my_client'
        assert export.mqtt_config['topic'] == 'my/topic'
        assert export.mqtt_config['username'] == 'user'
        assert export.mqtt_config['password'] == 'pass'

    def test_configure_with_authentication(self, mocker):
        """Test that configure() sets up authentication."""
        export = export_mqtt()

        # Mock MQTT client
        mock_client_class = mocker.patch('exports.mqtt.mqtt.Client')
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Mock inverter
        mock_inverter = mocker.Mock()
        mock_inverter.getInverterModel.return_value = "SH5.0RS"
        mock_inverter.getSerialNumber.return_value = "12345678"

        # Config with auth
        config = {
            'host': 'localhost',
            'username': 'testuser',
            'password': 'testpass'
        }

        # Configure
        export.configure(config, mock_inverter)

        # Verify username_pw_set was called
        mock_client.username_pw_set.assert_called_once_with('testuser', 'testpass')

    def test_configure_with_tls(self, mocker):
        """Test that configure() enables TLS for port 8883."""
        export = export_mqtt()

        # Mock MQTT client
        mock_client_class = mocker.patch('exports.mqtt.mqtt.Client')
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Mock inverter
        mock_inverter = mocker.Mock()
        mock_inverter.getInverterModel.return_value = "SH5.0RS"
        mock_inverter.getSerialNumber.return_value = "12345678"

        # Config with TLS port
        config = {
            'host': 'localhost',
            'port': 8883
        }

        # Configure
        export.configure(config, mock_inverter)

        # Verify TLS was enabled
        mock_client.tls_set.assert_called_once()

    def test_configure_starts_connection(self, mocker):
        """Test that configure() starts MQTT connection."""
        export = export_mqtt()

        # Mock MQTT client
        mock_client_class = mocker.patch('exports.mqtt.mqtt.Client')
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Mock inverter
        mock_inverter = mocker.Mock()
        mock_inverter.getInverterModel.return_value = "SH5.0RS"
        mock_inverter.getSerialNumber.return_value = "12345678"

        # Configure
        config = {'host': 'localhost'}
        export.configure(config, mock_inverter)

        # Verify connection started
        mock_client.connect_async.assert_called_once_with('localhost', port=1883, keepalive=60)
        mock_client.loop_start.assert_called_once()

    def test_configure_with_home_assistant_invalid_register(self, mocker):
        """Test configure() with HA discovery but invalid register."""
        export = export_mqtt()

        # Mock MQTT client
        mock_client_class = mocker.patch('exports.mqtt.mqtt.Client')
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Mock inverter
        mock_inverter = mocker.Mock()
        mock_inverter.getInverterModel.return_value = "SH5.0RS"
        mock_inverter.getSerialNumber.return_value = "12345678"
        mock_inverter.validateRegister.return_value = False  # Invalid register

        # Config with HA discovery
        config = {
            'host': 'localhost',
            'homeassistant': True,
            'ha_sensors': [
                {'register': 'invalid_register', 'name': 'Test', 'sensor_type': 'sensor'}
            ]
        }

        # Should fail
        result = export.configure(config, mock_inverter)

        assert result is False


class TestMQTTCallbacks:
    """Test MQTT callback handlers."""

    def test_on_connect_success(self, mocker):
        """Test on_connect callback with successful connection."""
        export = export_mqtt()

        # Mock client
        mock_client = Mock()
        mock_client._host = 'localhost'
        mock_client._port = 1883

        # Call callback
        export.on_connect(mock_client, None, None, 0, None)

        # Should not raise exception

    def test_on_connect_failure(self, mocker):
        """Test on_connect callback with failed connection."""
        export = export_mqtt()

        # Mock client
        mock_client = Mock()
        mock_client._host = 'localhost'
        mock_client._port = 1883

        # Call callback with error code
        export.on_connect(mock_client, None, None, 5, None)

        # Should not raise exception

    def test_on_disconnect_clean(self, mocker):
        """Test on_disconnect callback with clean disconnect."""
        export = export_mqtt()

        # Mock client
        mock_client = Mock()

        # Call callback
        export.on_disconnect(mock_client, None, None, 0, None)

        # Should not raise exception

    def test_on_disconnect_unexpected(self, mocker):
        """Test on_disconnect callback with unexpected disconnect."""
        export = export_mqtt()

        # Mock client
        mock_client = Mock()

        # Call callback with error code
        export.on_disconnect(mock_client, None, None, 1, None)

        # Should not raise exception

    def test_on_publish_removes_from_queue(self, mocker):
        """Test on_publish callback removes message from queue."""
        export = export_mqtt()
        export.mqtt_queue = [123, 456, 789]

        # Mock client
        mock_client = Mock()

        # Call callback
        export.on_publish(mock_client, None, 456, None, None)

        # Verify message removed from queue
        assert 456 not in export.mqtt_queue
        assert len(export.mqtt_queue) == 2

    def test_on_publish_message_not_in_queue(self, mocker):
        """Test on_publish callback when message not in queue."""
        export = export_mqtt()
        export.mqtt_queue = [123]

        # Mock client
        mock_client = Mock()

        # Call callback with message not in queue
        export.on_publish(mock_client, None, 999, None, None)

        # Should not raise exception


class TestMQTTPublishing:
    """Test MQTT message publishing."""

    def test_publish_basic_message(self, mocker):
        """Test basic message publishing."""
        export = export_mqtt()

        # Setup MQTT config
        export.mqtt_config = {
            'topic': 'test/topic',
            'homeassistant': False
        }
        export.mqtt_queue = []

        # Mock MQTT client
        mock_client = Mock()
        mock_client.is_connected.return_value = True
        mock_publish_result = Mock()
        mock_publish_result.mid = 123
        mock_client.publish.return_value = mock_publish_result
        export.mqtt_client = mock_client

        # Mock inverter
        mock_inverter = Mock()
        mock_inverter.inverter_config = {'model': 'SH5.0RS'}
        mock_inverter.client_config = {'host': '192.168.1.100'}
        mock_inverter.latest_scrape = {'battery_voltage': 52.4}

        # Publish
        result = export.publish(mock_inverter)

        # Verify
        assert result is True
        mock_client.publish.assert_called_once()
        assert 123 in export.mqtt_queue

    def test_publish_when_disconnected(self, mocker):
        """Test publish() when MQTT client is disconnected."""
        export = export_mqtt()

        # Setup MQTT config
        export.mqtt_config = {
            'topic': 'test/topic',
            'homeassistant': False
        }

        # Mock MQTT client as disconnected
        mock_client = Mock()
        mock_client.is_connected.return_value = False
        export.mqtt_client = mock_client

        # Mock inverter
        mock_inverter = Mock()
        mock_inverter.inverter_config = {}
        mock_inverter.client_config = {}
        mock_inverter.latest_scrape = {}

        # Publish should still work (messages queued)
        result = export.publish(mock_inverter)

        # Should still succeed (automatic reconnect)
        assert result is True

    def test_publish_with_no_client(self, mocker):
        """Test publish() when MQTT client is not initialized."""
        export = export_mqtt()
        export.mqtt_client = None

        # Mock inverter
        mock_inverter = Mock()

        # Should fail gracefully
        result = export.publish(mock_inverter)

        assert result is False

    def test_publish_with_home_assistant_discovery(self, mocker):
        """Test publish() with Home Assistant discovery."""
        export = export_mqtt()

        # Setup for HA discovery
        export.model = "SH5.0RS"
        export.serial_number = "12345678"
        export.mqtt_config = {
            'topic': 'test/topic',
            'homeassistant': True
        }
        export.ha_discovery_published = False
        export.ha_sensors = [
            {
                'name': 'Battery Voltage',
                'sensor_type': 'sensor',
                'register': 'battery_voltage'
            }
        ]
        export.mqtt_queue = []

        # Mock MQTT client
        mock_client = Mock()
        mock_client.is_connected.return_value = True
        mock_publish_result = Mock()
        mock_publish_result.mid = 123
        mock_client.publish.return_value = mock_publish_result
        export.mqtt_client = mock_client

        # Mock inverter
        mock_inverter = Mock()
        mock_inverter.inverter_config = {}
        mock_inverter.client_config = {}
        mock_inverter.latest_scrape = {}
        mock_inverter.getHost.return_value = '192.168.1.100'
        mock_inverter.getRegisterUnit.return_value = 'V'

        # Publish
        result = export.publish(mock_inverter)

        # Verify
        assert result is True
        assert export.ha_discovery_published is True
        # Should have published discovery + data
        assert mock_client.publish.call_count == 2

    def test_publish_home_assistant_discovery_only_once(self, mocker):
        """Test that HA discovery is only published once."""
        export = export_mqtt()

        # Setup for HA discovery
        export.model = "SH5.0RS"
        export.serial_number = "12345678"
        export.mqtt_config = {
            'topic': 'test/topic',
            'homeassistant': True
        }
        export.ha_discovery_published = True  # Already published
        export.ha_sensors = []
        export.mqtt_queue = []

        # Mock MQTT client
        mock_client = Mock()
        mock_client.is_connected.return_value = True
        mock_publish_result = Mock()
        mock_publish_result.mid = 123
        mock_client.publish.return_value = mock_publish_result
        export.mqtt_client = mock_client

        # Mock inverter
        mock_inverter = Mock()
        mock_inverter.inverter_config = {}
        mock_inverter.client_config = {}
        mock_inverter.latest_scrape = {}

        # Publish
        export.publish(mock_inverter)

        # Should only publish data, not discovery
        assert mock_client.publish.call_count == 1


class TestMQTTHelperMethods:
    """Test MQTT helper methods."""

    def test_clean_name_lowercase(self):
        """Test cleanName() converts to lowercase."""
        export = export_mqtt()
        result = export.cleanName("Battery Voltage")
        assert result == "battery_voltage"

    def test_clean_name_replaces_spaces(self):
        """Test cleanName() replaces spaces with underscores."""
        export = export_mqtt()
        result = export.cleanName("Total Active Power")
        assert result == "total_active_power"

    def test_clean_name_already_clean(self):
        """Test cleanName() with already clean name."""
        export = export_mqtt()
        result = export.cleanName("battery_voltage")
        assert result == "battery_voltage"
