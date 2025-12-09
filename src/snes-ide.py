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

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget, QDialog,
    QDialogButtonBox, QScrollArea, QLabel, QPushButton, QProgressBar,
    QGroupBox, QVBoxLayout as VBoxLayout
)
from PySide6.QtCore import QObject, Slot, Signal, QUrl, QProcess, Qt
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebChannel import QWebChannel

from typing_extensions import NoReturn, Any
from typing import Dict
from pathlib import Path
import sys
import json
import argparse
from tool_manager import ToolManager

# Textual imports (optional, for TUI mode)
try:
    from tui.app import SNESIDEApp as ToolBrowser
    HAS_TEXTUAL = True
except ImportError:
    try:
        from tools_browser import ToolBrowser
        HAS_TEXTUAL = True
    except ImportError:
        HAS_TEXTUAL = False


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
        self.scripts_dir: Path = self.get_executable_path() / "scripts"
        self.tool_manager: ToolManager = self._init_tool_manager()

    def _init_tool_manager(self) -> ToolManager:
        """
        Initialize the ToolManager with the appropriate tools.json path.

        Returns:
            ToolManager instance configured with tools.json.
        """
        try:
            tools_json_path = self.get_executable_path() / "tools.json"
            return ToolManager(tools_json_path)
        except Exception as e:
            print(f"Warning: Could not initialize ToolManager: {e}")
            # Return a manager with default path
            return ToolManager()

    @staticmethod
    def get_executable_path() -> Path:
        """Get the path of the executable or script based on whether the script is frozen 
        (PyInstaller) or not."""

        if getattr(sys, 'frozen', False):

            print("executable path mode chosen")
            return Path(sys.executable).resolve().parent

        else:

            print("Python script path mode chosen")
            return Path(__file__).resolve().parent

    @Slot(str)
    def run_script(self, script_name: str) -> None:
        """
        Execute a Python script from the scripts directory.

        This slot is connected to the run_script method which takes a script name
        as a parameter and executes it using the subprocess module.

        :param script_name: The name of the script to execute.
        :return: None
        """

        try:
            script_path: Path = self.scripts_dir / script_name

            if script_path.exists():
                self.process = QProcess()

                self.process.readyReadStandardOutput.connect(
                    self.handle_stdout)
                self.process.readyReadStandardError.connect(self.handle_stderr)
                self.process.finished.connect(self.handle_finished)

                self.process.setWorkingDirectory(str(self.scripts_dir))
                self.process.start(sys.executable, ['-s', str(script_path)])
                self.current_script = script_name

            else:
                self.scriptExecuted.emit(
                    script_name, f"Script not found: {script_path}")

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

    def handle_stdout(self):
        """
        Handle standard output from the subprocess.

        This slot is connected to the readyReadStandardOutput signal of the
        QProcess object. It reads the standard output data and prints it to
        the console.

        :return: None
        """
        
        data: "str|Any" = self.process.readAllStandardOutput().data()
        print(f"STDOUT: {data}")


    def handle_stderr(self):
        """
        Handle standard error from the subprocess.

        This slot is connected to the readyReadStandardError signal of the
        QProcess object. It reads the standard error data and prints it to
        the console.

        :return: None
        """
        
        data: "str|Any" = self.process.readAllStandardError().data()
        print(f"STDERR: {data}")


    def handle_finished(self, exit_code: int, _: Any):
        """
        Handle the finished signal of the QProcess object.

        This slot is connected to the finished signal of the QProcess object.
        It reads the standard error data and prints it to the console.

        :param exit_code: The exit code of the subprocess.
        :param _: Unused parameter.
        :return: None
        """
        
        script_name = getattr(self, 'current_script', 'Unknown')

        if exit_code == 0:
            self.scriptExecuted.emit(script_name, "Script executed successfully!")
            
        else:
            error_msg: "str|Any" = self.process.readAllStandardError().data()
            
            if isinstance(error_msg, str):
                error_msg = f"Error: {error_msg}"
                self.scriptExecuted.emit(script_name, error_msg)
            
            else:
                error_msg = f"Error: {error_msg}"
                self.scriptExecuted.emit(script_name, error_msg)

    @Slot(result=str)
    def get_tools_status(self) -> str:
        """
        Get the installation status of all tools as JSON.

        Returns:
            JSON string containing tool status information.
        """
        try:
            tools_by_category = self.tool_manager.get_tools_by_category()
            return json.dumps(tools_by_category)
        except Exception as e:
            error_data = {"error": str(e)}
            return json.dumps(error_data)

    @Slot(result=str)
    def get_missing_required_tools(self) -> str:
        """
        Get list of missing required tools as JSON.

        Returns:
            JSON string containing missing required tools.
        """
        try:
            missing = self.tool_manager.get_missing_required_tools()
            return json.dumps(missing)
        except Exception as e:
            error_data = {"error": str(e)}
            return json.dumps(error_data)


