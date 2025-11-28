def test_parse_info_input():
    from snes_installer.tui import parse_info_input

    assert parse_info_input("info 1") == 1
    assert parse_info_input("i 2") == 2
    assert parse_info_input("details 3") == 3
    assert parse_info_input("d 4") == 4
    assert parse_info_input("info") is None
    assert parse_info_input("info x") is None
    assert parse_info_input("") is None
