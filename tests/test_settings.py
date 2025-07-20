# -*- coding: utf-8 -*-
"""Unit tests for Settings module.

This module provides comprehensive tests for the refactored Settings.py
module, testing all classes and their methods.
"""

import json
import os
import tempfile
import unittest
from unittest.mock import Mock, patch, MagicMock, mock_open

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'Revit_Plugin', 'Daylight-Factor'))

# Mock the CLR and Revit modules before importing Settings
sys.modules['clr'] = MagicMock()
sys.modules['RhinoInside'] = MagicMock()
sys.modules['RhinoInside.Revit'] = MagicMock()
sys.modules['Autodesk'] = MagicMock()
sys.modules['Autodesk.Revit'] = MagicMock()
sys.modules['Autodesk.Revit.DB'] = MagicMock()
sys.modules['System'] = MagicMock()
sys.modules['System.Windows'] = MagicMock()
sys.modules['System.Windows.Markup'] = MagicMock()
sys.modules['System.IO'] = MagicMock()
sys.modules['System.Diagnostics'] = MagicMock()

# Now import the Settings module
from Settings import (
    DaylightSettings, RevitApiHelper, WpfControlFinder, 
    SettingsWindow, SettingsApplication
)


class TestDaylightSettings(unittest.TestCase):
    """Test cases for DaylightSettings class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.settings = DaylightSettings()
    
    def test_init(self):
        """Test DaylightSettings initialization."""
        self.assertIsInstance(self.settings, DaylightSettings)
        self.assertTrue(hasattr(self.settings, 'settings_file_path'))
        self.assertTrue(hasattr(self.settings, 'xaml_file_path'))
    
    def test_constants(self):
        """Test class constants."""
        self.assertEqual(DaylightSettings.SETTINGS_FILENAME, "settings_daylight.json")
        self.assertEqual(DaylightSettings.XAML_FILENAME, "SettingsDaylightWindow.xaml")
    
    @patch('os.path.abspath')
    @patch('os.path.dirname')
    @patch('os.path.join')
    def test_get_settings_file_path_success(self, mock_join, mock_dirname, mock_abspath):
        """Test successful settings file path calculation."""
        mock_abspath.return_value = '/test/path/Settings.py'
        mock_dirname.side_effect = ['/test/path', '/test']
        mock_join.return_value = '/test/settings_daylight.json'
        
        settings = DaylightSettings()
        
        mock_abspath.assert_called_once()
        self.assertEqual(mock_dirname.call_count, 2)
        mock_join.assert_called_with('/test', 'settings_daylight.json')
    
    @patch('os.path.abspath', side_effect=NameError("__file__ not defined"))
    @patch('os.getcwd')
    @patch('os.path.dirname')
    @patch('os.path.join')
    def test_get_settings_file_path_fallback(self, mock_join, mock_dirname, mock_getcwd, mock_abspath):
        """Test fallback when __file__ is not available."""
        mock_getcwd.return_value = '/fallback/path'
        mock_dirname.return_value = '/fallback'
        mock_join.return_value = '/fallback/settings_daylight.json'
        
        settings = DaylightSettings()
        
        mock_getcwd.assert_called_once()
        mock_dirname.assert_called_with('/fallback/path')
        mock_join.assert_called_with('/fallback', 'settings_daylight.json')


class TestRevitApiHelper(unittest.TestCase):
    """Test cases for RevitApiHelper class."""
    
    @patch('Settings.Revit')
    def test_get_active_document(self, mock_revit):
        """Test getting active Revit document."""
        mock_doc = Mock()
        mock_revit.ActiveDBDocument = mock_doc
        
        result = RevitApiHelper.get_active_document()
        
        self.assertEqual(result, mock_doc)
    
    @patch('Settings.UnitUtils')
    @patch('Settings.MM', 'test_mm_unit')
    def test_feet_to_mm(self, mock_unit_utils):
        """Test feet to millimeters conversion."""
        mock_unit_utils.ConvertFromInternalUnits.return_value = 3048.0
        
        result = RevitApiHelper.feet_to_mm(10.0)
        
        mock_unit_utils.ConvertFromInternalUnits.assert_called_once_with(10.0, 'test_mm_unit')
        self.assertEqual(result, 3048.0)


class TestWpfControlFinder(unittest.TestCase):
    """Test cases for WpfControlFinder class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.finder = WpfControlFinder()
    
    def test_find_child_by_name_direct_match(self):
        """Test finding control with direct name match."""
        mock_parent = Mock()
        mock_parent.Name = "TestControl"
        
        result = WpfControlFinder.find_child_by_name(mock_parent, "TestControl")
        
        self.assertEqual(result, mock_parent)
    
    def test_find_child_by_name_not_found(self):
        """Test when control is not found."""
        mock_parent = Mock()
        mock_parent.Name = "OtherControl"
        # Mock the hasattr calls to return False for all container properties
        mock_parent.Children = None
        mock_parent.Content = None
        mock_parent.Child = None
        mock_parent.Items = None
        
        result = WpfControlFinder.find_child_by_name(mock_parent, "TestControl")
        
        self.assertIsNone(result)
    
    def test_find_child_by_name_in_children(self):
        """Test finding control in Children container."""
        mock_child = Mock()
        mock_child.Name = "TestControl"
        
        mock_parent = Mock()
        mock_parent.Name = "Parent"
        mock_parent.Children = [mock_child]
        mock_parent.Content = None
        mock_parent.Child = None
        mock_parent.Items = None
        
        result = WpfControlFinder.find_child_by_name(mock_parent, "TestControl")
        
        self.assertEqual(result, mock_child)
    
    def test_search_in_container_iteration_error(self):
        """Test _search_in_container with iteration error."""
        mock_container = Mock()
        mock_container.__iter__ = Mock(side_effect=TypeError("Not iterable"))
        mock_container.Name = "TestControl"
        
        result = WpfControlFinder._search_in_container(mock_container, "TestControl")
        
        self.assertEqual(result, mock_container)


