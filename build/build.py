# ...existing code...

def copy_sh() -> None:
    """
    Copy POSIX shell wrapper files (.sh) from src/tools to SNES-IDE-out/tools so
    macOS builds include the expected POSIX wrappers.
    """
    (SNESIDEOUT / 'tools').mkdir(exist_ok=True)

    for file in (ROOT / 'src' / 'tools').rglob("*.sh"):

        if file.is_dir():
            continue

        rel_path = file.relative_to(ROOT / 'src' / 'tools')
        dest_path = SNESIDEOUT / 'tools' / rel_path
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(file, dest_path)
        try:
            dest_path.chmod(dest_path.stat().st_mode | 0o111)
        except Exception:
            pass
        print_step(f"Copied shell wrapper: {file} -> {dest_path}")
    return None


def copy_dlls() -> None:
    """
    Copy the dlls from tools dir (Windows only). On non-Windows targets this
    operation is skipped to avoid polluting macOS builds with Windows artifacts.
    """
    sys_platform = platform.system().lower()
    if sys_platform != 'windows':
        print_step("Skipping DLL copy: non-Windows target detected")
        return None

    (SNESIDEOUT / 'tools').mkdir(exist_ok=True)

    for file in (ROOT / 'tools').rglob("*.dll"):

        if file.is_dir():

            continue

        rel_path = file.relative_to(ROOT / 'tools')

        dest_path = SNESIDEOUT / 'tools' / rel_path

        dest_path.parent.mkdir(parents=True, exist_ok=True)

        shutil.copy(file, dest_path)
    
    return None

# ...existing code...

def main() -> int:
    """
    Main function to run the build process.
    """
    steps = [
        ("Cleaning SNES-IDE-out", clean_all),
        ("Copying root files", copy_root),
        ("Copying libs", copy_lib),
        ("Copying docs", copy_docs),
        ("Copying bat files", copy_bat),
        ("Copying sh files", copy_sh),
        ("Copying dlls", copy_dlls),
        ("Copying tracker", copyTracker),
        ("Compiling python files", compile),
    ]
# ...existing code...