import re


def extract_order_id(text):
    match = re.search(r"\bORD\d+\b", text.upper())

    if match:
        return match.group(0)

    return None