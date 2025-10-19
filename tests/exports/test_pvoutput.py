"""
Unit tests for exports/pvoutput.py

Tests cover:
- PVOutput export initialization
- Configuration with API credentials
- Team membership management
- Data collection and averaging
- Batch upload functionality
- Cumulative flag handling
- Error handling for API calls
"""

import pytest
import time
from unittest.mock import Mock, PropertyMock
from exports.pvoutput import export_pvoutput


class TestPVOutputInitialization:
    """Test PVOutput export initialization."""

    def test_create_instance(self):
        """Test that PVOutput export can be instantiated."""
        export = export_pvoutput()
        assert export is not None

    def test_instance_type(self):
        """Test that instance is correct type."""
        export = export_pvoutput()
        assert isinstance(export, export_pvoutput)

    def test_initial_attributes(self):
        """Test that initial attributes are set correctly."""
        export = export_pvoutput()
        assert export.url_base == "https://pvoutput.org/service/r2/"
        assert export.url_addbatchstatus == "https://pvoutput.org/service/r2/addbatchstatus.jsp"
        assert export.url_jointeam == "https://pvoutput.org/service/r2/jointeam.jsp"
        assert export.url_leaveteam == "https://pvoutput.org/service/r2/leaveteam.jsp"
        assert export.url_getsystem == "https://pvoutput.org/service/r2/getsystem.jsp"
        assert export.tid == '1618'
        assert export.status_interval == 5


class TestPVOutputHeaders:
    """Test PVOutput headers property."""

    def test_headers_property(self):
        """Test that headers property returns correct format."""
        export = export_pvoutput()
        export.pvoutput_config = {
            'api': 'test_api_key',
            'sid': 'test_system_id'
        }

        headers = export.headers

        assert headers['X-Pvoutput-Apikey'] == 'test_api_key'
        assert headers['X-Pvoutput-SystemId'] == 'test_system_id'
        assert headers['Content-Type'] == 'application/x-www-form-urlencoded'
        assert headers['cache-control'] == 'no-cache'


