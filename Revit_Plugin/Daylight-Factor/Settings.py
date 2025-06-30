# -*- coding: utf-8 -*-

import clr
clr.AddReference("RhinoInside.Revit")
from RhinoInside.Revit import Revit
# Import necessary Revit API classes
from Autodesk.Revit.DB import FilteredElementCollector, Level

# application
uiapp = Revit.ActiveUIApplication
dbapp = Revit.ActiveDBApplication

# document
uidoc = Revit.ActiveUIDocument
doc = Revit.ActiveDBDocument

import json
import os
import codecs  # Required for file open() with encoding in Python 2.x
from Autodesk.Revit.DB import UnitUtils
# --- Conversion of Revit-internal feet units to millimetres ---

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

# --- WPF Imports ---
clr.AddReference("PresentationFramework")
clr.AddReference("WindowsBase")
clr.AddReference("PresentationCore")
from System.Windows import Window, MessageBox
from System.Windows.Markup import XamlReader
from System.IO import FileStream, FileMode

# --- Constants ---
SETTINGS_FILENAME = "settings_daylight.json"
XAML_FILENAME = "SettingsDaylightWindow.xaml"

# --- Path Calculation (using os.path for Python 2.x compatibility) ---
try:
    script_abspath = os.path.abspath(__file__)
    script_dir = os.path.dirname(script_abspath)
    # Save settings file one directory above this script (in Revit_Plugin)
    parent_dir = os.path.dirname(script_dir)
    settings_file_path = os.path.join(parent_dir, SETTINGS_FILENAME)
    xaml_file_path = os.path.join(script_dir, XAML_FILENAME)
except NameError:
    print("WARNING: Could not determine script path. Using current working directory for XAML and settings.")
    script_dir = os.getcwd()
    parent_dir = os.path.dirname(script_dir)
    settings_file_path = os.path.join(parent_dir, SETTINGS_FILENAME)
    xaml_file_path = os.path.join(script_dir, XAML_FILENAME)

