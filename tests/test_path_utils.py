import sys
from pathlib import Path
from unittest.mock import patch


def _import_path_utils_from_src():
    # Ensure src is on sys.path so imports work consistently when running pytest
    repo_root = Path(__file__).resolve().parent.parent
    src_dir = repo_root / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))


_import_path_utils_from_src()

from path_utils import PathManager, path_manager


def test_frozen_detection():
    # When sys.frozen is present, PathManager.is_frozen should be True
    with patch("sys.frozen", True, create=True):
        manager = PathManager()
        assert manager.is_frozen is True


def test_executable_naming():
    manager = PathManager()

    with patch("os.name", "nt"):
        assert manager.executable_name("test") == "test.exe"

    with patch("os.name", "posix"):
        assert manager.executable_name("test") == "test"


def test_tool_path_resolution():
    manager = PathManager()
    tool_name = "get-snes-ide-home"
    tool_path = manager.get_tool_path(tool_name)
    assert tool_path.is_absolute()
    assert tool_name in str(tool_path)


def test_project_root_contains_build_script():
    manager = PathManager()
    build_script = manager.project_root / "build" / "build.py"
    assert build_script.exists()


def test_ensure_directory_exists(tmp_path: Path):
    manager = PathManager()
    # Use tmp_path to create a directory under the project's build output
    test_dir = tmp_path / "a" / "b"
    assert not test_dir.exists()
    created = manager.ensure_directory_exists(str(test_dir))
    assert created.exists()
    assert created.is_dir()
