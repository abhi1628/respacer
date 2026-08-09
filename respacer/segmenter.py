"""
segmenter.py
------------
Dictionary/frequency-based word segmentation (via wordninja's Viterbi
algorithm) with a confidence gate, plus casing restoration.

This is the fast, free, no-API-key path. It's intentionally conservative:
low-confidence splits are left untouched rather than guessed at, so the
LLM enhancer (optional) can take a second pass at just those tokens.
"""

import re
import wordninja

from .detector import needs_respacing, segmentation_confidence, DEFAULT_MIN_LENGTH

_WORD_SPLIT_RE = re.compile(r"(\w+|[^\w\s]+|\s+)")

MIN_CONFIDENCE = 0.55


def _restore_casing(original: str, words: list) -> list:
    """
    wordninja lowercases everything internally for lookup but we want to
    preserve the reader's original capitalization pattern as closely as
    possible (e.g. keep an all-caps acronym-like run in caps, keep the
    leading capital on a sentence).
    """
    result = []
    pos = 0
    for w in words:
        segment = original[pos: pos + len(w)]
        result.append(segment)
        pos += len(w)
    return result


def segment_token(token: str, min_length: int = DEFAULT_MIN_LENGTH):
    """
    Attempt to split a single glued-together token into separate words.

    Returns:
        (fixed_string, was_changed: bool, confidence: float)
    """
    if not needs_respacing(token, min_length=min_length):
        return token, False, 0.0

    raw_words = wordninja.split(token)
    confidence = segmentation_confidence(token, raw_words)

    if confidence < MIN_CONFIDENCE or len(raw_words) < 2:
        return token, False, confidence

    cased_words = _restore_casing(token, raw_words)
    cased_words = _merge_acronym_runs(cased_words)

    if len(cased_words) < 2:
        return token, False, confidence

    return " ".join(cased_words), True, confidence


def _merge_acronym_runs(words: list) -> list:
    """
    Consecutive single-uppercase-letter segments (e.g. wordninja splitting
    'AI' into 'A', 'I') are almost always a mis-split acronym, not two
    real one-letter words. Merge runs of 2+ such segments back together.
    """
    merged = []
    buffer = []

    def flush():
        if buffer:
            merged.append("".join(buffer))
            buffer.clear()

    for w in words:
        if len(w) == 1 and w.isupper():
            buffer.append(w)
        else:
            flush()
            merged.append(w)
    flush()
    return merged


def respace_text(text: str, min_length: int = DEFAULT_MIN_LENGTH, return_report: bool = False):
    """
    Walk a block of text and repair any glued-together tokens, leaving
    punctuation, whitespace, URLs, numbers, and normal words untouched.

    Args:
        text: input string (a paragraph, a run, a page, etc.)
        min_length: minimum token length to even consider fixing
        return_report: if True, also return a list of changes made

    Returns:
        fixed_text (str)                          if return_report=False
        (fixed_text, report: list[dict])           if return_report=True
    """
    pieces = _WORD_SPLIT_RE.findall(text)
    output = []
    report = []

    for piece in pieces:
        if piece.isspace() or not re.match(r"\w", piece):
            output.append(piece)
            continue

        fixed, changed, confidence = segment_token(piece, min_length=min_length)
        output.append(fixed)
        if changed:
            report.append(
                {"original": piece, "fixed": fixed, "confidence": round(confidence, 2)}
            )

    fixed_text = "".join(output)
    if return_report:
        return fixed_text, report
    return fixed_text