# --- Main Window Class ---
class SettingsWindow(Window):
    """
    Settings window for Daylight Prediction using standard WPF.
    Loads layout from XAML and handles loading/saving settings.
    """
    def _find_child_by_name(self, parent, name):
        # Recursively search for a child element by x:Name
        if hasattr(parent, 'Name') and parent.Name == name:
            return parent
        if hasattr(parent, 'Children') and parent.Children is not None:
            for child in parent.Children:
                result = self._find_child_by_name(child, name)
                if result is not None:
                    return result
        if hasattr(parent, 'Content') and parent.Content is not None and parent.Content != parent:
            result = self._find_child_by_name(parent.Content, name)
            if result is not None:
                return result
        if hasattr(parent, 'Child') and parent.Child is not None:
            result = self._find_child_by_name(parent.Child, name)
            if result is not None:
                return result
        if hasattr(parent, 'Items') and parent.Items is not None:
            for item in parent.Items:
                result = self._find_child_by_name(item, name)
                if result is not None:
                    return result
        return None

    def __init__(self, xaml_source, revit_doc):
        # Load XAML with shared read/write access to avoid file lock issues
        from System.IO import FileAccess, FileShare
        fs = FileStream(xaml_source, FileMode.Open, FileAccess.Read, FileShare.ReadWrite)
        try:
            window = XamlReader.Load(fs)
        finally:
            fs.Close()
        Window.__init__(self)
        self.Content = window.Content
        self.Title = window.Title
        self.Width = window.Width
        self.Height = window.Height

        # Use recursive search for controls
        self.SaveButton = self._find_child_by_name(self.Content, "SaveButton")
        self.ComboBoxLevels = self._find_child_by_name(self.Content, "ComboBoxLevels")
        self.RadioButtonTrue = self._find_child_by_name(self.Content, "RadioButtonTrue")
        self.RadioButtonFalse = self._find_child_by_name(self.Content, "RadioButtonFalse")
        self.TextBoxTransmission = self._find_child_by_name(self.Content, "TextBoxTransmission")

        # Attach event handler
        if self.SaveButton:
            self.SaveButton.Click += self.save_button_click

        self.revit_doc = revit_doc
        self._load_settings()

    def _load_settings(self):
        """Loads settings from the JSON file and updates UI elements."""
        try:
            # --- Populate levels from Revit model ---
            doc = self.revit_doc
            self.levels = [lvl for lvl in FilteredElementCollector(doc).OfClass(Level)]
            self.ComboBoxLevels.ItemsSource = self.levels

            # Default: select first level
            if os.path.isfile(settings_file_path):
                with codecs.open(settings_file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                is_multilayer = bool(data.get('multilayer_wall', False))
                transmission_val = str(data.get('transmission_value', 70))
                level_elevation = data.get('level_elevation', None)
                if level_elevation is not None:
                    for lvl in self.levels:
                        if abs(lvl.Elevation - float(level_elevation)) < 0.001:
                            self.ComboBoxLevels.SelectedItem = lvl
                            break
                    else:
                        self.ComboBoxLevels.SelectedIndex = 0
                else:
                    self.ComboBoxLevels.SelectedIndex = 0
            else:
                is_multilayer = False
                transmission_val = "70"
                self.ComboBoxLevels.SelectedIndex = 0

            self.RadioButtonTrue.IsChecked = is_multilayer
            self.RadioButtonFalse.IsChecked = not is_multilayer
            self.TextBoxTransmission.Text = transmission_val

        except Exception as e:
            print("ERROR loading settings: {}".format(e))
            MessageBox.Show("Error loading settings file or levels.\nDefaults will be used.", "Load Error")
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
        try:
            print("Save button clicked")
            # 1. Read current values from UI controls
            is_multilayer = self.RadioButtonTrue.IsChecked
            transmission_str = self.TextBoxTransmission.Text
            print("Transmission input:", transmission_str)

            # 2. Validate the transmission value input
            try:
                transmission_value = int(transmission_str)
                if not (0 <= transmission_value <= 100):
                    raise ValueError("Value must be between 0 and 100.")
            except ValueError as e:
                MessageBox.Show("Invalid Transmission Value: '{}'.\nPlease enter an integer between 0 and 100.\n({})".format(transmission_str, e),
                                "Invalid Input")
                return # Stop saving process

            # --- Get selected level and its elevation ---
            selected_level = self.ComboBoxLevels.SelectedItem
            if selected_level is not None:
                level_elevation = selected_level.Elevation
            else:
                MessageBox.Show("Please select a ground floor level.", "Missing Level")
                return

            # 3. Prepare data dictionary
            settings_data = {
                'multilayer_wall': is_multilayer,
                'transmission_value': transmission_value,
                'level_elevation': int(round(feet_to_mm(level_elevation)))  # Use Revit API conversion
            }
            print("Settings to save:", settings_data)
            print("Saving to:", settings_file_path)

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
                        MessageBox.Show("Failed to create settings directory:\n{}".format(e), "Directory Error")
                        return # Stop saving process

                # Write the file using codecs.open for Python 2 encoding compatibility
                with codecs.open(settings_file_path, 'w', encoding='utf-8') as f:
                    json.dump(settings_data, f, indent=4, sort_keys=True) # sort_keys for consistent output
                print("Settings saved successfully.")
                self.Close() # Close the window upon successful save

            except Exception as e:
                # Handle potential errors during file writing
                print("ERROR saving settings: {}".format(e))
                MessageBox.Show("Failed to save settings:\n{}".format(e), "Save Error")
        except Exception as e:
            print("ERROR in save_button_click:", e)
            MessageBox.Show("Unexpected error in save_button_click:\n{}".format(e), "Save Error")


# --- Script Execution ---
if __name__ == '__main__':
    # Verify the XAML file exists before trying to load it
    if not os.path.isfile(xaml_file_path):
        MessageBox.Show("Error: UI definition file not found:\n{}".format(xaml_file_path), "UI File Error")
    else:
        # Create an instance of the settings window
        settings_window = SettingsWindow(xaml_file_path, doc)
        # Show the window as a modal dialog (waits until closed)
        settings_window.ShowDialog()