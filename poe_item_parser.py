import re


EXPLICIT_MODIFIER_RE = re.compile(
    r"^\{\s*(?:(?:Desecrated|Crafted)\s+)?(?:Prefix|Suffix)\s+Modifier\b[^}]*\}\s*$",
    re.IGNORECASE,
)


def looks_like_poe_item(text):
    if not text or not isinstance(text, str):
        return False

    required_markers = ("Item Class:", "Rarity:", "--------")
    return all(marker in text for marker in required_markers)


def parse_item_class(item_text):
    if not item_text or not isinstance(item_text, str):
        return None

    for line in item_text.splitlines():
        line = line.strip()
        if line.startswith("Item Class:"):
            item_class = line.split(":", 1)[1].strip()
            return item_class or None

    return None


def parse_explicit_modifiers(item_text):
    if not looks_like_poe_item(item_text):
        return []

    lines = [line.strip() for line in item_text.splitlines()]
    modifiers = []

    for index, line in enumerate(lines[:-1]):
        if not EXPLICIT_MODIFIER_RE.match(line):
            continue

        raw_modifier = lines[index + 1].strip()
        if raw_modifier and not raw_modifier.startswith("{") and raw_modifier != "--------":
            modifiers.append(raw_modifier)

    return modifiers
