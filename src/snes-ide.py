"""
SNES-IDE - snes-ide.py
Copyright (C) 2025 BrunoRNS

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import QObject, Slot, Signal
from PySide6.QtWebChannel import QWebChannel

from typing_extensions import NoReturn
from pathlib import Path
import sys

# Import path utilities
from path_utils import path_manager
from subprocess_utils import subprocess_manager

class ScriptRunner(QObject):
    
    scriptExecuted: Signal = Signal(str, str)
    
    def __init__(self) -> None:
        """
        Initializes the ScriptRunner object.

        Sets the path of the scripts directory to the directory containing the
        executable or script, depending on whether the script is frozen (PyInstaller)
        or not.

        :return: None
        """
        
        super().__init__()
        self.scripts_dir: Path = path_manager.executable_dir / "scripts"

    @Slot(str)
    def run_script(self, script_name: str) -> None:
        """Execute a Python script from the scripts directory"""
        
        try:
            script_path: Path = self.scripts_dir / script_name
            if script_path.exists():
                # Execute Python script using subprocess_manager
                result = subprocess_manager.run_external_executable(
                    sys.executable,
                    args=[str(script_path)],
                    cwd=self.scripts_dir,
                    capture_output=True
                )
                
                if result.success:
                    self.scriptExecuted.emit(script_name, "Script executed successfully!")
                else:
                    self.scriptExecuted.emit(script_name, f"Error: {result.stderr}")
            else:
                self.scriptExecuted.emit(script_name, f"Script not found: {script_path}")

        except Exception as e:
            self.scriptExecuted.emit(script_name, f"Exception: {str(e)}")
            
    @Slot(str)
    def runScript(self, scriptName: str) -> None:
        """
        Execute a Python script from the scripts directory.

        This slot is connected to the run_script method which takes a script name
        as a parameter and executes it using the subprocess module.

        :param scriptName: The name of the script to execute.
        :return: None
        """
        
        self.run_script(scriptName)

class MainWindow(QMainWindow):
    
    def __init__(self) -> None:
        """
        Initializes the main window of the SNES IDE.

        Sets the window title to "SNES IDE - Super Nintendo Development Environment",
        sets the window size to 1200x800, and sets the layout to a vertical box layout.
        Creates a QWebEngineView and sets it as the central widget of the main window.
        Creates a QWebChannel and registers a ScriptRunner object with it.
        Loads the index.html file from the assets directory into the QWebEngineView.
        """
        
        super().__init__()
        self.setWindowTitle("SNES IDE - Super Nintendo Development Environment")
        self.setGeometry(100, 100, 1200, 800)
        
        central_widget: QWidget = QWidget()
        self.setCentralWidget(central_widget)
        layout: QVBoxLayout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.web_view: QWebEngineView = QWebEngineView()
        
        self.channel: QWebChannel = QWebChannel()
        self.script_runner: ScriptRunner = ScriptRunner()
        self.channel.registerObject("scriptRunner", self.script_runner)
        self.web_view.page().setWebChannel(self.channel)
        
        html_path: Path = path_manager.executable_dir / "assets" / "index.html"
        self.web_view.load(f"file:///{html_path.resolve()}")
        
        layout.addWidget(self.web_view)

def main() -> NoReturn:
    """
    Main entry point of the application. Initializes QApplication,
    sets the style to Fusion if possible, creates a MainWindow,
    shows it and starts the application event loop.
    """
    
    app: QApplication = QApplication(sys.argv)
    
    try:
        app.setStyle('Fusion') # type: ignore
    except: ...
    
    window: MainWindow = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