class ToolInstallerDialog(QDialog):
    """Dialog for managing tool installation and verification."""

    def __init__(self, script_runner: ScriptRunner, parent: QWidget = None) -> None:
        """
        Initialize the Tool Installer Dialog.

        Args:
            script_runner: Reference to ScriptRunner for accessing ToolManager.
            parent: Parent widget.

        Returns:
            None
        """
        super().__init__(parent)
        self.script_runner = script_runner
        self.setWindowTitle("Tool Installer")
        self.setGeometry(100, 100, 800, 600)
        self.init_ui()
        self.load_tools_status()

    def init_ui(self) -> None:
        """Initialize the user interface for the dialog."""
        layout = VBoxLayout(self)

        # Title
        title = QLabel("SNES-IDE Tool Manager")
        title.setStyleSheet("font-weight: bold; font-size: 14px; margin-bottom: 10px;")
        layout.addWidget(title)

        # Refresh button
        refresh_button = QPushButton("Refresh Status")
        refresh_button.clicked.connect(self.load_tools_status)
        layout.addWidget(refresh_button)

        # Scroll area for tools
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = VBoxLayout(scroll_widget)

        self.tool_groups: Dict[str, QGroupBox] = {}

        # Create groups by category
        tools_by_category = self.script_runner.tool_manager.get_tools_by_category()

        for category in sorted(tools_by_category.keys()):
            group = QGroupBox(category.replace("-", " ").title())
            group_layout = VBoxLayout()

            for tool_status in sorted(
                tools_by_category[category],
                key=lambda t: (not t["available"], t["priority"] == "optional", t["name"])
            ):
                tool_widget = self.create_tool_widget(tool_status)
                group_layout.addWidget(tool_widget)

            group.setLayout(group_layout)
            scroll_layout.addWidget(group)
            self.tool_groups[category] = group

        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_widget)
        layout.addWidget(scroll_area)

        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def create_tool_widget(self, tool_status: Dict[str, Any]) -> QWidget:
        """
        Create a widget for displaying and managing a single tool.

        Args:
            tool_status: Tool status dictionary.

        Returns:
            QWidget containing tool information and action buttons.
        """
        widget = QWidget()
        layout = VBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # Tool header with name and status
        header_layout = VBoxLayout()

        name_label = QLabel(tool_status["name"])
        name_label.setStyleSheet("font-weight: bold;")

        desc_label = QLabel(tool_status["description"])
        desc_label.setStyleSheet("font-size: 10px; color: gray;")

        status_text = "✓ Available" if tool_status["available"] else "✗ Not installed"
        status_color = "green" if tool_status["available"] else "red"
        status_label = QLabel(status_text)
        status_label.setStyleSheet(f"color: {status_color}; font-weight: bold;")

        header_layout.addWidget(name_label)
        header_layout.addWidget(desc_label)
        header_layout.addWidget(status_label)

        if tool_status["path"]:
            path_label = QLabel(f"Path: {tool_status['path']}")
            path_label.setStyleSheet("font-size: 9px; color: darkblue;")
            header_layout.addWidget(path_label)

        layout.addLayout(header_layout)

        # Action buttons
        if not tool_status["available"]:
            action_layout = VBoxLayout()

            install_button = QPushButton("Install")
            install_button.setMaximumWidth(100)
            # TODO: Connect to installation script when available
            install_button.setEnabled(False)
            install_button.setToolTip("Installation script not yet implemented")

            action_layout.addWidget(install_button)
            layout.addLayout(action_layout)

        widget.setLayout(layout)
        return widget

    def load_tools_status(self) -> None:
        """Reload and display current tool status."""
        try:
            # Force reload of tool statuses
            tools_by_category = self.script_runner.tool_manager.get_tools_by_category()

            # Update existing groups
            for category in self.tool_groups.keys():
                if category in tools_by_category:
                    # Tools are already displayed, just update visibility
                    pass

        except Exception as e:
            error_label = QLabel(f"Error loading tool status: {str(e)}")
            error_label.setStyleSheet("color: red;")


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
        self.setWindowTitle(
            "SNES IDE - Super Nintendo Development Environment")
        self.setGeometry(100, 100, 1200, 800)

        central_widget: QWidget = QWidget()
        self.setCentralWidget(central_widget)
        layout: QVBoxLayout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        self.web_view: QWebEngineView = QWebEngineView()

        self.channel: QWebChannel = QWebChannel()
        self.script_runner: ScriptRunner = ScriptRunner()
        self.tool_installer_dialog: ToolInstallerDialog = ToolInstallerDialog(
            self.script_runner, self
        )
        self.channel.registerObject("scriptRunner", self.script_runner)
        self.channel.registerObject("toolInstaller", self)
        self.web_view.page().setWebChannel(self.channel)

        html_path: Path = ScriptRunner.get_executable_path() / "assets" / "index.html"

        url: QUrl = QUrl.fromLocalFile(str(html_path.resolve()))

        self.web_view.load(url)

        layout.addWidget(self.web_view)

    @Slot()
    def show_tool_installer(self) -> None:
        """
        Show the tool installer dialog.

        Returns:
            None
        """
        self.tool_installer_dialog.show()


def run_tui() -> NoReturn:
    """Run the Textual TUI version."""
    if not HAS_TEXTUAL:
        print("Error: textual is not installed. Install it with:")
        print("  pip install textual")
        sys.exit(1)
    
    app = ToolBrowser()
    app.run()
    sys.exit(0)


def main() -> NoReturn:
    """
    Main entry point of the application.
    
    Supports command-line flags:
    - --tui, -t: Run in Textual TUI mode instead of Qt GUI
    """
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="SNES IDE - Tool Manager")
    parser.add_argument(
        "--tui", "-t",
        action="store_true",
        help="Run in Textual TUI mode instead of Qt GUI"
    )
    args = parser.parse_args()
    
    # Launch TUI if requested
    if args.tui:
        run_tui()
    
    # Otherwise launch Qt GUI
    app: QApplication = QApplication(sys.argv)

    try:
        app.setStyle('Fusion')  # type: ignore
    except:
        ...

    window: MainWindow = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
