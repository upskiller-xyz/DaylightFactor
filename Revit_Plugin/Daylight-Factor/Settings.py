# -*- coding: utf-8 -*-
"""Settings window for Daylight Prediction using standard WPF.

This module provides a settings interface for the Daylight Factor plugin,
allowing users to configure prediction parameters through a WPF dialog.
"""

import codecs
import json
import os
import System.Diagnostics as diag

import clr

clr.AddReference("RhinoInside.Revit")
clr.AddReference("PresentationFramework")
clr.AddReference("WindowsBase")
clr.AddReference("PresentationCore")

from RhinoInside.Revit import Revit
from Autodesk.Revit.DB import FilteredElementCollector, Level, UnitUtils
from System.Windows import Window, MessageBox
from System.Windows.Markup import XamlReader
from System.IO import FileStream, FileMode, FileAccess, FileShare


try:
    from Autodesk.Revit.DB import UnitTypeId
    MM = UnitTypeId.Millimeters
except ImportError:
    from Autodesk.Revit.DB import DisplayUnitType
    MM = DisplayUnitType.DUT_MILLIMETERS


class DaylightSettings:
    """Configuration settings for daylight analysis."""

    SETTINGS_FILENAME = "settings_daylight.json"
    XAML_FILENAME = "SettingsDaylightWindow.xaml"

    def __init__(self):
        self.settings_file_path = self._get_settings_file_path()
        self.xaml_file_path = self._get_xaml_file_path()

    def _get_settings_file_path(self):
        """Get the path to the settings file."""
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            parent_dir = os.path.dirname(script_dir)
            return os.path.join(parent_dir, self.SETTINGS_FILENAME)
        except NameError:
            print("WARNING: Could not determine script path. "
                  "Using current working directory.")
            script_dir = os.getcwd()
            parent_dir = os.path.dirname(script_dir)
            return os.path.join(parent_dir, self.SETTINGS_FILENAME)

    def _get_xaml_file_path(self):
        """Get the path to the XAML file."""
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            return os.path.join(script_dir, self.XAML_FILENAME)
        except NameError:
            script_dir = os.getcwd()
            return os.path.join(script_dir, self.XAML_FILENAME)


class RevitApiHelper:
    """Helper class for Revit API operations."""

    @staticmethod
    def get_active_document():
        """Get the active Revit document."""
        return Revit.ActiveDBDocument

    @staticmethod
    def feet_to_mm(value_ft):
        """Convert Revit-internal feet to millimetres."""
        return UnitUtils.ConvertFromInternalUnits(value_ft, MM)

class WpfControlFinder:
    """Helper class for finding WPF controls by name."""

    @staticmethod
    def find_child_by_name(parent, name):
        """Recursively search for a child element by x:Name."""
        if hasattr(parent, 'Name') and parent.Name == name:
            return parent

        search_properties = ['Children', 'Content', 'Child', 'Items']

        for prop in search_properties:
            if hasattr(parent, prop):
                container = getattr(parent, prop)
                if container is not None and container != parent:
                    result = WpfControlFinder._search_in_container(
                        container, name
                    )
                    if result is not None:
                        return result

        return None

    @staticmethod
    def _search_in_container(container, name):
        """Search for a control in a container."""
        try:
            for item in container:
                result = WpfControlFinder.find_child_by_name(item, name)
                if result is not None:
                    return result
        except (TypeError, AttributeError):
            return WpfControlFinder.find_child_by_name(container, name)

        return None


