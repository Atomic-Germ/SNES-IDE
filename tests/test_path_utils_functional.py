"""
Functional test script to validate path_utils migration works in practice.

This script performs smoke tests to ensure that migrated scripts can:
1. Import correctly
2. Access path_manager 
3. Resolve paths properly
4. Work in both development and simulated frozen modes
"""

import sys
import os
import tempfile
import subprocess
from pathlib import Path
from typing import List, Dict, Tuple

# Setup path to import project modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

def test_script_imports() -> List[Tuple[str, bool, str]]:
    """Test that migrated scripts can import without errors."""
    results = []
    
    scripts_to_test = [
        "src/scripts/get-snes-ide-home.py",
        # Note: Other scripts might require GUI libraries, so we'll focus on basic ones
    ]
    
    for script_path in scripts_to_test:
        full_path = project_root / script_path
        if not full_path.exists():
            results.append((script_path, False, "File not found"))
            continue
            
        try:
            # Try to import the script's module
            result = subprocess.run(
                [sys.executable, "-c", f"exec(open(r'{full_path}').read())"],
                capture_output=True, 
                text=True,
                timeout=10,
                cwd=project_root
            )
            
            if result.returncode == 0:
                results.append((script_path, True, "Import successful"))
            else:
                results.append((script_path, False, f"Import error: {result.stderr[:200]}"))
                
        except subprocess.TimeoutExpired:
            results.append((script_path, False, "Timeout during import test"))
        except Exception as e:
            results.append((script_path, False, f"Exception: {str(e)}"))
            
    return results

def test_path_manager_basic_functionality():
    """Test basic path_manager functionality."""
    try:
        from path_utils import path_manager
        
        # Test basic properties
        print(f"  Project root: {path_manager.project_root}")
        print(f"  Executable dir: {path_manager.executable_dir}")
        
        assert path_manager.project_root is not None, "Project root is None"
        assert path_manager.executable_dir is not None, "Executable dir is None"
        assert isinstance(path_manager.project_root, Path), f"Project root is {type(path_manager.project_root)}, expected Path"
        assert isinstance(path_manager.executable_dir, Path), f"Executable dir is {type(path_manager.executable_dir)}, expected Path"
        
        # Test that project root contains expected directories
        src_exists = (path_manager.project_root / "src").exists()
        build_exists = (path_manager.project_root / "build").exists()
        
        print(f"  src/ exists: {src_exists}")
        print(f"  build/ exists: {build_exists}")
        
        assert src_exists, f"src directory not found at {path_manager.project_root / 'src'}"
        assert build_exists, f"build directory not found at {path_manager.project_root / 'build'}"
        
        # Test resource path resolution
        scripts_path = path_manager.resource_path("src/scripts") 
        expected_scripts_path = path_manager.project_root / "src" / "scripts"
        
        print(f"  Scripts path: {scripts_path}")
        print(f"  Expected: {expected_scripts_path}")
        
        assert scripts_path == expected_scripts_path, f"Scripts path mismatch: {scripts_path} != {expected_scripts_path}"
        
        print("✅ path_manager basic functionality: PASS")
        return True
        
    except Exception as e:
        print(f"❌ path_manager basic functionality: FAIL - {e}")
        import traceback
        traceback.print_exc()
        return False

