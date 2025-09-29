from pathlib import Path


def test_devkitsnes_tools_present():
    """Fail until the pvsneslib/devkitsnes contains at least one expected executable.

    Expected tools: wla-65816, wlalink, 816-tcc (with or without .exe suffix).
    """
    base = Path('libs') / 'pvsneslib' / 'devkitsnes'
    assert base.exists() and base.is_dir(), (
        'pvsneslib devkitsnes directory missing - CI must download/extract devkitsnes into libs/pvsneslib/devkitsnes/'
    )

    candidates = list(base.rglob('wla-65816*')) + list(base.rglob('wlalink*')) + list(base.rglob('816-tcc*'))
    # Filter to executable files
    execs = [p for p in candidates if p.is_file() and p.exists()]
    assert execs, (
        'No devkit tool executables found (wla-65816, wlalink, 816-tcc); build/provide them in libs/pvsneslib/devkitsnes/'
    )
    # Optional: ensure at least one is executable on POSIX
    assert any(p.stat().st_mode & 0o111 for p in execs), 'Found devkit files but none are executable; CI should chmod +x them'
