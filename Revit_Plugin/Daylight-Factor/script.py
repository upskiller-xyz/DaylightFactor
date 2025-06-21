# -*- coding: utf-8 -*-
# pylint: disable=E0401,W0703,C0103
# E0401: Module import errors (expected for pyrevit imports outside Revit)
# W0703: Catching too general exception (Exception) - sometimes needed for UI/IO
# C0103: Invalid constant name (convention)

import json
import os
import codecs # Required for file open() with encoding in Python 2.x

# --- Conversion of Revit-internal feet units to millimetres ---
import clr
clr.AddReference("RevitAPI")
clr.AddReference("PresentationFramework")
clr.AddReference("PresentationCore")
clr.AddReference("WindowsBase")
clr.AddReference("System.Xaml")
from Autodesk.Revit.DB import UnitUtils

# Try the modern API first (Revit 2021+)
try:
    from Autodesk.Revit.DB import UnitTypeId
    MM = UnitTypeId.Millimeters
except ImportError:
    from Autodesk.Revit.DB import DisplayUnitType
    MM = DisplayUnitType.DUT_MILLIMETERS

def feet_to_mm(value_ft):
    """Convert Revit-internal feet to millimetres."""
    return UnitUtils.ConvertFromInternalUnits(value_ft, MM)

from Autodesk.Revit.DB import FilteredElementCollector, Level

# --- WPF Imports ---
from System.Windows import MessageBox
from System.Windows.Markup import XamlReader
from System.IO import FileStream, FileMode

# --- Constants ---
SETTINGS_FILENAME = "settings_daylight.json"
XAML_FILENAME = "SettingsDaylightWindow.xaml"

# --- Path Calculation (using os.path for Python 2.x compatibility) ---
try:
    # Get absolute path of the script
    script_abspath = os.path.abspath(__file__)
    # Get the directory containing the script
    script_dir = os.path.dirname(script_abspath)
    # Path to XAML file in the same directory
    xaml_file_path = os.path.join(script_dir, XAML_FILENAME)

    # Navigate 4 levels up for the settings file target directory
    level1_up = os.path.dirname(script_dir)
    level2_up = os.path.dirname(level1_up)
    level3_up = os.path.dirname(level2_up)
    target_dir = os.path.dirname(level3_up)

    # Full path to the settings file
    settings_file_path = os.path.join(target_dir, SETTINGS_FILENAME)
except NameError:
    # Fallback if __file__ is not defined (e.g., interactive console)
    print("WARNING: Could not determine script path. Using current working directory for XAML and settings.")
    script_dir = os.getcwd()
    xaml_file_path = os.path.join(script_dir, XAML_FILENAME)
    settings_file_path = os.path.join(script_dir, SETTINGS_FILENAME)

# --- Helper: Get Revit Document ---
def get_revit_doc():
    # For IronPython in Revit, __revit__ may be available, otherwise use __context__ or UIApplication
    try:
        return __revit__.ActiveUIDocument.Document
    except:
        try:
            return __context__.ActiveUIDocument.Document
        except:
            # Fallback: try global variable 'doc'
            global doc
            return doc

# --- Helper: Show Alert ---
def show_alert(message, title="Alert"):
    MessageBox.Show(message, title)

# --- Main Window Class ---
class SettingsWindow(object):
    """
    Settings window for Daylight Prediction.
    Loads layout from XAML and handles loading/saving settings.
    Uses os.path and codecs.open for Python 2.x compatibility.
    """
    def __init__(self, xaml_source):
        # Load the XAML file
        with FileStream(xaml_source, FileMode.Open) as fs:
            self.window = XamlReader.Load(fs)
        self._wire_events()
        self._load_settings()

    def _wire_events(self):
        # Wire up SaveButton click event
        self.window.SaveButton.Click += self.save_button_click

    def _load_settings(self):
        try:
            doc = get_revit_doc()
            self.levels = [lvl for lvl in FilteredElementCollector(doc).OfClass(Level)]
            self.window.ComboBoxLevels.ItemsSource = self.levels

            selected_level_id = None
            if os.path.isfile(settings_file_path):
                with codecs.open(settings_file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                is_multilayer = bool(data.get('multilayer_wall', False))
                transmission_val = str(data.get('transmission_value', 70))
                level_elevation = data.get('level_elevation', None)
                if level_elevation is not None:
                    for lvl in self.levels:
                        if abs(lvl.Elevation - float(level_elevation)) < 0.001:
                            self.window.ComboBoxLevels.SelectedItem = lvl
                            break
                else:
                    self.window.ComboBoxLevels.SelectedIndex = 0
            else:
                is_multilayer = False
                transmission_val = "70"
                self.window.ComboBoxLevels.SelectedIndex = 0

            self.window.RadioButtonTrue.IsChecked = is_multilayer
            self.window.RadioButtonFalse.IsChecked = not is_multilayer
            self.window.TextBoxTransmission.Text = transmission_val

        except Exception as e:
            show_alert("Error loading settings file or levels.\nDefaults will be used.", title="Load Error")
            self.window.RadioButtonFalse.IsChecked = True
            self.window.RadioButtonTrue.IsChecked = False
            self.window.TextBoxTransmission.Text = "70"
            if hasattr(self.window, 'ComboBoxLevels'):
                self.window.ComboBoxLevels.SelectedIndex = 0

    def save_button_click(self, sender, args):
        is_multilayer = self.window.RadioButtonTrue.IsChecked
        transmission_str = self.window.TextBoxTransmission.Text

        try:
            transmission_value = int(transmission_str)
            if not (0 <= transmission_value <= 100):
                raise ValueError("Value must be between 0 and 100.")
        except ValueError as e:
            show_alert("Invalid Transmission Value: '{}'.\nPlease enter an integer between 0 and 100.\n({})".format(transmission_str, e),
                       title="Invalid Input")
            return

        selected_level = self.window.ComboBoxLevels.SelectedItem
        if selected_level is not None:
            level_elevation = selected_level.Elevation
        else:
            show_alert("Please select a ground floor level.", title="Missing Level")
            return

        settings_data = {
            'multilayer_wall': is_multilayer,
            'transmission_value': transmission_value,
            'level_elevation': int(round(feet_to_mm(level_elevation)))
        }

        try:
            settings_dir = os.path.dirname(settings_file_path)
            if not os.path.isdir(settings_dir):
                os.makedirs(settings_dir)
            with codecs.open(settings_file_path, 'w', encoding='utf-8') as f:
                json.dump(settings_data, f, indent=4, sort_keys=True)
            self.window.Close()
        except Exception as e:
            show_alert("Failed to save settings:\n{}".format(e), title="Save Error")

    def show_dialog(self):
        self.window.ShowDialog()

# --- Script Execution ---
if __name__ == '__main__':
    if not os.path.isfile(xaml_file_path):
        show_alert("Error: UI definition file not found:\n{}".format(xaml_file_path), title="UI File Error")
    else:
        settings_window = SettingsWindow(xaml_file_path)
        settings_window.show_dialog()