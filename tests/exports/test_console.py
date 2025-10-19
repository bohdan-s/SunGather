"""
Unit tests for exports/console.py

Tests cover:
- Console export initialization
- Console output formatting
- Register display
"""

import pytest
from exports.console import export_console


class TestConsoleExportInitialization:
    """Test console export initialization."""

    def test_create_instance(self):
        """Test that console export can be instantiated."""
        export = export_console()
        assert export is not None

    def test_instance_type(self):
        """Test that instance is correct type."""
        export = export_console()
        assert isinstance(export, export_console)


class TestConsoleConfigureMethod:
    """Test console export configuration."""

    def test_configure_returns_true(self, mocker):
        """Test that configure() returns True on success."""
        export = export_console()

        # Create a mock inverter with required attributes
        mock_inverter = mocker.Mock()
        mock_inverter.client_config = {
            'host': '192.168.1.100',
            'port': 502,
            'timeout': 10
        }
        mock_inverter.inverter_config = {
            'model': 'SH5.0RS',
            'connection': 'modbus',
            'slave': 0x01
        }

        # Mock print to capture output
        mock_print = mocker.patch('builtins.print')

        # Call configure
        result = export.configure({}, mock_inverter)

        # Verify
        assert result is True
        assert mock_print.call_count > 0  # Should have printed something

    def test_configure_prints_client_config(self, mocker, capsys):
        """Test that configure() prints client configuration."""
        export = export_console()

        # Create mock inverter
        mock_inverter = mocker.Mock()
        mock_inverter.client_config = {'host': '192.168.1.100'}
        mock_inverter.inverter_config = {}

        # Call configure (prints to stdout)
        export.configure({}, mock_inverter)

        # Capture printed output
        captured = capsys.readouterr()

        # Verify output contains our config
        assert '192.168.1.100' in captured.out
        assert 'host' in captured.out

    def test_configure_prints_inverter_config(self, mocker, capsys):
        """Test that configure() prints inverter configuration."""
        export = export_console()

        # Create mock inverter
        mock_inverter = mocker.Mock()
        mock_inverter.client_config = {}
        mock_inverter.inverter_config = {'model': 'SH5.0RS'}

        # Call configure
        export.configure({}, mock_inverter)

        # Capture output
        captured = capsys.readouterr()

        # Verify
        assert 'SH5.0RS' in captured.out
        assert 'model' in captured.out

    def test_configure_with_empty_config(self, mocker):
        """Test configure() handles empty configuration."""
        export = export_console()

        # Create mock inverter with empty configs
        mock_inverter = mocker.Mock()
        mock_inverter.client_config = {}
        mock_inverter.inverter_config = {}

        # Should not raise exception
        result = export.configure({}, mock_inverter)

        assert result is True


class TestConsolePublishMethod:
    """Test console export publishing."""

    def test_publish_returns_true(self, mocker):
        """Test that publish() returns True on success."""
        export = export_console()

        # Create mock inverter with data
        mock_inverter = mocker.Mock()
        mock_inverter.latest_scrape = {
            'total_active_power': 3500,
            'battery_voltage': 52.4
        }
        mock_inverter.getRegisterAddress.return_value = '5000'
        mock_inverter.getRegisterUnit.return_value = 'W'

        # Mock print
        mocker.patch('builtins.print')

        # Call publish
        result = export.publish(mock_inverter)

        # Verify
        assert result is True

    def test_publish_prints_register_data(self, mocker, capsys):
        """Test that publish() prints register data."""
        export = export_console()

        # Create mock inverter
        mock_inverter = mocker.Mock()
        mock_inverter.latest_scrape = {
            'total_active_power': 3500,
            'battery_voltage': 52.4
        }
        mock_inverter.getRegisterAddress.side_effect = lambda reg: {
            'total_active_power': '5000',
            'battery_voltage': '5001'
        }.get(reg, '----')
        mock_inverter.getRegisterUnit.side_effect = lambda reg: {
            'total_active_power': 'W',
            'battery_voltage': 'V'
        }.get(reg, '')

        # Call publish
        export.publish(mock_inverter)

        # Capture output
        captured = capsys.readouterr()

        # Verify output contains register data
        assert 'total_active_power' in captured.out
        assert 'battery_voltage' in captured.out
        assert '3500' in captured.out
        assert '52.4' in captured.out

    def test_publish_shows_register_count(self, mocker, capsys):
        """Test that publish() shows count of logged registers."""
        export = export_console()

        # Create mock inverter with 3 registers
        mock_inverter = mocker.Mock()
        mock_inverter.latest_scrape = {
            'reg1': 100,
            'reg2': 200,
            'reg3': 300
        }
        mock_inverter.getRegisterAddress.return_value = '5000'
        mock_inverter.getRegisterUnit.return_value = ''

        # Call publish
        export.publish(mock_inverter)

        # Capture output
        captured = capsys.readouterr()

        # Verify count is shown
        assert 'Logged 3 registers to Console' in captured.out

    def test_publish_with_empty_data(self, mocker, capsys):
        """Test publish() handles empty register data."""
        export = export_console()

        # Create mock inverter with no data
        mock_inverter = mocker.Mock()
        mock_inverter.latest_scrape = {}

        # Should not raise exception
        result = export.publish(mock_inverter)

        # Verify
        assert result is True

        # Capture output
        captured = capsys.readouterr()
        assert 'Logged 0 registers to Console' in captured.out

    def test_publish_calls_inverter_methods(self, mocker):
        """Test that publish() calls inverter helper methods."""
        export = export_console()

        # Create mock inverter
        mock_inverter = mocker.Mock()
        mock_inverter.latest_scrape = {'test_register': 123}
        mock_inverter.getRegisterAddress.return_value = '5000'
        mock_inverter.getRegisterUnit.return_value = 'W'

        # Mock print
        mocker.patch('builtins.print')

        # Call publish
        export.publish(mock_inverter)

        # Verify inverter methods were called
        mock_inverter.getRegisterAddress.assert_called_with('test_register')
        mock_inverter.getRegisterUnit.assert_called_with('test_register')
