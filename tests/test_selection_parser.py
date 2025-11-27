def test_parse_selection_input():
    from snes_installer.tui import parse_selection_input
    from typing import List, Dict

    tools = [
        {"name": "a"},
        {"name": "b"},
        {"name": "c"},
        {"name": "d"}
    ]

    # single index
    assert parse_selection_input("1", tools) == ["a"]
    # multiple indices
    assert parse_selection_input("1,3", tools) == ["a","c"]
    # ranges
    assert parse_selection_input("1-3", tools) == ["a","b","c"]
    # combined
    assert parse_selection_input("1,3-4", tools) == ["a","c","d"]
    # all
    assert parse_selection_input("all", tools) == ["a","b","c","d"]
    # synonyms
    assert parse_selection_input("install all", tools) == ["a","b","c","d"]
    # back / empty
    assert parse_selection_input("", tools) == []
    assert parse_selection_input("back", tools) == []
    # invalid inputs
    assert parse_selection_input("x", tools) == []
    assert parse_selection_input("5", tools) == []
    # fallback for multi-select: empty meaning no selection
    assert parse_selection_input("", tools) == []
