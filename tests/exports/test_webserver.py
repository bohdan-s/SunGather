"""
Unit tests for exports/webserver.py

Tests cover:
- Webserver configuration and startup
- HTTP GET request handling (/, /metrics, /json, /config)
- HTTP POST request handling
- Data formatting (HTML, JSON, metrics)
- Error handling
"""

import pytest
import json
from io import BytesIO
from unittest.mock import Mock, MagicMock
from exports.webserver import export_webserver, MyServer


class TestWebserverExportInitialization:
    """Test webserver export initialization."""

    def test_create_instance(self):
        """Test that webserver export can be instantiated."""
        export = export_webserver()
        assert export is not None

    def test_instance_type(self):
        """Test that instance is correct type."""
        export = export_webserver()
        assert isinstance(export, export_webserver)

    def test_class_attributes_set_by_publish(self, mocker):
        """Test that class attributes are set after publish() is called."""
        export = export_webserver()

        # Mock inverter
        mock_inverter = mocker.Mock()
        mock_inverter.latest_scrape = {}
        mock_inverter.client_config = {}
        mock_inverter.inverter_config = {}

        # Publish sets the class attributes
        export.publish(mock_inverter)

        # Now attributes should exist
        assert hasattr(export_webserver, 'main')
        assert hasattr(export_webserver, 'metrics')
        assert hasattr(export_webserver, 'json')


class TestWebserverConfiguration:
    """Test webserver export configuration."""

    def test_configure_starts_server(self, mocker):
        """Test that configure() starts HTTP server."""
        export = export_webserver()

        # Mock HTTPServer and Thread
        mock_server = mocker.patch('exports.webserver.HTTPServer')
        mock_thread = mocker.patch('exports.webserver.Thread')

        # Mock inverter
        mock_inverter = mocker.Mock()
        mock_inverter.client_config = {'host': '192.168.1.100'}
        mock_inverter.inverter_config = {'model': 'SH5.0RS'}

        # Configure
        config = {'port': 8080}
        result = export.configure(config, mock_inverter)

        # Verify
        assert result is True
        mock_server.assert_called_once()
        mock_thread.assert_called_once()

    def test_configure_default_port(self, mocker):
        """Test that configure() uses default port 8080."""
        export = export_webserver()

        # Mock HTTPServer and Thread
        mock_server_class = mocker.patch('exports.webserver.HTTPServer')
        mocker.patch('exports.webserver.Thread')

        # Mock inverter
        mock_inverter = mocker.Mock()
        mock_inverter.client_config = {}
        mock_inverter.inverter_config = {}

        # Configure without port
        result = export.configure({}, mock_inverter)

        # Verify default port was used
        assert result is True
        call_args = mock_server_class.call_args[0]
        assert call_args[0] == ('', 8080)

    def test_configure_custom_port(self, mocker):
        """Test that configure() uses custom port."""
        export = export_webserver()

        # Mock HTTPServer and Thread
        mock_server_class = mocker.patch('exports.webserver.HTTPServer')
        mocker.patch('exports.webserver.Thread')

        # Mock inverter
        mock_inverter = mocker.Mock()
        mock_inverter.client_config = {}
        mock_inverter.inverter_config = {}

        # Configure with custom port
        result = export.configure({'port': 9999}, mock_inverter)

        # Verify custom port was used
        assert result is True
        call_args = mock_server_class.call_args[0]
        assert call_args[0] == ('', 9999)

    def test_configure_builds_config_html(self, mocker):
        """Test that configure() builds configuration HTML."""
        export = export_webserver()

        # Mock HTTPServer and Thread
        mocker.patch('exports.webserver.HTTPServer')
        mocker.patch('exports.webserver.Thread')

        # Mock inverter with configs
        mock_inverter = mocker.Mock()
        mock_inverter.client_config = {'host': '192.168.1.100', 'port': 502}
        mock_inverter.inverter_config = {'model': 'SH5.0RS', 'connection': 'modbus'}

        # Configure
        export.configure({}, mock_inverter)

        # Verify config HTML was built
        assert hasattr(export_webserver, 'config')
        assert '192.168.1.100' in export_webserver.config
        assert 'SH5.0RS' in export_webserver.config

    def test_configure_handles_error(self, mocker):
        """Test that configure() handles server startup errors."""
        export = export_webserver()

        # Mock HTTPServer to raise exception
        mocker.patch('exports.webserver.HTTPServer', side_effect=OSError("Port in use"))

        # Mock inverter
        mock_inverter = mocker.Mock()
        mock_inverter.client_config = {}
        mock_inverter.inverter_config = {}

        # Configure should return False on error
        result = export.configure({}, mock_inverter)

        assert result is False


