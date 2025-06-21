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

# --- PyRevit Imports ---
from pyrevit import forms
from pyrevit import revit
from Autodesk.Revit.DB import FilteredElementCollector, Level

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

# --- Main Window Class ---
class SettingsWindow(forms.WPFWindow):
    """
    Settings window for Daylight Prediction.
    Loads layout from XAML and handles loading/saving settings.
    Uses os.path and codecs.open for Python 2.x compatibility.
    """
    def __init__(self, xaml_source):
        """
        Initializes the window by loading XAML and initial settings.

        Args:
            xaml_source (str): Path to the XAML file.
        """
        # Load the XAML file. Controls with x:Name become attributes (e.g., self.SaveButton)
        forms.WPFWindow.__init__(self, xaml_source)
        # Load existing settings into the UI controls
        self._load_settings()

    def _load_settings(self):
        """Loads settings from the JSON file and updates UI elements."""
        try:
            # --- Populate levels from Revit model ---
            doc = revit.doc
            self.levels = [lvl for lvl in FilteredElementCollector(doc).OfClass(Level)]
            self.ComboBoxLevels.ItemsSource = self.levels

            # Default: select first level
            selected_level_id = None
            if os.path.isfile(settings_file_path):
                # print("Loading settings from: {}".format(settings_file_path))  # Comment out this line to avoid printing or showing this terminal output message to the user
                # Use codecs.open for Python 2 compatibility with encoding
                with codecs.open(settings_file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Get values, providing defaults if keys are missing
                is_multilayer = bool(data.get('multilayer_wall', False)) # Default: False
                transmission_val = str(data.get('transmission_value', 70)) # Default: 70
                level_elevation = data.get('level_elevation', None)
                # Try to select the saved elevation
                if level_elevation is not None:
                    for lvl in self.levels:
                        if abs(lvl.Elevation - float(level_elevation)) < 0.001:
                            self.ComboBoxLevels.SelectedItem = lvl
                            break
                else:
                    self.ComboBoxLevels.SelectedIndex = 0
            else:
                print("Settings file not found. Using default values.")
                is_multilayer = False
                transmission_val = "70"
                self.ComboBoxLevels.SelectedIndex = 0

            # Update UI controls based on loaded data
            self.RadioButtonTrue.IsChecked = is_multilayer
            self.RadioButtonFalse.IsChecked = not is_multilayer
            self.TextBoxTransmission.Text = transmission_val

        except Exception as e:
            print("ERROR loading settings: {}".format(e))
            forms.alert("Error loading settings file or levels.\nDefaults will be used.", title="Load Error")
            # Set default UI values on error
            self.RadioButtonFalse.IsChecked = True
            self.RadioButtonTrue.IsChecked = False
            self.TextBoxTransmission.Text = "70"
            if hasattr(self, 'ComboBoxLevels'):
                self.ComboBoxLevels.SelectedIndex = 0

    def save_button_click(self, sender, args):
        """
        Handles the click event for the 'SaveButton' defined in XAML.
        Validates input, saves data to JSON, and closes the window.
        """
        # 1. Read current values from UI controls
        is_multilayer = self.RadioButtonTrue.IsChecked
        transmission_str = self.TextBoxTransmission.Text

        # 2. Validate the transmission value input
        try:
            transmission_value = int(transmission_str)
            if not (0 <= transmission_value <= 100):
                 raise ValueError("Value must be between 0 and 100.")
        except ValueError as e:
            forms.alert("Invalid Transmission Value: '{}'.\nPlease enter an integer between 0 and 100.\n({})".format(transmission_str, e),
                        title="Invalid Input", warn_icon=True)
            return # Stop saving process

        # --- Get selected level and its elevation ---
        selected_level = self.ComboBoxLevels.SelectedItem
        if selected_level is not None:
            level_elevation = selected_level.Elevation
        else:
            forms.alert("Please select a ground floor level.", title="Missing Level", warn_icon=True)
            return

        # 3. Prepare data dictionary
        settings_data = {
            'multilayer_wall': is_multilayer,
            'transmission_value': transmission_value,
            'level_elevation': int(round(feet_to_mm(level_elevation)))  # Use Revit API conversion
        }

        # 4. Write data to JSON file
        try:
            # Ensure target directory exists (manual check for Python < 3.2)
            settings_dir = os.path.dirname(settings_file_path)
            if not os.path.isdir(settings_dir):
                print("Creating directory: {}".format(settings_dir))
                try:
                    # Create directory (no exist_ok argument)
                    os.makedirs(settings_dir)
                except OSError as e:
                    print("ERROR creating directory: {}".format(e))
                    forms.alert("Failed to create settings directory:\n{}".format(e), title="Directory Error", warn_icon=True)
                    return # Stop saving process

            # Write the file using codecs.open for Python 2 encoding compatibility
            with codecs.open(settings_file_path, 'w', encoding='utf-8') as f:
                json.dump(settings_data, f, indent=4, sort_keys=True) # sort_keys for consistent output

            #print("Settings saved successfully to: {}".format(settings_file_path))  # Comment out this line to avoid printing or showing this terminal output message to the user
            self.Close() # Close the window upon successful save

        except Exception as e:
            # Handle potential errors during file writing
            print("ERROR saving settings: {}".format(e))
            forms.alert("Failed to save settings:\n{}".format(e), title="Save Error", warn_icon=True)

# --- Script Execution ---
if __name__ == '__main__':
    # Verify the XAML file exists before trying to load it
    if not os.path.isfile(xaml_file_path):
        forms.alert("Error: UI definition file not found:\n{}".format(xaml_file_path), title="UI File Error", exitscript=True)
    else:
        # Create an instance of the settings window
        settings_window = SettingsWindow(xaml_file_path)
        # Show the window as a modal dialog (waits until closed)
        settings_window.show_dialog()
        # Optional: Code here runs after the dialog is closed
        # print("Settings window closed.") # Comment out this line to avoid printing or showing this terminal output message to the user