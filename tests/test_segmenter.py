from respacer.segmenter import respace_text
from respacer.detector import needs_respacing


def test_basic_glued_sentence():
    out = respace_text("ThisisaparagraphaboutAI")
    assert out == "This is a paragraph about AI"


def test_leaves_urls_alone():
    text = "Visit https://zeroapi.in/tool today"
    assert respace_text(text) == text


def test_leaves_emails_alone():
    text = "Contact hello@zeroapi.in for help"
    assert respace_text(text) == text


def test_leaves_normal_prose_alone():
    text = "This sentence is completely normal and should not change at all."
    assert respace_text(text) == text


def test_leaves_snake_case_alone():
    text = "Set the GROQ_API_KEY environment variable"
    assert respace_text(text) == text


def test_short_tokens_untouched():
    # below default min_length -- ambiguous short strings are left alone
    assert needs_respacing("cat") is False
    assert needs_respacing("thisislongenough") is True


def test_no_characters_lost():
    original = "Baderiaglobalinstituteofengineeringandmanagement"
    fixed = respace_text(original)
    assert fixed.replace(" ", "").lower() == original.lower()