class TestPVOutputConfiguration:
    """Test PVOutput export configuration."""

    def test_configure_with_valid_credentials(self, mocker):
        """Test configure() with valid API credentials."""
        export = export_pvoutput()

        # Mock requests.post
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "System Name,0,0,0,0,0,0,0,0,0,0,0,0,0,0,5;0;1618"
        mock_response.content = b"System response"
        mock_post = mocker.patch('exports.pvoutput.requests.post', return_value=mock_response)

        # Mock inverter
        mock_inverter = Mock()
        mock_inverter.validateRegister.return_value = True

        # Config
        config = {
            'api': 'test_api',
            'sid': 'test_sid',
            'parameters': [
                {'register': 'total_active_power', 'name': 'v2'}
            ]
        }

        # Configure
        result = export.configure(config, mock_inverter)

        # Verify
        assert result is True
        assert export.pvoutput_config['api'] == 'test_api'
        assert export.pvoutput_config['sid'] == 'test_sid'
        assert export.pvoutput_config['join_team'] is True  # Default
        assert export.status_interval == 5
        mock_post.assert_called()

    def test_configure_with_custom_settings(self, mocker):
        """Test configure() with custom settings."""
        export = export_pvoutput()

        # Mock requests.post
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "System Name,0,0,0,0,0,0,0,0,0,0,0,0,0,0,10;0;1618"
        mock_response.content = b"System response"
        mocker.patch('exports.pvoutput.requests.post', return_value=mock_response)

        # Mock inverter
        mock_inverter = Mock()
        mock_inverter.validateRegister.return_value = True

        # Custom config
        config = {
            'api': 'test_api',
            'sid': 'test_sid',
            'join_team': False,
            'rate_limit': 120,
            'cumulative_flag': 1,
            'batch_points': 3,
            'parameters': [
                {'register': 'total_active_power', 'name': 'v2'}
            ]
        }

        # Configure
        result = export.configure(config, mock_inverter)

        # Verify custom settings
        assert result is True
        assert export.pvoutput_config['join_team'] is False
        assert export.pvoutput_config['rate_limit'] == 120
        assert export.pvoutput_config['cumulative_flag'] == 1
        assert export.pvoutput_config['batch_points'] == 3

    def test_configure_with_invalid_register(self, mocker):
        """Test configure() fails with invalid register."""
        export = export_pvoutput()

        # Mock inverter - register is invalid
        mock_inverter = Mock()
        mock_inverter.validateRegister.return_value = False

        # Config
        config = {
            'api': 'test_api',
            'sid': 'test_sid',
            'parameters': [
                {'register': 'invalid_register', 'name': 'v2'}
            ]
        }

        # Should fail
        result = export.configure(config, mock_inverter)

        assert result is False

    def test_configure_handles_api_error(self, mocker):
        """Test configure() handles PVOutput API errors."""
        export = export_pvoutput()

        # Mock requests.post to raise exception
        mocker.patch('exports.pvoutput.requests.post', side_effect=Exception("API error"))

        # Mock inverter
        mock_inverter = Mock()
        mock_inverter.validateRegister.return_value = True

        # Config
        config = {
            'api': 'test_api',
            'sid': 'test_sid',
            'parameters': [
                {'register': 'total_active_power', 'name': 'v2'}
            ]
        }

        # Should handle error
        result = export.configure(config, mock_inverter)

        assert result is False

    def test_configure_joins_team_when_not_member(self, mocker):
        """Test configure() joins team when not already a member."""
        export = export_pvoutput()

        # Mock requests.post - not a team member
        mock_response1 = Mock()
        mock_response1.status_code = 200
        mock_response1.text = "System Name,0,0,0,0,0,0,0,0,0,0,0,0,0,0,5;0;9999"  # Different team
        mock_response1.content = b"System response"

        mock_response2 = Mock()
        mock_response2.status_code = 200
        mock_response2.content = b"Joined team"

        mock_post = mocker.patch('exports.pvoutput.requests.post')
        mock_post.side_effect = [mock_response1, mock_response2]

        # Mock inverter
        mock_inverter = Mock()
        mock_inverter.validateRegister.return_value = True

        # Config with join_team=True
        config = {
            'api': 'test_api',
            'sid': 'test_sid',
            'join_team': True,
            'parameters': [
                {'register': 'total_active_power', 'name': 'v2'}
            ]
        }

        # Configure
        result = export.configure(config, mock_inverter)

        # Verify team join was called
        assert result is True
        assert mock_post.call_count == 2
        # Second call should be join team
        assert 'jointeam.jsp' in str(mock_post.call_args_list[1])

    def test_configure_leaves_team_when_member_and_disabled(self, mocker):
        """Test configure() leaves team when member but join_team=False."""
        export = export_pvoutput()

        # Mock requests.post - is a team member
        mock_response1 = Mock()
        mock_response1.status_code = 200
        mock_response1.text = "System Name,0,0,0,0,0,0,0,0,0,0,0,0,0,0,5;0;1618"  # Member of team 1618
        mock_response1.content = b"System response"

        mock_response2 = Mock()
        mock_response2.status_code = 200
        mock_response2.content = b"Left team"

        mock_post = mocker.patch('exports.pvoutput.requests.post')
        mock_post.side_effect = [mock_response1, mock_response2]

        # Mock inverter
        mock_inverter = Mock()
        mock_inverter.validateRegister.return_value = True

        # Config with join_team=False
        config = {
            'api': 'test_api',
            'sid': 'test_sid',
            'join_team': False,
            'parameters': [
                {'register': 'total_active_power', 'name': 'v2'}
            ]
        }

        # Configure
        result = export.configure(config, mock_inverter)

        # Verify team leave was called
        assert result is True
        assert mock_post.call_count == 2
        # Second call should be leave team
        assert 'leaveteam.jsp' in str(mock_post.call_args_list[1])


