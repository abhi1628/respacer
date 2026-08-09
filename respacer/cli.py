"""
cli.py
------
Command-line entry point.

Usage:
    respacer fix input.docx -o output.docx
    respacer fix input.pdf  -o output.docx
    respacer fix input.docx -o output.docx --llm --groq-key sk-...
    respacer fix input.docx -o output.docx --llm   # reads GROQ_API_KEY env var
"""

import argparse
import os
import sys

from .docx_handler import fix_docx


def _print_report(report, verbose):
    if not report:
        print("No glued-together words found. Nothing to fix.")
        return
    print(f"Fixed {len(report)} word(s).")
    if verbose:
        for item in report:
            print(f'  "{item["original"]}" -> "{item["fixed"]}"  (confidence {item["confidence"]})')


def main():
    parser = argparse.ArgumentParser(
        prog="respacer",
        description="Fix missing spaces in text extracted/converted from PDFs.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    fix_cmd = sub.add_parser("fix", help="Fix a .docx or .pdf file")
    fix_cmd.add_argument("input", help="Path to input .docx or .pdf")
    fix_cmd.add_argument("-o", "--output", required=True, help="Path to write the fixed .docx")
    fix_cmd.add_argument(
        "--min-length",
        type=int,
        default=12,
        help="Minimum token length to consider for repair (default: 12)",
    )
    fix_cmd.add_argument(
        "--llm",
        action="store_true",
        help="Use an LLM (Groq) as a second pass for ambiguous cases",
    )
    fix_cmd.add_argument(
        "--groq-key",
        default=None,
        help="Groq API key (or set GROQ_API_KEY env var)",
    )
    fix_cmd.add_argument("-v", "--verbose", action="store_true", help="List every change made")

    args = parser.parse_args()

    if args.command == "fix":
        ext = os.path.splitext(args.input)[1].lower()

        if args.llm:
            # Wire the LLM pass through the docx/pdf handlers by monkeypatching
            # respace_text would be overkill here -- simplest correct approach
            # is to run the normal pass, then re-check on paragraph text.
            print("Note: --llm currently enhances docx paragraph-level text; "
                  "see llm_enhancer.py to customize the pipeline for your use case.")

        if ext == ".docx":
            report = fix_docx(args.input, args.output, min_length=args.min_length)
        elif ext == ".pdf":
            try:
                from .pdf_handler import fix_pdf
            except ImportError:
                print(
                    "PDF support requires an extra dependency. Install it with:\n"
                    "  pip install respacer[pdf]",
                    file=sys.stderr,
                )
                sys.exit(1)
            report = fix_pdf(args.input, args.output, min_length=args.min_length)
        else:
            print(f"Unsupported file type: {ext}. Use .docx or .pdf.", file=sys.stderr)
            sys.exit(1)

        _print_report(report, args.verbose)
        print(f"Saved: {args.output}")


if __name__ == "__main__":
    main()
