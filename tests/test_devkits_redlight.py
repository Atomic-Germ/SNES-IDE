from pathlib import Path


def test_devkitsnes_present():
    """Fail until the pvsneslib/devkitsnes artifacts are provided in libs/ for macOS CI."""
    base = Path('libs') / 'pvsneslib' / 'devkitsnes'
    assert base.exists() and any(base.rglob('*')), (
        'pvsneslib devkitsnes files missing - CI must download/extract devkitsnes into libs/pvsneslib/devkitsnes/'
    )