class TestPVOutputDataCollection:
    """Test PVOutput data collection."""

    def test_collect_data_success(self, mocker):
        """Test successful data collection."""
        export = export_pvoutput()
        export.pvoutput_config = {'cumulative_flag': 0}
        export.pvoutput_parameters = [
            {'register': 'total_active_power', 'name': 'v2'}
        ]
        export.collected_data = {}

        # Mock inverter
        mock_inverter = Mock()
        mock_inverter.validateLatestScrape.return_value = True
        mock_inverter.getRegisterValue.return_value = 3500

        # Collect data
        result = export.collect_data(mock_inverter)

        # Verify
        assert result is True
        assert export.collected_data['v2'] == 3500
        assert export.collected_data['count'] == 1

    def test_collect_data_with_multiple(self, mocker):
        """Test data collection with multiple parameter."""
        export = export_pvoutput()
        export.pvoutput_config = {'cumulative_flag': 0}
        export.pvoutput_parameters = [
            {'register': 'battery_voltage', 'name': 'v6', 'multiple': 10}
        ]
        export.collected_data = {}

        # Mock inverter
        mock_inverter = Mock()
        mock_inverter.validateLatestScrape.return_value = True
        mock_inverter.getRegisterValue.return_value = 52.4

        # Collect data
        result = export.collect_data(mock_inverter)

        # Verify value was multiplied
        assert result is True
        assert export.collected_data['v6'] == 524.0

    def test_collect_data_averages_values(self):
        """Test that collect_data averages multiple readings."""
        export = export_pvoutput()
        export.pvoutput_config = {'cumulative_flag': 0}
        export.pvoutput_parameters = [
            {'register': 'total_active_power', 'name': 'v2'}
        ]
        export.collected_data = {}

        # Mock inverter
        mock_inverter = Mock()
        mock_inverter.validateLatestScrape.return_value = True

        # First collection - value 3000
        mock_inverter.getRegisterValue.return_value = 3000
        export.collect_data(mock_inverter)
        assert export.collected_data['v2'] == 3000
        assert export.collected_data['count'] == 1

        # Second collection - value 4000
        mock_inverter.getRegisterValue.return_value = 4000
        export.collect_data(mock_inverter)
        assert export.collected_data['v2'] == 7000  # Sum for averaging later
        assert export.collected_data['count'] == 2

    def test_collect_data_cumulative_v1(self):
        """Test data collection with cumulative flag for v1."""
        export = export_pvoutput()
        export.pvoutput_config = {'cumulative_flag': 1}  # Both v1 and v3 cumulative
        export.pvoutput_parameters = [
            {'register': 'total_energy', 'name': 'v1'}
        ]
        export.collected_data = {}

        # Mock inverter
        mock_inverter = Mock()
        mock_inverter.validateLatestScrape.return_value = True

        # First reading
        mock_inverter.getRegisterValue.return_value = 10000
        export.collect_data(mock_inverter)
        assert export.collected_data['v1'] == 10000

        # Second reading - should replace, not add
        mock_inverter.getRegisterValue.return_value = 12000
        export.collect_data(mock_inverter)
        assert export.collected_data['v1'] == 12000  # Replaced, not summed

    def test_collect_data_missing_timestamp(self):
        """Test collect_data fails when timestamp missing."""
        export = export_pvoutput()
        export.pvoutput_parameters = []

        # Mock inverter - timestamp not available
        mock_inverter = Mock()
        mock_inverter.validateLatestScrape.return_value = False

        # Should fail
        result = export.collect_data(mock_inverter)

        assert result is False

    def test_collect_data_missing_register(self):
        """Test collect_data fails when required register missing."""
        export = export_pvoutput()
        export.pvoutput_parameters = [
            {'register': 'total_active_power', 'name': 'v2'}
        ]

        # Mock inverter - timestamp OK, but register missing
        mock_inverter = Mock()
        mock_inverter.validateLatestScrape.side_effect = [True, False]

        # Should fail
        result = export.collect_data(mock_inverter)

        assert result is False


