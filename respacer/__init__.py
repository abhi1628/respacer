"""
respacer
~~~~~~~~
Fix missing spaces in text extracted/converted from PDFs
(e.g. "ThisisaparagraphaboutAI" -> "This is a paragraph about AI"),
while preserving document formatting.
"""

from .segmenter import respace_text
from .detector import needs_respacing

__version__ = "0.1.0"

__all__ = ["respace_text", "needs_respacing", "__version__"]