class TestWebserverPublishing:
    """Test webserver data publishing."""

    def test_publish_returns_true(self, mocker):
        """Test that publish() returns True."""
        export = export_webserver()

        # Mock inverter
        mock_inverter = mocker.Mock()
        mock_inverter.latest_scrape = {'total_active_power': 3500}
        mock_inverter.client_config = {'host': '192.168.1.100'}
        mock_inverter.inverter_config = {'model': 'SH5.0RS'}
        mock_inverter.getRegisterAddress.return_value = '5000'
        mock_inverter.getRegisterUnit.return_value = 'W'

        # Publish
        result = export.publish(mock_inverter)

        assert result is True

    def test_publish_builds_html_body(self, mocker):
        """Test that publish() builds HTML main body."""
        export = export_webserver()

        # Mock inverter
        mock_inverter = mocker.Mock()
        mock_inverter.latest_scrape = {'battery_voltage': 52.4}
        mock_inverter.client_config = {}
        mock_inverter.inverter_config = {}
        mock_inverter.getRegisterAddress.return_value = '5001'
        mock_inverter.getRegisterUnit.return_value = 'V'

        # Publish
        export.publish(mock_inverter)

        # Verify HTML was built with register data
        assert hasattr(export_webserver, 'main')
        assert 'battery_voltage' in export_webserver.main
        assert '52.4' in export_webserver.main

    def test_publish_builds_metrics_endpoint_data(self, mocker):
        """Test that publish() builds data for /metrics endpoint."""
        export = export_webserver()

        # Mock inverter
        mock_inverter = mocker.Mock()
        mock_inverter.latest_scrape = {'total_active_power': 3500}
        mock_inverter.client_config = {}
        mock_inverter.inverter_config = {}
        mock_inverter.getRegisterAddress.return_value = '5000'
        mock_inverter.getRegisterUnit.return_value = 'W'

        # Publish
        export.publish(mock_inverter)

        # Verify metrics format: register_name{address="X", unit="Y"} value
        assert hasattr(export_webserver, 'metrics')
        assert 'total_active_power' in export_webserver.metrics
        assert 'address="5000"' in export_webserver.metrics
        assert 'unit="W"' in export_webserver.metrics
        assert '3500' in export_webserver.metrics

    def test_publish_builds_json(self, mocker):
        """Test that publish() builds JSON output."""
        export = export_webserver()

        # Mock inverter
        mock_inverter = mocker.Mock()
        mock_inverter.latest_scrape = {'battery_voltage': 52.4}
        mock_inverter.client_config = {'host': '192.168.1.100'}
        mock_inverter.inverter_config = {'model': 'SH5.0RS'}
        mock_inverter.getRegisterAddress.return_value = '5001'
        mock_inverter.getRegisterUnit.return_value = 'V'

        # Publish
        export.publish(mock_inverter)

        # Verify JSON was built
        assert hasattr(export_webserver, 'json')
        json_data = json.loads(export_webserver.json)
        assert 'registers' in json_data
        assert 'client_config' in json_data
        assert 'inverter_config' in json_data
        assert json_data['client_config']['host'] == '192.168.1.100'
        assert json_data['inverter_config']['model'] == 'SH5.0RS'

    def test_publish_with_empty_data(self, mocker):
        """Test publish() with no register data."""
        export = export_webserver()

        # Mock inverter with empty data
        mock_inverter = mocker.Mock()
        mock_inverter.latest_scrape = {}
        mock_inverter.client_config = {}
        mock_inverter.inverter_config = {}

        # Should not raise exception
        result = export.publish(mock_inverter)

        assert result is True


