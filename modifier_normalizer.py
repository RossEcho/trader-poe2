import re


ROLL_RANGE_RE = re.compile(r"\([^)]*\)")
NUMBER_RE = re.compile(r"(?<![#A-Za-z])([+-]?\d+(?:\.\d+)?)")


def normalize_modifier(modifier_text):
    cleaned = ROLL_RANGE_RE.sub("", modifier_text).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return NUMBER_RE.sub(_replace_number, cleaned)


def extract_modifier_values(modifier_text):
    cleaned = ROLL_RANGE_RE.sub("", modifier_text).strip()
    values = []
    for match in NUMBER_RE.finditer(cleaned):
        value = match.group(1)
        if value.startswith("+"):
            value = value[1:]
        values.append(value)
    return values


def _replace_number(match):
    value = match.group(1)
    if value.startswith("+"):
        return "+#"
    if value.startswith("-"):
        return "-#"
    return "#"
