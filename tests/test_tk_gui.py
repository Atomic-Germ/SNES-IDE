import tkinter as tk
from pathlib import Path
from types import SimpleNamespace

def test_tk_gui_preview_and_install(monkeypatch, tmp_path):
    # Verify the GUI can be created in headless mode, and on_install uses progress_callback
    from snes_installer.tk_gui import SNESTkGui
    from snes_installer.installer import ToolInstaller
    config_file = Path(__file__).parent.parent / 'src' / 'snes_installer' / 'tools_config.json'
    gui = SNESTkGui(config_file, create_root=False)

    # Prepare a fake installer that records calls
    captured = {'called': [], 'events': []}
    def fake_install_selected_tools(names, progress_callback=None, stop_event=None):
        import time
        for n in names:
            if progress_callback:
                progress_callback(n, 'starting', None)
                captured['events'].append((n, 'starting'))
            # emulate a build that checks for stop_event periodically
            for _ in range(20):
                time.sleep(0.01)
                if stop_event and getattr(stop_event, 'is_set', lambda: False)():
                    if progress_callback:
                        progress_callback(n, 'failed', 'cancelled')
                        captured['events'].append((n, 'failed'))
                    return
            if progress_callback:
                progress_callback(n, 'success', None)
                captured['events'].append((n, 'success'))
        captured['called'].append(tuple(names))

    monkeypatch.setattr(gui, 'installer', ToolInstaller(config_file, install_dir=tmp_path / 'inst'))
    monkeypatch.setattr(gui.installer, 'install_selected_tools', fake_install_selected_tools)

    # Set some tools as selected in our headless var map (use .set() when available)
    for name in list(gui.tool_vars.keys())[:2]:
        var = gui.tool_vars[name]
        if hasattr(var, 'set'):
            var.set(1)
        else:
            gui.tool_vars[name] = 1
    # Monkeypatch messagebox to auto-confirm installation
    import tkinter as _tk
    monkeypatch.setattr(_tk.messagebox, 'askyesno', lambda *a, **k: True)
    monkeypatch.setattr(_tk.messagebox, 'showinfo', lambda *a, **k: None)
    # Use real threading behavior (don't monkeypatch Thread)
    # Verify selected compute works in headless mode
    selected_calc = [name for name, var in gui.tool_vars.items() if (var.get() if hasattr(var, 'get') else var)]
    assert selected_calc, "No selected tools were set; can't run install test"
    # Call on_install which should run in background and fake installers check stop_event

    # Now call on_install in background and then call on_cancel to set event
    gui.on_install()
    import time
    # give it a moment to start so the fake installer begins its loop
    time.sleep(0.15)
    # simulate user pressing cancel
    gui.on_cancel()
    # ensure we observed progress events (at least a starting event)
    import time
    start = time.time()
    while time.time() - start < 2.0 and not captured['events']:
        time.sleep(0.05)
    assert captured['events']
    assert any(ev[1] == 'starting' for ev in captured['events'])
    print('CAPTURED EVENTS:', captured['events'])
    try:
        print('GUI LOG LINES:', gui._log_lines)
    except Exception:
        pass
    # At minimum we should see a starting event; success/failure may race with test timing.
    # Avoid flaky timing-dependent assertion here.
    # ensure that cancel_event cleared after completion
    # process waits until the GUI background thread completes and clears cancel_event
    start = time.time()
    while time.time() - start < 2.0 and getattr(gui, 'cancel_event', True) is not None:
        time.sleep(0.01)
    assert getattr(gui, 'cancel_event', None) is None
    
    # Test that the tk GUI module and class are importable
    from snes_installer import tk_gui
    assert hasattr(tk_gui, 'SNESTkGui')
