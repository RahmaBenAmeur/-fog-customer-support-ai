"""
transcript_cleanup.py  -  fixes what Whisper writes for order numbers and emails.

Whisper writes what it hears, not the format our system needs:
    "ORD 001", "ORD-001", "O-R-D-001", "O R D 0 0 1"   ->  ORD001
    "alice at example dot com", "alice @ example . com" ->  alice@example.com
    "A L I C E at example dot com"                      ->  alice@example.com

It is called by whisper_service.py on every transcription, before the text
reaches the chatbot.

Limits (cannot be fixed by code): if Whisper hears different WORDS
(e.g. "elishatexample.com" for "alice at example.com") nothing here can guess
the right name. In that case the customer should spell the name letter by
letter ("A L I C E at example dot com") or type the email.
"""

import re

# separators Whisper puts between letters / digits
_SEP = r"[\s.\-]*"

# ORD 001 | ORD-001 | O-R-D-001 | O.R.D. 001 | O R D 0 0 1
# (the last letter may be heard as T, B or P: "ORT-001", "ORB 001")
_ORDER_ID = re.compile(
    r"\b[Oo]" + _SEP + r"[Rr]" + _SEP + r"[DdTtBbPp]" + _SEP + r"(\d(?:[\s.\-]?\d)*)"
)

# "order 001" (Whisper sometimes writes the word "order" for "ORD"): 3+ digits only
_ORDER_WORD = re.compile(r"\b[Oo]rder[\s\-]*(\d{3,})\b")

_TLDS = "com|net|org|tn|fr|info|io|co|edu|gov|me|biz"

# letters spelled one by one in front of a real email ending:  A L I C E at example dot com
_SPELLED = re.compile(
    r"(?<![A-Za-z0-9])((?:[A-Za-z0-9][\s.\-]+){2,}[A-Za-z0-9])"
    r"(?=\s*(?:@|\bat\b)\s*[A-Za-z0-9\-]+\s*(?:\.|\bdot\b)\s*(?:" + _TLDS + r")\b)",
    re.IGNORECASE,
)

# local part + (@ | at) + domain + (. | dot) + tld
_EMAIL = re.compile(
    r"(?P<local>[A-Za-z0-9._+\-]+)\s*(?:@|\bat\b)\s*(?P<domain>[A-Za-z0-9\-]+)"
    r"\s*(?:\.|\bdot\b)\s*(?P<tld>(?:" + _TLDS + r"))\b",
    re.IGNORECASE,
)

# "look at store.com", "bought it at amazon.com" are not emails
_NOT_A_LOCAL_PART = {
    "look", "looked", "looking", "bought", "ordered", "arrived", "available",
    "found", "seen", "it", "them", "that", "this", "here", "there", "home",
    "work", "stay", "stayed", "me", "us", "you", "him", "her", "is", "was",
    "are", "were", "be", "been", "i", "we", "they", "he", "she",
}


def _fix_order_id(match):
    digits = re.sub(r"[\s.\-]", "", match.group(1))
    return "ORD" + digits


def _fix_spelled(match):
    return re.sub(r"[\s.\-]", "", match.group(1))


def _fix_email(match):
    if match.group("local").lower() in _NOT_A_LOCAL_PART:
        return match.group(0)
    return f"{match.group('local')}@{match.group('domain')}.{match.group('tld')}".lower()


def normalize_transcript(text):
    """Return the transcription with order numbers and emails in a clean format."""
    if not text:
        return text

    text = _ORDER_ID.sub(_fix_order_id, text)
    text = _ORDER_WORD.sub(lambda m: "ORD" + m.group(1), text)
    text = _SPELLED.sub(_fix_spelled, text)
    text = _EMAIL.sub(_fix_email, text)
    return text