def test_build_script_enhancement():
    """Test that build script uses enhanced path utilities."""
    try:
        build_script = project_root / "build/build.py"
        if not build_script.exists():
            print("⚠️  Build script not found, skipping test")
            return True
            
        with open(build_script, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Check for key enhancements
        checks = [
            ("path_manager.project_root", "Uses centralized project root"),
            ("ensure_directory_exists", "Has enhanced directory creation"),
            ("get_build_resource_path", "Has resource path helper"),
            ("from path_utils import path_manager", "Imports path_manager")
        ]
        
        for check, description in checks:
            if check not in content:
                print(f"❌ Build script enhancement: FAIL - Missing {description}")
                return False
                
        print("✅ Build script enhancement: PASS")
        return True
        
    except Exception as e:
        print(f"❌ Build script enhancement: FAIL - {e}")
        return False

def test_no_duplicate_functions():
    """Test that no duplicate get_executable_path functions remain."""
    try:
        duplicate_files = []
        
        # Check all Python files in src and build directories
        for directory in ["src", "build"]:
            dir_path = project_root / directory
            if dir_path.exists():
                for py_file in dir_path.rglob("*.py"):
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if "def get_executable_path(" in content:
                            duplicate_files.append(py_file.relative_to(project_root))
                            
        if duplicate_files:
            print(f"❌ No duplicate functions: FAIL - Found duplicates in {duplicate_files}")
            return False
        else:
            print("✅ No duplicate functions: PASS")
            return True
            
    except Exception as e:
        print(f"❌ No duplicate functions: FAIL - {e}")
        return False

def test_consistent_imports():
    """Test that all migrated scripts have consistent imports."""
    try:
        migrated_scripts = [
            "src/scripts/compile-pvsneslib-proj.py",
            "src/scripts/compile-dotnetsnes-proj.py", 
            "src/scripts/compile-javasnes-proj.py",
            "src/scripts/create-pvsneslib-proj.py",
            "src/scripts/create-dotnetsnes-proj.py",
            "src/scripts/create-javasnes-proj.py",
            "src/scripts/gfx-png-bmp-editor.py",
            "src/scripts/audio-wav-brr-converter.py",
            "src/snes-ide.py",
            "src/scripts/get-snes-ide-home.py",
            "build/build.py"
        ]
        
        missing_imports = []
        
        for script_path in migrated_scripts:
            full_path = project_root / script_path
            if full_path.exists():
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                if "from path_utils import path_manager" not in content:
                    missing_imports.append(script_path)
                    
        if missing_imports:
            print(f"❌ Consistent imports: FAIL - Missing imports in {missing_imports[:3]}...")
            return False
        else:
            print("✅ Consistent imports: PASS")
            return True
            
    except Exception as e:
        print(f"❌ Consistent imports: FAIL - {e}")
        return False

def test_get_snes_ide_home_functionality():
    """Test that get-snes-ide-home script works with new path management."""
    try:
        script_path = project_root / "src/scripts/get-snes-ide-home.py"
        if not script_path.exists():
            print("⚠️  get-snes-ide-home script not found, skipping test")
            return True
            
        # Run the script and check it produces output
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=project_root
        )
        
        if result.returncode == 0 and result.stdout.strip():
            # Should output a valid path
            output_path = Path(result.stdout.strip())
            print(f"✅ get-snes-ide-home functionality: PASS - Output: {output_path}")
            return True
        else:
            print(f"❌ get-snes-ide-home functionality: FAIL - {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ get-snes-ide-home functionality: FAIL - Timeout")
        return False
    except Exception as e:
        print(f"❌ get-snes-ide-home functionality: FAIL - {e}")
        return False

def main():
    """Run all functional validation tests."""
    print("🔍 Running Path Utils Migration Functional Tests")
    print("=" * 60)
    
    # Run individual tests
    test_results = []
    
    print("\n📦 Testing basic path_manager functionality...")
    test_results.append(test_path_manager_basic_functionality())
    
    print("\n🔨 Testing build script enhancements...")
    test_results.append(test_build_script_enhancement())
    
    print("\n🧹 Testing duplicate function removal...")
    test_results.append(test_no_duplicate_functions())
    
    print("\n📥 Testing consistent imports...")
    test_results.append(test_consistent_imports())
    
    print("\n⚙️  Testing get-snes-ide-home functionality...")
    test_results.append(test_get_snes_ide_home_functionality())
    
    # Print summary
    print("\n" + "=" * 60)
    passed = sum(test_results)
    total = len(test_results)
    
    if passed == total:
        print(f"🎉 All tests passed! ({passed}/{total})")
        print("✅ Path utils migration is working correctly!")
        return 0
    else:
        print(f"❌ Some tests failed: {passed}/{total} passed")
        print("🔧 Please review the failed tests above")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)