from pathlib import Path

def test_show_main_menu_questionary(monkeypatch):
    from snes_installer.tui import SNESInstallerTUI
    config_file = Path(__file__).parent.parent / 'src' / 'snes_installer' / 'tools_config.json'
    tui = SNESInstallerTUI(config_file, dry_run=True)

    class FakeQuestionary:
        @staticmethod
        def select(prompt, choices):
            class Choice:
                def __init__(self, title):
                    self.title = title
                def ask(self):
                    return choices[0]
            return Choice(choices[0])

    monkeypatch.setitem(__import__('sys').modules, 'questionary', FakeQuestionary)
    res = tui.show_main_menu()
    assert res == 'install_all'


def test_show_main_menu_numeric_fallback(monkeypatch):
    from snes_installer.tui import SNESInstallerTUI
    from rich.prompt import Prompt
    config_file = Path(__file__).parent.parent / 'src' / 'snes_installer' / 'tools_config.json'
    tui = SNESInstallerTUI(config_file, dry_run=True)

    # Make questionary not importable
    import sys
    sys.modules.pop('questionary', None)

    # Monkeypatch Prompt.ask to return '1'
    monkeypatch.setattr(Prompt, 'ask', lambda *a, **k: '1')
    res = tui.show_main_menu()
    assert res == 'install_all'
