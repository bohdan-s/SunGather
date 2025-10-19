"""
Unit tests for exports/hassio.py

IMPORTANT NOTE: As of 2025-10-19, hassio.py is nearly identical to pvoutput.py
but has a critical bug on line 12-16: it defines self.api_base but then tries to
use self.url_base (which is undefined), causing AttributeError on instantiation.

These tests document the current broken state of the code. When hassio.py is fixed,
these tests should be updated to match the corrected behavior.

The code also uses pvoutput_config and pvoutput_parameters internally even though
it's supposed to be for Home Assistant.

HOW THIS BUG MANIFESTS IN PRODUCTION:
When sungather.py loads exports, it calls:
    export_instance = getattr(export_load, "export_hassio")()  # Line 142
This instantiates the class (calls __init__), which triggers the AttributeError.
The exception is caught by the generic exception handler (line 151-153) and logged as:
    "Failed loading export hassio: 'export_hassio' object has no attribute 'url_base'"
The export is then skipped and sungather.py continues running with other exports.
"""

import pytest
from exports.hassio import export_hassio


class TestHassioBrokenState:
    """Test that documents the broken state of hassio.py."""

    def test_instantiation_fails_with_attribute_error(self):
        """Test that Hassio export fails to instantiate due to bug.

        The __init__ method defines self.api_base on line 12 but then
        tries to use self.url_base on lines 13-16, causing AttributeError.

        This test will PASS as long as the bug exists. When the bug is fixed,
        this test will fail and should be replaced with proper functional tests
        similar to test_pvoutput.py.
        """
        with pytest.raises(AttributeError, match="'export_hassio' object has no attribute 'url_base'"):
            export = export_hassio()