class TestSettingsWindow(unittest.TestCase):
    """Test cases for SettingsWindow class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock all the required dependencies
        self.mock_xaml_source = "/test/path/test.xaml"
        self.mock_revit_doc = Mock()
        
        # Mock the Window base class
        with patch('Settings.Window.__init__'):
            with patch.object(SettingsWindow, '_load_xaml'):
                with patch.object(SettingsWindow, '_initialize_controls'):
                    with patch.object(SettingsWindow, '_attach_event_handlers'):
                        with patch.object(SettingsWindow, '_load_settings'):
                            self.window = SettingsWindow(self.mock_xaml_source, self.mock_revit_doc)
    
    def test_init_calls_required_methods(self):
        """Test that __init__ calls all required setup methods."""
        with patch('Settings.Window.__init__') as mock_window_init:
            with patch.object(SettingsWindow, '_load_xaml') as mock_load_xaml:
                with patch.object(SettingsWindow, '_initialize_controls') as mock_init_controls:
                    with patch.object(SettingsWindow, '_attach_event_handlers') as mock_attach_events:
                        with patch.object(SettingsWindow, '_load_settings') as mock_load_settings:
                            
                            window = SettingsWindow(self.mock_xaml_source, self.mock_revit_doc)
                            
                            mock_window_init.assert_called_once()
                            mock_load_xaml.assert_called_once_with(self.mock_xaml_source)
                            mock_init_controls.assert_called_once()
                            mock_attach_events.assert_called_once()
                            mock_load_settings.assert_called_once()
    
    @patch('Settings.FileStream')
    @patch('Settings.XamlReader')
    def test_load_xaml(self, mock_xaml_reader, mock_file_stream):
        """Test XAML loading method."""
        mock_stream = Mock()
        mock_file_stream.return_value = mock_stream
        
        mock_xaml_window = Mock()
        mock_xaml_window.Content = "test_content"
        mock_xaml_window.Title = "test_title"
        mock_xaml_window.Width = 400
        mock_xaml_window.Height = 300
        mock_xaml_reader.Load.return_value = mock_xaml_window
        
        self.window._load_xaml(self.mock_xaml_source)
        
        mock_file_stream.assert_called_once()
        mock_xaml_reader.Load.assert_called_once_with(mock_stream)
        mock_stream.Close.assert_called_once()
        
        self.assertEqual(self.window.Content, "test_content")
        self.assertEqual(self.window.Title, "test_title")
        self.assertEqual(self.window.Width, 400)
        self.assertEqual(self.window.Height, 300)
    
    def test_collect_ui_data_missing_level(self):
        """Test _collect_ui_data when no level is selected."""
        self.window.ComboBoxLevels = Mock()
        self.window.ComboBoxLevels.SelectedItem = None
        
        with patch('Settings.MessageBox') as mock_message_box:
            result = self.window._collect_ui_data()
            
            self.assertIsNone(result)
            mock_message_box.Show.assert_called_once()
    
    def test_collect_ui_data_success(self):
        """Test successful UI data collection."""
        # Set up mock controls
        self.window.ComboBoxLevels = Mock()
        self.window.RadioButtonTrue = Mock()
        self.window.TextBoxTransmission = Mock()
        self.window.ComboBoxExecutionMode = Mock()
        self.window.RadioWriteYes = Mock()
        
        mock_level = Mock()
        self.window.ComboBoxLevels.SelectedItem = mock_level
        self.window.RadioButtonTrue.IsChecked = True
        self.window.TextBoxTransmission.Text = "75"
        self.window.ComboBoxExecutionMode.SelectedIndex = 1
        self.window.RadioWriteYes.IsChecked = False
        
        result = self.window._collect_ui_data()
        
        expected = {
            'is_multilayer': True,
            'transmission_str': "75",
            'exec_mode': 'local',
            'write_results': False,
            'selected_level': mock_level
        }
        
        self.assertEqual(result, expected)
    
    def test_validate_inputs_success(self):
        """Test successful input validation."""
        ui_data = {'transmission_str': '75'}
        
        result = self.window._validate_inputs(ui_data)
        
        self.assertTrue(result)
        self.assertEqual(ui_data['transmission_value'], 75)
    
    def test_validate_inputs_invalid_value(self):
        """Test input validation with invalid value."""
        ui_data = {'transmission_str': '150'}
        
        with patch('Settings.MessageBox') as mock_message_box:
            result = self.window._validate_inputs(ui_data)
            
            self.assertFalse(result)
            mock_message_box.Show.assert_called_once()
    
    def test_validate_inputs_non_integer(self):
        """Test input validation with non-integer value."""
        ui_data = {'transmission_str': 'invalid'}
        
        with patch('Settings.MessageBox') as mock_message_box:
            result = self.window._validate_inputs(ui_data)
            
            self.assertFalse(result)
            mock_message_box.Show.assert_called_once()
    
    @patch('Settings.RevitApiHelper.feet_to_mm')
    def test_prepare_settings_data(self, mock_feet_to_mm):
        """Test settings data preparation."""
        mock_feet_to_mm.return_value = 3048.0
        
        mock_level = Mock()
        mock_level.Elevation = 10.0
        
        ui_data = {
            'is_multilayer': True,
            'transmission_value': 80,
            'exec_mode': 'local',
            'write_results': False,
            'selected_level': mock_level
        }
        
        result = self.window._prepare_settings_data(ui_data)
        
        expected = {
            'multilayer_wall': True,
            'transmission_value': 80,
            'level_elevation': 3048,
            'execution_mode': 'local',
            'write_results': False
        }
        
        self.assertEqual(result, expected)
        mock_feet_to_mm.assert_called_once_with(10.0)


class TestSettingsApplication(unittest.TestCase):
    """Test cases for SettingsApplication class."""
    
    @patch('Settings.RevitApiHelper.get_active_document')
    def test_init(self, mock_get_doc):
        """Test SettingsApplication initialization."""
        mock_doc = Mock()
        mock_get_doc.return_value = mock_doc
        
        app = SettingsApplication()
        
        self.assertIsInstance(app.settings, DaylightSettings)
        self.assertEqual(app.revit_doc, mock_doc)
    
    @patch('Settings.SettingsWindow')
    @patch.object(SettingsApplication, '_validate_xaml_file')
    def test_run_success(self, mock_validate, mock_settings_window):
        """Test successful application run."""
        mock_validate.return_value = True
        mock_window_instance = Mock()
        mock_settings_window.return_value = mock_window_instance
        
        app = SettingsApplication()
        app.run()
        
        mock_validate.assert_called_once()
        mock_settings_window.assert_called_once_with(
            app.settings.xaml_file_path, 
            app.revit_doc
        )
        mock_window_instance.ShowDialog.assert_called_once()
    
    @patch.object(SettingsApplication, '_validate_xaml_file')
    def test_run_validation_failure(self, mock_validate):
        """Test application run with validation failure."""
        mock_validate.return_value = False
        
        app = SettingsApplication()
        
        with patch('Settings.SettingsWindow') as mock_settings_window:
            app.run()
            
            mock_validate.assert_called_once()
            mock_settings_window.assert_not_called()
    
    @patch('os.path.isfile')
    def test_validate_xaml_file_exists(self, mock_isfile):
        """Test XAML file validation when file exists."""
        mock_isfile.return_value = True
        
        app = SettingsApplication()
        result = app._validate_xaml_file()
        
        self.assertTrue(result)
        mock_isfile.assert_called_once_with(app.settings.xaml_file_path)
    
    @patch('os.path.isfile')
    def test_validate_xaml_file_missing(self, mock_isfile):
        """Test XAML file validation when file is missing."""
        mock_isfile.return_value = False
        
        app = SettingsApplication()
        
        with patch('Settings.MessageBox') as mock_message_box:
            result = app._validate_xaml_file()
            
            self.assertFalse(result)
            mock_isfile.assert_called_once_with(app.settings.xaml_file_path)
            mock_message_box.Show.assert_called_once()


class TestIntegration(unittest.TestCase):
    """Integration tests for the Settings module."""
    
    def test_json_settings_roundtrip(self):
        """Test saving and loading settings to/from JSON."""
        test_data = {
            'multilayer_wall': True,
            'transmission_value': 85,
            'level_elevation': 3000,
            'execution_mode': 'local',
            'write_results': False
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_data, f, indent=4, sort_keys=True)
            temp_path = f.name
        
        try:
            # Read back the data
            with open(temp_path, 'r') as f:
                loaded_data = json.load(f)
            
            self.assertEqual(loaded_data, test_data)
        finally:
            os.unlink(temp_path)
    
    @patch('Settings.codecs.open', new_callable=mock_open, read_data='{"test": "data"}')
    @patch('os.path.isfile')
    def test_settings_file_loading(self, mock_isfile, mock_file):
        """Test settings file loading integration."""
        mock_isfile.return_value = True
        
        settings = DaylightSettings()
        
        # This would be called by SettingsWindow._load_settings_from_file
        with patch('json.load') as mock_json_load:
            mock_json_load.return_value = {"test": "data"}
            
            # Simulate the file loading
            with settings.settings_file_path as path:
                pass
            
            # Verify the mock was set up correctly
            self.assertTrue(mock_isfile.called)


if __name__ == '__main__':
    unittest.main()