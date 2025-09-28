from setuptools import setup

APP = ["src/snes-ide.py"]

OPTIONS = {
    'argv_emulation': True,
    'iconfile': 'assets/icons/icon.icns' if False else None,
    'resources': [
        'icons',
        'src/tools',
        'libs'
    ],
    'packages': [],
}

setup(
    name='SNES-IDE',
    app=APP,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
