"""
detector.py
-----------
Decides WHICH tokens in a document are actually broken (missing spaces)
vs. tokens that only look suspicious but should be left alone
(URLs, emails, code identifiers, numbers, already-normal words).

This exists because a naive "run every long word through a segmenter"
approach corrupts URLs, camelCase variable names, and proper nouns.
"""

import re
import wordninja

_URL_RE = re.compile(r"^(https?://|www\.)\S+$", re.IGNORECASE)
_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_NUMERIC_RE = re.compile(r"^[\d.,:/\-+%$]+$")
_HAS_DIGIT_RE = re.compile(r"\d")
_SNAKE_OR_KEBAB_RE = re.compile(r"[_\-]")
_PURE_ALPHA_RE = re.compile(r"^[A-Za-z]+$")

# Minimum length before we even consider a token "suspicious".
# Real English words are almost never this long; merged PDF text is.
DEFAULT_MIN_LENGTH = 12


def _looks_like_code_or_identifier(token: str) -> bool:
    """snake_case, kebab-case, or tokens mixing letters+digits like 'v2.1' or 'GROQ_API_KEY'."""
    if _SNAKE_OR_KEBAB_RE.search(token):
        return True
    if _HAS_DIGIT_RE.search(token):
        return True
    return False


def needs_respacing(token: str, min_length: int = DEFAULT_MIN_LENGTH) -> bool:
    """
    Return True if `token` is a candidate for space-repair.

    A token is a candidate only if:
      - it's pure alphabetic (no digits/punctuation glued in)
      - it's not a URL or email
      - it's not snake_case/kebab-case or otherwise code-like
      - it's at least `min_length` characters long
    """
    if not token or not _PURE_ALPHA_RE.match(token):
        return False
    if _URL_RE.match(token) or _EMAIL_RE.match(token):
        return False
    if _NUMERIC_RE.match(token):
        return False
    if _looks_like_code_or_identifier(token):
        return False
    if len(token) < min_length:
        return False
    return True


def segmentation_confidence(original: str, words: list) -> float:
    """
    Score a wordninja segmentation from 0.0 (reject) to 1.0 (confident).

    Rejects/penalizes:
      - any resulting fragment of length 1 that isn't 'a' or 'i'
      - segmentations that don't preserve all original characters
      - segmentations with an unusually high proportion of very short words
        (a common sign of "false split", e.g. 'Bader i a Global Institute')
    """
    if not words:
        return 0.0

    rebuilt = "".join(words)
    if rebuilt.lower() != original.lower():
        return 0.0  # characters were lost/changed -- never trust this

    single_letter_junk = sum(
        1 for w in words if len(w) == 1 and w.lower() not in ("a", "i")
    )
    if single_letter_junk > 0:
        return 0.0

    short_word_ratio = sum(1 for w in words if len(w) <= 2) / len(words)
    avg_len = len(rebuilt) / len(words)

    score = 1.0
    score -= short_word_ratio * 0.6
    if avg_len < 2.5:
        score -= 0.3

    return max(0.0, min(1.0, score))