class SettingsWindow(Window):
    """Settings window for Daylight Prediction using standard WPF.

    Loads layout from XAML and handles loading/saving settings.
    """

    def __init__(self, xaml_source, revit_doc):
        """Initialize the settings window.

        Args:
            xaml_source: Path to the XAML file
            revit_doc: Active Revit document
        """
        Window.__init__(self)
        self.revit_doc = revit_doc
        self.settings = DaylightSettings()

        self._load_xaml(xaml_source)
        self._initialize_controls()
        self._attach_event_handlers()
        self._load_settings()

    def _load_xaml(self, xaml_source):
        """Load XAML window definition."""
        fs = FileStream(
            xaml_source, FileMode.Open,
            FileAccess.Read, FileShare.ReadWrite
        )
        try:
            window = XamlReader.Load(fs)
            self.Content = window.Content
            self.Title = window.Title
            self.Width = window.Width
            self.Height = window.Height
        finally:
            fs.Close()

    def _initialize_controls(self):
        """Initialize WPF controls by finding them in the XAML."""
        finder = WpfControlFinder()

        control_names = [
            "SaveButton", "ComboBoxLevels", "RadioButtonTrue",
            "RadioButtonFalse", "TextBoxTransmission", "HelpButton",
            "ComboBoxExecutionMode", "RadioWriteYes", "RadioWriteNo"
        ]

        for control_name in control_names:
            control = finder.find_child_by_name(self.Content, control_name)
            setattr(self, control_name, control)

    def _attach_event_handlers(self):
        """Attach event handlers to UI controls."""
        if self.SaveButton:
            self.SaveButton.Click += self.save_button_click
        if self.HelpButton:
            self.HelpButton.Click += self.help_button_click

    def _load_settings(self):
        """Load settings from JSON file and update UI elements."""
        try:
            self._populate_levels()

            if os.path.isfile(self.settings.settings_file_path):
                data = self._load_settings_from_file()
            else:
                data = self._get_default_settings()

            self._apply_settings_to_ui(data)

        except Exception as e:
            print("ERROR loading settings: {}".format(e))
            MessageBox.Show(
                "Error loading settings file or levels.\n"
                "Defaults will be used.",
                "Load Error"
            )
            self._apply_default_ui_values()

    def _populate_levels(self):
        """Populate the levels dropdown from Revit model."""
        collector = FilteredElementCollector(self.revit_doc)
        self.levels = [lvl for lvl in collector.OfClass(Level)]
        self.ComboBoxLevels.ItemsSource = self.levels

    def _load_settings_from_file(self):
        """Load settings data from JSON file."""
        with codecs.open(
            self.settings.settings_file_path, 'r', encoding='utf-8'
        ) as f:
            return json.load(f)

    def _get_default_settings(self):
        """Get default settings values."""
        return {
            'multilayer_wall': False,
            'transmission_value': 70,
            'level_elevation': None,
            'execution_mode': 'web',
            'write_results': True
        }

    def _apply_settings_to_ui(self, data):
        """Apply loaded settings to UI controls."""
        is_multilayer = bool(data.get('multilayer_wall', False))
        transmission_val = str(data.get('transmission_value', 70))
        level_elevation = data.get('level_elevation', None)
        exec_mode = data.get('execution_mode', 'web')
        write_results = bool(data.get('write_results', True))

        self.RadioButtonTrue.IsChecked = is_multilayer
        self.RadioButtonFalse.IsChecked = not is_multilayer
        self.TextBoxTransmission.Text = transmission_val

        self.ComboBoxExecutionMode.SelectedIndex = (
            1 if exec_mode == 'local' else 0
        )
        self.RadioWriteYes.IsChecked = write_results
        self.RadioWriteNo.IsChecked = not write_results

        self._select_level_by_elevation(level_elevation)

    def _select_level_by_elevation(self, level_elevation):
        """Select the appropriate level in the dropdown."""
        if level_elevation is not None:
            for lvl in self.levels:
                if abs(lvl.Elevation - float(level_elevation)) < 0.001:
                    self.ComboBoxLevels.SelectedItem = lvl
                    return

        self.ComboBoxLevels.SelectedIndex = 0

    def _apply_default_ui_values(self):
        """Apply default values to UI controls in case of error."""
        self.RadioButtonFalse.IsChecked = True
        self.RadioButtonTrue.IsChecked = False
        self.TextBoxTransmission.Text = "70"
        if hasattr(self, 'ComboBoxLevels'):
            self.ComboBoxLevels.SelectedIndex = 0

    def save_button_click(self, sender, args):
        """Handle the click event for the SaveButton.

        Validates input, saves data to JSON, and closes the window.
        """
        try:
            print("Save button clicked")

            ui_data = self._collect_ui_data()
            if not ui_data:
                return

            if not self._validate_inputs(ui_data):
                return

            settings_data = self._prepare_settings_data(ui_data)

            if self._save_settings_to_file(settings_data):
                self.Close()

        except Exception as e:
            print("ERROR in save_button_click:", e)
            MessageBox.Show(
                "Unexpected error in save_button_click:\n{}".format(e),
                "Save Error"
            )

    def _collect_ui_data(self):
        """Collect data from UI controls."""
        selected_level = self.ComboBoxLevels.SelectedItem
        if selected_level is None:
            MessageBox.Show(
                "Please select a ground floor level.",
                "Missing Level"
            )
            return None

        return {
            'is_multilayer': self.RadioButtonTrue.IsChecked,
            'transmission_str': self.TextBoxTransmission.Text,
            'exec_mode': (
                'local' if self.ComboBoxExecutionMode.SelectedIndex == 1
                else 'web'
            ),
            'write_results': self.RadioWriteYes.IsChecked,
            'selected_level': selected_level
        }

    def _validate_inputs(self, ui_data):
        """Validate user inputs."""
        try:
            transmission_value = int(ui_data['transmission_str'])
            if not (0 <= transmission_value <= 100):
                raise ValueError("Value must be between 0 and 100.")
            ui_data['transmission_value'] = transmission_value
            return True
        except ValueError as e:
            MessageBox.Show(
                "Invalid Transmission Value: '{}'.\n"
                "Please enter an integer between 0 and 100.\n({})".format(
                    ui_data['transmission_str'], e
                ),
                "Invalid Input"
            )
            return False

    def _prepare_settings_data(self, ui_data):
        """Prepare settings data for saving."""
        level_elevation_mm = int(round(
            RevitApiHelper.feet_to_mm(ui_data['selected_level'].Elevation)
        ))

        return {
            'multilayer_wall': ui_data['is_multilayer'],
            'transmission_value': ui_data['transmission_value'],
            'level_elevation': level_elevation_mm,
            'execution_mode': ui_data['exec_mode'],
            'write_results': ui_data['write_results']
        }

    def _save_settings_to_file(self, settings_data):
        """Save settings data to JSON file."""
        try:
            print("Settings to save:", settings_data)
            print("Saving to:", self.settings.settings_file_path)

            self._ensure_settings_directory()

            with codecs.open(
                self.settings.settings_file_path, 'w', encoding='utf-8'
            ) as f:
                json.dump(settings_data, f, indent=4, sort_keys=True)

            print("Settings saved successfully.")
            return True

        except Exception as e:
            print("ERROR saving settings: {}".format(e))
            MessageBox.Show(
                "Failed to save settings:\n{}".format(e),
                "Save Error"
            )
            return False

    def _ensure_settings_directory(self):
        """Ensure the settings directory exists."""
        settings_dir = os.path.dirname(self.settings.settings_file_path)
        if not os.path.isdir(settings_dir):
            print("Creating directory: {}".format(settings_dir))
            try:
                os.makedirs(settings_dir)
            except OSError as e:
                print("ERROR creating directory: {}".format(e))
                MessageBox.Show(
                    "Failed to create settings directory:\n{}".format(e),
                    "Directory Error"
                )
                raise

    def help_button_click(self, sender, args):
        """Handle the click event for the HelpButton.

        Redirects to the documentation on Github.
        """
        url = (
            "https://github.com/upskiller-xyz/DaylightFactor/wiki/"
            "Usage-of-the-Daylight-Factor-Plugin"
        )

        psi = diag.ProcessStartInfo()
        psi.FileName = url
        psi.UseShellExecute = True

        diag.Process.Start(psi)


class SettingsApplication:
    """Main application class for the settings window."""

    def __init__(self):
        self.settings = DaylightSettings()
        self.revit_doc = RevitApiHelper.get_active_document()

    def run(self):
        """Run the settings application."""
        if not self._validate_xaml_file():
            return

        settings_window = SettingsWindow(
            self.settings.xaml_file_path,
            self.revit_doc
        )
        settings_window.ShowDialog()

    def _validate_xaml_file(self):
        """Validate that the XAML file exists."""
        if not os.path.isfile(self.settings.xaml_file_path):
            MessageBox.Show(
                "Error: UI definition file not found:\n{}".format(
                    self.settings.xaml_file_path
                ),
                "UI File Error"
            )
            return False
        return True


if __name__ == '__main__':
    app = SettingsApplication()
    app.run()
