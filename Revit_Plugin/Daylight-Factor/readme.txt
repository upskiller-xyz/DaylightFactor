# PyRevit Settings Dialog for Daylight Prediction

This document outlines the development process and technical decisions made while creating a settings dialog for a PyRevit script. The goal was to provide a user-friendly way to configure parameters for a daylight prediction tool and persist these settings in a JSON file.

## Initial Goal

- Create a GUI window accessible from a PyRevit pushbutton.
- Allow users to set a boolean value (e.g., "External Wall as Multilayered Wall?") and a numerical value (e.g., "Transmission Value %").
- Load existing settings when the dialog opens.
- Save the chosen settings to a JSON file (`settings_daylight.json`) located four levels above the script's directory (in the main extension folder).
- Ensure the solution requires no complex setup for the end-user.

## Development Journey & Technical Challenges

1.  **Attempt 1: `tkinter`**
    * **Reasoning:** Part of Python's standard library, seemed like the most straightforward approach for a simple GUI.
    * **Problem:** The script failed immediately with a `SyntaxError` related to f-strings (`f"..."`).
    * **Diagnosis:** This indicated that the IronPython engine used by the target PyRevit/Revit environment was based on a Python version older than 3.6 (where f-strings were introduced).
    * **Intermediate Fix:** Replacing f-strings with `str.format()` resolved the syntax error but revealed deeper compatibility issues.

2.  **Identifying the Core Constraint: IronPython Environment**
    * It became clear that the primary constraint was the specific (likely old, Python 2.x based) IronPython version bundled with Revit and used by PyRevit by default. All solutions needed to be compatible with this environment.

3.  **Evaluating Alternatives**
    * **CPython Engine:** PyRevit allows configuring a CPython engine. This would grant access to modern Python features and libraries (including `tkinter` without issues).
        * **Rejected:** Requires end-users to install a specific Python version and configure PyRevit, violating the "easy deployment" requirement.
    * **WinForms (`System.Windows.Forms`):** A .NET GUI framework directly accessible from IronPython.
        * **Viable:** Compatible and requires no extra installation. However, the syntax can be verbose and less "Pythonic".
    * **`pyrevit.forms` (WPF/XAML):** PyRevit's built-in mechanism for creating GUIs, used for its own dialogs (e.g., "About", "Extensions").
        * **Chosen:** This seemed the most idiomatic and robust approach within the PyRevit ecosystem. It leverages WPF/.NET (compatible with IronPython), allows UI definition in separate XAML files, and requires no extra user setup.

4.  **Attempt 2: `pyrevit.forms` with WPF/XAML**
    * **Implementation:**
        * Created `SettingsDaylightWindow.xaml` defining the window layout using standard WPF controls (`Grid`, `Label`, `RadioButton`, `TextBox`, `Button`) and `x:Name` attributes for control identification.
        * Created `script.py` with a class inheriting from `pyrevit.forms.WPFWindow`, loading the XAML.
    * **Problem 2: `pathlib` Import Error (`ImportError: Cannot import name curdir`)**
        * **Diagnosis:** The `pathlib` module (or its underlying dependencies like `os`/`ntpath`) was incompatible with the IronPython environment's standard library (likely missing `os.curdir` where expected).
        * **Solution:** Replaced all `pathlib` usage with the older, universally compatible `os` and `os.path` modules for all path manipulations.
    * **Problem 3: `os.makedirs(exist_ok=True)` Error (`TypeError: unexpected keyword argument 'exist_ok'`)**
        * **Diagnosis:** The `exist_ok` argument was introduced in Python 3.2. The environment was older.
        * **Solution:** Manually replicated the behavior by checking `if not os.path.isdir(path):` before calling `os.makedirs(path)` without the argument.
    * **Problem 4: `open(encoding=...)` Error (`TypeError: unexpected keyword argument 'encoding'`)**
        * **Diagnosis:** The built-in `open()` function only gained the `encoding` parameter in Python 3.0. The environment was clearly Python 2.x based.
        * **Solution:** Replaced built-in `open()` with `codecs.open()`, which supports the `encoding` parameter in Python 2.x.

## Final Solution

The final, working solution consists of:

1.  **`SettingsDaylightWindow.xaml`:** A WPF XAML file defining the user interface.
2.  **`script.py`:** A Python script using `pyrevit.forms.WPFWindow` to load the XAML and handle logic. It is specifically written for Python 2.x / older IronPython compatibility using:
    * `os` and `os.path` for path operations.
    * Manual directory existence check before `os.makedirs`.
    * `codecs.open()` for file I/O with UTF-8 encoding.
    * `str.format()` or basic concatenation for string formatting (no f-strings).

This approach ensures the settings dialog works reliably within the standard PyRevit/IronPython environment without requiring additional setup from the end-user.