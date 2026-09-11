from pathlib import Path

from modifier_normalizer import extract_modifier_values, normalize_modifier
from poe_item_parser import looks_like_poe_item, parse_explicit_modifiers
from trader_logic import format_decrement_value, parse_decrement_value


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "sample_item.txt"


def test_parse_sample_explicit_modifiers_only():
    item_text = FIXTURE_PATH.read_text(encoding="utf-8")

    assert parse_explicit_modifiers(item_text) == [
        "+114(105-124) to maximum Mana",
        "+145(120-149) to maximum Life",
        "+77(71-79) to maximum Energy Shield",
        "+34(31-35)% to Fire Resistance",
        "19(19-21)% increased Cast Speed",
        "17(15-18)% increased Rarity of Items found",
    ]


def test_normalize_sample_modifiers():
    item_text = FIXTURE_PATH.read_text(encoding="utf-8")

    assert [normalize_modifier(modifier) for modifier in parse_explicit_modifiers(item_text)] == [
        "+# to maximum Mana",
        "+# to maximum Life",
        "+# to maximum Energy Shield",
        "+#% to Fire Resistance",
        "#% increased Cast Speed",
        "#% increased Rarity of Items found",
    ]


def test_extract_sample_values():
    item_text = FIXTURE_PATH.read_text(encoding="utf-8")

    assert [extract_modifier_values(modifier) for modifier in parse_explicit_modifiers(item_text)] == [
        ["114"],
        ["145"],
        ["77"],
        ["34"],
        ["19"],
        ["17"],
    ]


def test_normalize_edge_cases():
    assert normalize_modifier("-12.5(10-15)% to Fire Resistance") == "-#% to Fire Resistance"
    assert normalize_modifier("Adds 3(1-4) to 7(5-9) Fire Damage") == "Adds # to # Fire Damage"
    assert normalize_modifier("Cannot be Frozen") == "Cannot be Frozen"
    assert extract_modifier_values("-12.5(10-15)% to Fire Resistance") == ["-12.5"]
    assert extract_modifier_values("Adds 3(1-4) to 7(5-9) Fire Damage") == ["3", "7"]


def test_malformed_clipboard_is_not_an_item():
    assert not looks_like_poe_item("hello")
    assert parse_explicit_modifiers("hello") == []


def test_decrement_value_helpers():
    assert format_decrement_value(parse_decrement_value("114") - 1) == "113"
    assert format_decrement_value(parse_decrement_value("1.5") - 1) == "0.5"
    assert parse_decrement_value(None) is None
