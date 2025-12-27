# app/text_cleaner.py
from __future__ import annotations
import re


_CONTROL_CODE_PATTERNS = [
    r"[\\¥￥＼]C\[\d+\]",   # \C[2] color
    r"[\\¥￥＼]V\[\d+\]",   # \V[1] variable
    r"[\\¥￥＼]N\[\d+\]",   # \N[3] actor name
    r"[\\¥￥＼]P\[\d+\]",   # \P[1] party member name (some plugins)
    r"[\\¥￥＼]I\[\d+\]",   # \I[10] icon
    r"[\\¥￥＼]G",          # \G currency unit
    r"[\\¥￥＼]\.",         # \. short wait
    r"[\\¥￥＼]\|",         # \| long wait
    r"[\\¥￥＼]!",          # \! wait for input
    r"[\\¥￥＼]>",          # \> fast
    r"[\\¥￥＼]<",          # \< slow
    r"[\\¥￥＼]\^",         # \^ close message
    r"[\\¥￥＼]\$"          # \$ open gold window
]

_TEXTSIZE = re.compile(r"[\\¥￥＼][{}]")  # \{ \}
_SPACES = re.compile(r"[ \t]+")


def _normalize_backslash_variants(text: str) -> str:
    r"""
    Normalize backslash-like characters often seen on Windows/Japanese locales.
    Converts ¥/￥/＼ into the standard backslash \.
    """
    return (text
            .replace("¥", "\\")
            .replace("￥", "\\")
            .replace("＼", "\\"))


def _convert_literal_newlines(text: str) -> str:
    """
    Convert literal newline tokens into actual newline chars.
    Handles both:
      - "\\n"  (single slash + n)
      - "\\\\n" (double slash + n)
    """
    # Handle double-backslash first, then single-backslash
    text = re.sub(r"\\\\n", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"\\n", "\n", text, flags=re.IGNORECASE)
    return text


def clean_control_codes(text: str) -> str:
    if not text:
        return ""

    # Normalize line breaks
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Normalize backslash variants first (IMPORTANT)
    text = _normalize_backslash_variants(text)

    # Convert literal newline tokens to actual newline
    text = _convert_literal_newlines(text)

    # Remove text-size control codes \{ \}
    text = _TEXTSIZE.sub("", text)

    # Remove known control code patterns
    for pat in _CONTROL_CODE_PATTERNS:
        text = re.sub(pat, "", text, flags=re.IGNORECASE)

    # Extra safety: if something removed only the prefix and left "[1]" right before a colon, strip that.
    # This prevents artifacts like "[1]：..." from being read aloud.
    text = re.sub(r"\[\d+\](?=[:：])", "", text)

    # Trim whitespace each line
    lines = [ln.strip() for ln in text.split("\n")]

    # Strip leading/trailing empty lines
    while lines and lines[0] == "":
        lines.pop(0)
    while lines and lines[-1] == "":
        lines.pop()

    return "\n".join(lines)


def preprocess(text: str) -> str:
    cleaned = clean_control_codes(text)
    cleaned_lines = [_SPACES.sub(" ", ln).strip() for ln in cleaned.split("\n")]
    return "\n".join(cleaned_lines).strip()


if __name__ == "__main__":
    samples = [
        r"\C[2]こんにちは！\C[0] \V[1] \I[10]",
        "  \n  \\N[1]：やった！\n\n",
        r"文章中に\\nがある場合\\n改行にしたい。",
        r"文章中に\nがある場合\n改行にしたい。",
        r"サイズ\{大きく\}して\}戻す\{",
        r"待機\. さらに\| 進む\! 終了\^",
        # Add a variant test that may appear as yen-sign backslash
        "¥N[1]：やった！"
    ]

    for i, s in enumerate(samples, 1):
        print("==== sample", i, "====")
        print("IN :")
        print(s)
        print("OUT:")
        print(preprocess(s))
        print()