class TestPVOutputPublishing:
    """Test PVOutput publishing functionality."""

    def test_publish_before_interval(self, mocker):
        """Test that publish() waits for interval before uploading."""
        export = export_pvoutput()
        export.pvoutput_config = {'cumulative_flag': 0}
        export.pvoutput_parameters = [
            {'register': 'total_active_power', 'name': 'v2'}
        ]
        export.collected_data = {}
        export.batch_data = []
        export.batch_count = 0
        export.status_interval = 5
        export.last_publish = time.time()  # Just published

        # Mock inverter
        mock_inverter = Mock()
        mock_inverter.validateLatestScrape.return_value = True
        mock_inverter.getRegisterValue.return_value = 3500

        # Publish - should collect but not upload yet
        export.publish(mock_inverter)

        # Data should be collected
        assert export.collected_data['v2'] == 3500
        # But not yet added to batch
        assert len(export.batch_data) == 0

    def test_publish_adds_to_batch(self, mocker):
        """Test that publish() adds data to batch."""
        export = export_pvoutput()
        export.pvoutput_config = {
            'cumulative_flag': 0,
            'batch_points': 2  # Need 2 points before upload
        }
        export.pvoutput_parameters = [
            {'register': 'total_active_power', 'name': 'v2'}
        ]
        export.collected_data = {}
        export.batch_data = []
        export.batch_count = 0
        export.status_interval = 5
        export.last_publish = time.time() - 600  # 10 minutes ago

        # Mock inverter
        mock_inverter = Mock()
        mock_inverter.validateLatestScrape.return_value = True
        mock_inverter.getRegisterValue.side_effect = [
            3500,  # collect_data: total_active_power
            '2025-10-19 14:30:00'  # publish: timestamp
        ]

        # Publish
        export.publish(mock_inverter)

        # Verify data was added to batch
        assert len(export.batch_data) == 1
        assert '20251019' in export.batch_data[0]  # Date
        assert '14:30' in export.batch_data[0]  # Time
        assert '3500' in export.batch_data[0]  # Value

    def test_publish_limits_batch_to_30(self, mocker):
        """Test that publish() limits batch data to 30 points."""
        export = export_pvoutput()
        export.pvoutput_config = {'cumulative_flag': 0, 'batch_points': 999}
        export.pvoutput_parameters = [{'register': 'power', 'name': 'v2'}]
        export.collected_data = {}
        export.batch_data = [f"20251019,14:{i:02d},,3500,,,,,,,,,," for i in range(1, 31)]  # 30 points
        export.batch_count = 0
        export.status_interval = 5
        export.last_publish = time.time() - 600

        # Mock inverter
        mock_inverter = Mock()
        mock_inverter.validateLatestScrape.return_value = True
        mock_inverter.getRegisterValue.side_effect = [
            3500,  # collect_data: power
            '2025-10-19 14:30:00'  # publish: timestamp
        ]

        # Publish - will add 31st point
        export.publish(mock_inverter)

        # Should remove oldest and still be at 30
        assert len(export.batch_data) == 30
        # Newest data should be present
        assert '20251019,14:30' in export.batch_data[-1]

    def test_publish_handles_upload_error(self, mocker):
        """Test that publish() handles upload errors gracefully."""
        export = export_pvoutput()
        export.pvoutput_config = {'cumulative_flag': 0, 'batch_points': 1}
        export.pvoutput_parameters = [{'register': 'power', 'name': 'v2'}]
        export.collected_data = {}
        export.batch_data = []
        export.batch_count = 0
        export.status_interval = 5
        export.last_publish = time.time() - 600

        # Mock inverter
        mock_inverter = Mock()
        mock_inverter.validateLatestScrape.return_value = True
        mock_inverter.getRegisterValue.side_effect = [
            3500,  # collect_data: power
            '2025-10-19 14:30:00'  # publish: timestamp
        ]

        # Mock requests.post to raise exception
        mocker.patch('exports.pvoutput.requests.post', side_effect=Exception("Network error"))

        # Publish - should handle error
        export.publish(mock_inverter)

        # Should not raise exception

    def test_batch_count_increments(self, mocker):
        """Test that batch_count increments when interval reached."""
        export = export_pvoutput()
        export.pvoutput_config = {'cumulative_flag': 0, 'batch_points': 5}
        export.pvoutput_parameters = [{'register': 'power', 'name': 'v2'}]
        export.collected_data = {}
        export.batch_data = []
        export.batch_count = 0
        export.status_interval = 5
        export.last_publish = time.time() - 600

        # Mock inverter
        mock_inverter = Mock()
        mock_inverter.validateLatestScrape.return_value = True
        mock_inverter.getRegisterValue.side_effect = [
            3500,  # collect_data: power
            '2025-10-19 14:30:00'  # publish: timestamp
        ]

        # Publish
        export.publish(mock_inverter)

        # Batch count should have incremented
        assert export.batch_count == 1
        # Data should be in batch
        assert len(export.batch_data) == 1
