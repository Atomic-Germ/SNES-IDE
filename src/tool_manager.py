"""
Tool Manager Module - tool_manager.py
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

import json
import subprocess
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, List
import sys


class ToolManager:
    """Manages tool installation and verification from tools.json configuration."""

    def __init__(self, tools_config_path: Optional[Path] = None) -> None:
        """
        Initialize the ToolManager.

        Args:
            tools_config_path: Path to tools.json config file. If None, uses default location.

        Returns:
            None
        """
        if tools_config_path is None:
            # Default to tools.json in the same directory as this script
            self.config_path = Path(__file__).resolve().parent / "tools.json"
        else:
            self.config_path = Path(tools_config_path)

        self.tools_config: Dict[str, Any] = {}
        self.load_config()

    def load_config(self) -> None:
        """
        Load tools.json configuration file.

        Raises:
            FileNotFoundError: If tools.json is not found.
            json.JSONDecodeError: If tools.json is malformed.

        Returns:
            None
        """
        if not self.config_path.exists():
            raise FileNotFoundError(f"tools.json not found at {self.config_path}")

        with open(self.config_path, "r", encoding="utf-8") as f:
            self.tools_config = json.load(f)

    def get_all_tools(self) -> List[Dict[str, Any]]:
        """
        Get list of all tools from configuration.

        Returns:
            List of tool configuration dictionaries.
        """
        return self.tools_config.get("tools", [])

    def find_tool_in_path(self, tool_name: str) -> Optional[Path]:
        """
        Check if a tool binary is available in system PATH.

        Args:
            tool_name: Name of the tool binary to search for.

        Returns:
            Path to the tool if found, None otherwise.
        """
        return shutil.which(tool_name)

    def get_tool_status(self, tool: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get installation status of a tool.

        Args:
            tool: Tool configuration dictionary.

        Returns:
            Dictionary with status information including:
                - name: Tool name
                - available: Boolean indicating if tool is in PATH
                - path: Path to tool if available
                - category: Tool category
                - priority: Tool priority (required/optional)
                - description: Tool description
        """
        binary_name = tool.get("binary_name", {})
        search_name = None

        # Determine the binary name for current platform
        if isinstance(binary_name, dict):
            search_name = binary_name.get(sys.platform)
        elif isinstance(binary_name, str):
            search_name = binary_name

        if search_name is None:
            # Fallback to tool name
            search_name = tool.get("name", "").lower()

        tool_path = self.find_tool_in_path(search_name)

        return {
            "name": tool.get("name", "Unknown"),
            "available": tool_path is not None,
            "path": str(tool_path) if tool_path else None,
            "category": tool.get("category", "unknown"),
            "priority": tool.get("priority", "optional"),
            "description": tool.get("description", ""),
            "is_sdk": tool.get("is_sdk", False),
        }

    def get_all_tools_status(self) -> List[Dict[str, Any]]:
        """
        Get installation status of all tools.

        Returns:
            List of tool status dictionaries.
        """
        all_tools = self.get_all_tools()
        return [self.get_tool_status(tool) for tool in all_tools]

    def get_tools_by_category(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get tools organized by category with their status.

        Returns:
            Dictionary mapping category names to lists of tool status dictionaries.
        """
        status_by_category: Dict[str, List[Dict[str, Any]]] = {}

        for tool_status in self.get_all_tools_status():
            category = tool_status["category"]
            if category not in status_by_category:
                status_by_category[category] = []
            status_by_category[category].append(tool_status)

        return status_by_category

    def verify_tool(self, tool_name: str) -> bool:
        """
        Verify a tool using its verify_command.

        Args:
            tool_name: Name of the tool to verify.

        Returns:
            True if tool verification succeeds, False otherwise.
        """
        all_tools = self.get_all_tools()
        tool = next((t for t in all_tools if t.get("name") == tool_name), None)

        if tool is None:
            return False

        verify_command = tool.get("verify_command", [])
        if not verify_command:
            return self.find_tool_in_path(tool.get("name", "")) is not None

        try:
            subprocess.run(
                verify_command,
                capture_output=True,
                timeout=5,
                check=True,
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def get_tool_by_name(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        Get tool configuration by name.

        Args:
            tool_name: Name of the tool to retrieve.

        Returns:
            Tool configuration dictionary or None if not found.
        """
        all_tools = self.get_all_tools()
        return next((t for t in all_tools if t.get("name") == tool_name), None)

    def get_required_tools(self) -> List[Dict[str, Any]]:
        """
        Get list of required tools.

        Returns:
            List of tool status dictionaries for required tools only.
        """
        return [
            status for status in self.get_all_tools_status()
            if status["priority"] == "required"
        ]

    def get_optional_tools(self) -> List[Dict[str, Any]]:
        """
        Get list of optional tools.

        Returns:
            List of tool status dictionaries for optional tools only.
        """
        return [
            status for status in self.get_all_tools_status()
            if status["priority"] == "optional"
        ]

    def get_missing_required_tools(self) -> List[Dict[str, Any]]:
        """
        Get list of required tools that are not available.

        Returns:
            List of unavailable required tool status dictionaries.
        """
        return [
            tool for tool in self.get_required_tools()
            if not tool["available"]
        ]
