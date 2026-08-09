"""
llm_enhancer.py
----------------
OPTIONAL second pass. The dictionary segmenter (segmenter.py) is fast,
free, and requires no API key, but it deliberately refuses to guess on
low-confidence tokens (proper nouns, jargon, ambiguous acronyms like the
CamelCase-vs-broken-title problem). This module sends ONLY those
unresolved paragraphs to an LLM (via Groq, since it's fast/cheap) for a
context-aware fix.

This is intentionally NOT used by default. Nothing in this package makes
a network call unless you explicitly pass an API key.
"""

import json
import requests

from .segmenter import respace_text
from .detector import needs_respacing, DEFAULT_MIN_LENGTH

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = "llama-3.1-8b-instant"

_SYSTEM_PROMPT = (
    "You fix missing spaces in text that was badly extracted from a PDF. "
    "Insert spaces where words have been incorrectly glued together. "
    "Do NOT change spelling, wording, punctuation, or add/remove any content. "
    "Do NOT touch URLs, emails, or code-like tokens. "
    "Return ONLY the corrected text, nothing else -- no preamble, no explanation."
)


def _still_broken(text: str, min_length: int) -> bool:
    """Check whether a paragraph still contains an unresolved glued token."""
    for token in text.split():
        cleaned = "".join(ch for ch in token if ch.isalpha())
        if needs_respacing(cleaned, min_length=min_length):
            return True
    return False


def enhance_paragraph(text: str, api_key: str, model: str = DEFAULT_MODEL, timeout: int = 30) -> str:
    """
    Send a single paragraph to Groq for a context-aware space fix.
    Only call this on paragraphs the dictionary pass couldn't resolve --
    it costs tokens and is slower than the local segmenter.
    """
    if not api_key:
        raise ValueError("A Groq API key is required for LLM enhancement.")

    resp = requests.post(
        GROQ_URL,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
        },
        timeout=timeout,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"].strip()


def respace_text_with_llm(
    text: str,
    api_key: str,
    min_length: int = DEFAULT_MIN_LENGTH,
    model: str = DEFAULT_MODEL,
) -> str:
    """
    Hybrid pipeline: run the free dictionary segmenter first, and only
    fall back to the LLM for paragraphs that are still broken afterward.
    This keeps API usage (and cost) proportional to how ambiguous the
    document actually is, rather than sending everything to the LLM.
    """
    fixed = respace_text(text, min_length=min_length)
    if _still_broken(fixed, min_length=min_length):
        try:
            return enhance_paragraph(fixed, api_key=api_key, model=model)
        except requests.RequestException:
            # Network/API failure -- fall back to the local best-effort result
            return fixed
    return fixed
