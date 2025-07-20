# -*- coding: utf-8 -*-
"""Pytest configuration and shared fixtures."""

import sys
import os
from unittest.mock import MagicMock

# Add the source directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'Revit_Plugin', 'Daylight-Factor'))

# Mock external dependencies that are not available in test environment
def mock_external_modules():
    """Mock external modules that are not available during testing."""
    modules_to_mock = [
        'clr',
        'RhinoInside',
        'RhinoInside.Revit',
        'Autodesk',
        'Autodesk.Revit',
        'Autodesk.Revit.DB',
        'System',
        'System.Windows',
        'System.Windows.Markup',
        'System.IO',
        'System.Diagnostics'
    ]
    
    for module in modules_to_mock:
        if module not in sys.modules:
            sys.modules[module] = MagicMock()

# Apply mocks before importing any modules
mock_external_modules()