class TestHTTPGetHandlers:
    """Test HTTP GET request handlers."""

    def test_get_root_path(self, mocker):
        """Test GET request to / returns HTML."""
        # Set up class data
        export_webserver.main = "Test main content"

        # Create handler without triggering __init__ auto-handling
        handler = MyServer.__new__(MyServer)
        handler.path = '/'

        # Mock methods
        handler.send_response = Mock()
        handler.send_header = Mock()
        handler.end_headers = Mock()
        handler.wfile = Mock()

        # Handle request
        handler.do_GET()

        # Verify response
        handler.send_response.assert_called_with(200)
        handler.send_header.assert_called_with("Content-type", "text/html")
        assert handler.wfile.write.call_count > 0

    def test_get_metrics_path(self, mocker):
        """Test GET request to /metrics returns metrics data."""
        # Set up class data
        export_webserver.metrics = "test_metric{label=\"value\"} 123\n"

        # Create handler without triggering __init__
        handler = MyServer.__new__(MyServer)
        handler.path = '/metrics'

        # Mock methods
        handler.send_response = Mock()
        handler.send_header = Mock()
        handler.end_headers = Mock()
        handler.wfile = Mock()

        # Handle request
        handler.do_GET()

        # Verify response
        handler.send_response.assert_called_with(200)
        handler.send_header.assert_called_with("Content-type", "text/plain")
        handler.wfile.write.assert_called_once()

        # Verify content
        written_content = handler.wfile.write.call_args[0][0]
        assert b"test_metric" in written_content

    def test_get_json_path(self, mocker):
        """Test GET request to /json returns JSON."""
        # Set up class data
        test_json = {"registers": {}, "client_config": {"host": "192.168.1.100"}}
        export_webserver.json = json.dumps(test_json)

        # Create handler without triggering __init__
        handler = MyServer.__new__(MyServer)
        handler.path = '/json'

        # Mock methods
        handler.send_response = Mock()
        handler.send_header = Mock()
        handler.end_headers = Mock()
        handler.wfile = Mock()

        # Handle request
        handler.do_GET()

        # Verify response
        handler.send_response.assert_called_with(200)
        handler.send_header.assert_called_with("Content-type", "application/json")
        handler.wfile.write.assert_called_once()

        # Verify JSON content
        written_content = handler.wfile.write.call_args[0][0].decode('utf-8')
        parsed_json = json.loads(written_content)
        assert parsed_json['client_config']['host'] == '192.168.1.100'

    def test_get_config_path(self, mocker):
        """Test GET request to /config returns configuration HTML."""
        # Set up class data
        export_webserver.config = "<html>Config page</html>"

        # Create handler without triggering __init__
        handler = MyServer.__new__(MyServer)
        handler.path = '/config'

        # Mock methods
        handler.send_response = Mock()
        handler.send_header = Mock()
        handler.end_headers = Mock()
        handler.wfile = Mock()

        # Handle request
        handler.do_GET()

        # Verify response
        handler.send_response.assert_called_with(200)
        handler.send_header.assert_called_with("Content-type", "text/html")
        handler.wfile.write.assert_called_once()


class TestHTTPPostHandlers:
    """Test HTTP POST request handlers."""

    def test_post_with_valid_data(self, mocker):
        """Test POST request with valid data."""
        # Create handler without triggering __init__
        handler = MyServer.__new__(MyServer)

        # Mock headers and request body
        handler.headers = {'Content-Length': '10'}
        handler.rfile = BytesIO(b"key=value")

        # Mock methods
        handler.send_response = Mock()
        handler.send_header = Mock()
        handler.end_headers = Mock()
        handler.wfile = Mock()

        # Handle request
        handler.do_POST()

        # Verify response was sent
        handler.wfile.write.assert_called_once()

    def test_post_with_missing_content_length(self, mocker):
        """Test POST request without Content-Length header."""
        # Create handler without triggering __init__
        handler = MyServer.__new__(MyServer)

        # Mock headers without Content-Length
        handler.headers = {}

        # Mock methods
        handler.send_response = Mock()
        handler.send_header = Mock()
        handler.end_headers = Mock()
        handler.wfile = Mock()

        # Handle request
        handler.do_POST()

        # Verify 400 Bad Request
        handler.send_response.assert_called_with(400)
        handler.wfile.write.assert_called_once_with(b"Bad Request: Missing Content-Length")

    def test_post_handles_exception(self, mocker):
        """Test POST request error handling."""
        # Create handler without triggering __init__
        handler = MyServer.__new__(MyServer)

        # Mock headers
        handler.headers = {'Content-Length': '10'}
        # Mock rfile to raise exception
        handler.rfile = Mock()
        handler.rfile.read.side_effect = Exception("Read error")

        # Mock methods
        handler.send_response = Mock()
        handler.send_header = Mock()
        handler.end_headers = Mock()
        handler.wfile = Mock()

        # Handle request
        handler.do_POST()

        # Verify 500 Internal Server Error
        handler.send_response.assert_called_with(500)
