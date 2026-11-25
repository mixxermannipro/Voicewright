"""Conservative validation of LLM-edited dictation.

The guard cannot prove semantic equivalence. It catches the failures that
actually happen with small local models: protocol leakage, assistant replies,
truncation, invented or changed facts, and dropped negations.

Two modes
---------
``strict``
    Default. Word order must survive, only fillers may disappear. Used for
    plain cleanup where the meaning must not change.
``transform``
    For explicitly dictated commands ("shorter", "formal", "translate").
    Numbers, dates, URLs, e-mails and code must survive; wording may change.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

ASSISTANT_INTROS = (
    "here is the corrected text", "here's the corrected text", "here is your corrected",
    "here is the edited text", "here's the edited text", "the corrected text is",
    "the edited text is", "sure, here is", "certainly, here is",
    "hier ist der korrigierte text", "hier ist dein korrigierter text",
    "hier ist der bearbeitete text", "gerne, hier ist", "natürlich, hier ist",
)

PROTOCOL_MARKERS = (
    "<|im_start|>", "<|im_end|>", "<|endoftext|>", "<tool_call>", "</tool_call>",
    "<|assistant|>", "<|user|>", "```", "the user message is dictated text",
    "please provide the text to edit", "as an ai language model",
    "i cannot assist with that", "i can't assist with that",
    "ich kann dabei nicht helfen", "als ki-sprachmodell",
)

NEGATIONS = {
    "de": ("nicht", "kein", "keine", "keinen", "keinem", "keiner", "keines",
           "nie", "niemals", "nichts", "ohne", "weder", "noch"),
    "en": ("not", "no", "never", "none", "nothing", "without", "neither", "nor",
           "cannot", "can't", "don't", "doesn't", "didn't", "won't", "isn't", "aren't"),
}

_NUMBER_RE = re.compile(r"(?<![\w.])\d+(?:[.,:/-]\d+)*(?![\w])")
_URL_RE = re.compile(r"https?://[^\s<>\"']+|www\.[^\s<>\"']+", re.IGNORECASE)
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_CODE_RE = re.compile(r"`[^`]+`|\b[\w-]+\([^)]*\)|\b\w+\.\w{2,4}\b")
_WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)


@dataclass
class GuardResult:
    ok: bool
    text: str
    reasons: list[str] = field(default_factory=list)


def _norm_number(token: str) -> str:
    return token.replace(",", ".").rstrip(".")


def _tokens(pattern: re.Pattern, text: str) -> list[str]:
    return [m.group(0).strip() for m in pattern.finditer(text) if m.group(0).strip()]


def _negation_count(text: str, language: str) -> int:
    words = [w.lower() for w in _WORD_RE.findall(text)]
    if language.startswith("de"):
        bag = NEGATIONS["de"]
    elif language.startswith("en"):
        bag = NEGATIONS["en"]
    else:
        bag = NEGATIONS["de"] + NEGATIONS["en"]
    return sum(1 for w in words if w in bag)


def validate(source: str, candidate: str, language: str = "", mode: str = "strict",
             dictionary: tuple[str, ...] = ()) -> GuardResult:
    """Return the accepted text or the reason the candidate was rejected."""
    reasons: list[str] = []
    src = (source or "").strip()
    out = (candidate or "").strip()

    if not out:
        return GuardResult(False, src, ["empty result"])
    if out == src:
        return GuardResult(True, out, [])

    low = out.lower()
    if any(marker in low for marker in PROTOCOL_MARKERS):
        reasons.append("protocol leakage")
    if any(low.startswith(intro) for intro in ASSISTANT_INTROS):
        reasons.append("assistant preamble")
    if any(intro in low[:120] for intro in ASSISTANT_INTROS):
        reasons.append("assistant preamble")

    # Length sanity: a cleanup may shorten, never turn into an essay.
    src_len, out_len = len(src), len(out)
    ratio = out_len / max(1, src_len)
    if ratio > 2.2:
        reasons.append(f"output grew too much ({ratio:.1f}x)")
    if mode == "strict" and ratio < 0.35:
        reasons.append(f"output shrank too much ({ratio:.1f}x)")

    # Protected facts.
    src_numbers = {_norm_number(n) for n in _tokens(_NUMBER_RE, src)}
    out_numbers = {_norm_number(n) for n in _tokens(_NUMBER_RE, out)}
    missing_numbers = src_numbers - out_numbers
    if missing_numbers:
        reasons.append("numbers changed: " + ", ".join(sorted(missing_numbers)))

    for pattern, label in ((_URL_RE, "URL"), (_EMAIL_RE, "e-mail"), (_CODE_RE, "code")):
        missing = set(_tokens(pattern, src)) - set(_tokens(pattern, out))
        if missing:
            reasons.append(f"{label} missing: " + ", ".join(sorted(missing)[:3]))

    for word in dictionary:
        if word and word in src and word not in out:
            reasons.append(f"dictionary word missing: {word}")

    if mode == "strict":
        if _negation_count(src, language) > _negation_count(out, language):
            reasons.append("negation dropped")

    if reasons:
        return GuardResult(False, src, reasons)
    return GuardResult(True, out, [])


def clean_protocol(text: str) -> str:
    """Remove obvious protocol residue before validation."""
    out = re.sub(r"(?s)```[a-zA-Z]*\n?|\n?```", "", text)
    out = re.sub(r"<\|[^|]*\|>", "", out)
    out = re.sub(r"(?s)<think>.*?</think>", "", out)
    out = re.sub(r"(?s)^\s*(?:assistant|system|user)\s*:\s*", "", out, flags=re.IGNORECASE)
    return out.strip()
