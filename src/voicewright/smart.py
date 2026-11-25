"""Smart, fully local dictation features.

Everything here is deterministic and instant. Nothing calls a model.

* spoken punctuation and line commands
* structure requests ("as a list", "as an e-mail", "as notes")
* rewrite commands ("shorter", "more formal", "translate to English")
* text snippets and word replacements
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Optional

# ---------------------------------------------------------------------------
# Spoken punctuation
# ---------------------------------------------------------------------------
# Ordered longest-first so "anführungszeichen auf" wins over "anführungszeichen".
_SPOKEN: tuple[tuple[str, str], ...] = (
    ("anführungszeichen auf", "„"),
    ("anführungszeichen zu", "“"),
    ("öffnendes anführungszeichen", "„"),
    ("schließendes anführungszeichen", "“"),
    ("open quotation mark", "“"),
    ("close quotation mark", "”"),
    ("open quote", "“"),
    ("close quote", "”"),
    ("klammer auf", "("),
    ("klammer zu", ")"),
    ("open parenthesis", "("),
    ("close parenthesis", ")"),
    ("neuer absatz", "\n\n"),
    ("neue zeile", "\n"),
    ("new paragraph", "\n\n"),
    ("new line", "\n"),
    ("line break", "\n"),
    ("fragezeichen", "?"),
    ("ausrufezeichen", "!"),
    ("doppelpunkt", ":"),
    ("semikolon", ";"),
    ("strichpunkt", ";"),
    ("gedankenstrich", " – "),
    ("bindestrich", "-"),
    ("komma", ","),
    ("punkt", "."),
    ("exclamation mark", "!"),
    ("question mark", "?"),
    ("semicolon", ";"),
    ("colon", ":"),
    ("comma", ","),
    ("full stop", "."),
    ("period", "."),
    ("prozent", "%"),
    ("percent", "%"),
)

_LITERAL_ON = ("literalmodus an", "literal mode on", "wörtlich an")
_LITERAL_OFF = ("literalmodus aus", "literal mode off", "wörtlich aus")

_SPOKEN_RE = re.compile(
    r"(?<![\w-])(" + "|".join(re.escape(p) for p, _ in _SPOKEN) + r")(?![\w-])",
    re.IGNORECASE,
)
_LITERAL_RE = re.compile(
    r"(?<![\w-])(" + "|".join(re.escape(p) for p in _LITERAL_ON + _LITERAL_OFF) + r")(?![\w-])",
    re.IGNORECASE,
)


def apply_spoken_punctuation(text: str) -> str:
    """Turn dictated punctuation into real characters.

    Text between "literal mode on" and "literal mode off" is left untouched, so
    someone can dictate a sentence *about* the word "Komma".
    """
    if not text:
        return text
    out: list[str] = []
    literal = False
    pos = 0
    for match in _LITERAL_RE.finditer(text):
        chunk = text[pos:match.start()]
        out.append(chunk if literal else _replace_spoken(chunk))
        phrase = match.group(0).lower()
        literal = phrase in _LITERAL_ON
        pos = match.end()
    tail = text[pos:]
    out.append(tail if literal else _replace_spoken(tail))
    return "".join(out)


def _replace_spoken(chunk: str) -> str:
    if not chunk:
        return chunk
    mapping = {p.lower(): ch for p, ch in _SPOKEN}

    def repl(m: re.Match) -> str:
        return mapping.get(m.group(0).lower(), m.group(0))

    return _SPOKEN_RE.sub(repl, chunk)


def tidy_punctuation(text: str) -> str:
    """Remove the spacing artefacts spoken punctuation leaves behind."""
    t = text
    t = re.sub(r"[ \t]+([,.!?;:])", r"\1", t)
    t = re.sub(r"([,;:])(?=[^\s\d])", r"\1 ", t)
    t = re.sub(r"[ \t]*\n[ \t]*", "\n", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    t = re.sub(r"[ \t]{2,}", " ", t)
    return t.strip()


# ---------------------------------------------------------------------------
# Structure requests
# ---------------------------------------------------------------------------
_LIST_CUES = (
    "als stichpunkte", "als stichpunktliste", "als liste", "stichpunkte",
    "aufzählung", "als aufzählung", "bullet points", "as a list", "as bullets",
)
_EMAIL_CUES = ("als e-mail", "als email", "als mail", "as an email", "as an e-mail")
_NOTES_CUES = ("als notizen", "als notiz", "as notes", "als zusammenfassung")

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")


def detect_structure(text: str) -> tuple[Optional[str], str]:
    """Return (mode, text_without_cue). Mode is list | email | notes | None."""
    low = text.lower().strip()
    for cue, mode in ((_EMAIL_CUES, "email"), (_NOTES_CUES, "notes"), (_LIST_CUES, "list")):
        for phrase in cue:
            if low.endswith(phrase):
                return mode, text[: len(text) - len(phrase)].rstrip(" ,.;:")
            if low.startswith(phrase):
                return mode, text[len(phrase):].lstrip(" ,.;:")
    return None, text


def _sentences(text: str) -> list[str]:
    parts = [p.strip(" ,;") for p in _SENTENCE_SPLIT.split(text) if p.strip(" ,;")]
    return parts


def as_bullets(text: str) -> str:
    parts = _sentences(text)
    if len(parts) <= 1:
        parts = [p.strip() for p in re.split(r",\s*(?:und|and)?\s*", text) if p.strip()]
    lines = []
    for part in parts:
        part = part.strip().rstrip(".")
        if part:
            lines.append("- " + part[0].upper() + part[1:] if part else "")
    return "\n".join(lines) if lines else text


def as_notes(text: str) -> str:
    parts = _sentences(text)
    if not parts:
        return text
    title = parts[0].rstrip(".")
    rest = parts[1:]
    out = [title]
    if rest:
        out.append("")
        out.extend("- " + p.rstrip(".") for p in rest)
    return "\n".join(out)


def as_email(text: str) -> str:
    parts = _sentences(text)
    if not parts:
        return text
    body = " ".join(parts)
    return f"Hallo,\n\n{body}\n\nViele Grüße"


def apply_structure(text: str, mode: str) -> str:
    if mode == "list":
        return as_bullets(text)
    if mode == "notes":
        return as_notes(text)
    if mode == "email":
        return as_email(text)
    return text


# ---------------------------------------------------------------------------
# Rewrite commands
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Command:
    kind: str                 # shorter | longer | formal | casual | grammar | translate | emoji | none
    argument: str = ""
    rest: str = ""


_COMMANDS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("mach das kürzer", "kürzer", "kürze das", "shorter", "make it shorter"), "shorter"),
    (("mach das länger", "länger", "ausführlicher", "longer"), "longer"),
    (("formeller", "förmlicher", "more formal", "make it formal"), "formal"),
    (("lockerer", "casual", "entspannter", "more casual"), "casual"),
    (("korrigiere nur die grammatik", "nur grammatik", "grammar only"), "grammar"),
    (("füge emojis hinzu", "mit emojis", "add emojis"), "emoji"),
)

_TRANSLATE_RE = re.compile(
    r"(?:übersetze(?:\s+das)?\s+(?:auf|in|nach)\s+([\wäöüß]+)|translate(?:\s+it)?\s+(?:to|into)\s+([\w]+))",
    re.IGNORECASE,
)

_LANGUAGE_MAP = {
    "englisch": "en", "english": "en", "deutsch": "de", "german": "de",
    "französisch": "fr", "french": "fr", "spanisch": "es", "spanish": "es",
    "italienisch": "it", "italian": "it", "portugiesisch": "pt", "portuguese": "pt",
    "niederländisch": "nl", "dutch": "nl", "polnisch": "pl", "polish": "pl",
    "türkisch": "tr", "turkish": "tr", "russisch": "ru", "russian": "ru",
}


def detect_command(text: str) -> Command:
    """Recognise a rewrite command at the start or end of the dictation."""
    stripped = text.strip()
    low = stripped.lower()

    m = _TRANSLATE_RE.search(stripped)
    if m:
        word = (m.group(1) or m.group(2) or "").lower()
        rest = (stripped[:m.start()] + " " + stripped[m.end():]).strip(" ,.;:")
        return Command("translate", _LANGUAGE_MAP.get(word, word), rest)

    for phrases, kind in _COMMANDS:
        for phrase in phrases:
            if low.endswith(phrase):
                rest = stripped[: len(stripped) - len(phrase)].rstrip(" ,.;:")
                return Command(kind, "", rest)
            if low.startswith(phrase):
                rest = stripped[len(phrase):].lstrip(" ,.;:")
                return Command(kind, "", rest)
    return Command("none", "", stripped)


COMMAND_INSTRUCTIONS = {
    "shorter": "Make the text noticeably shorter and more concise. Keep every fact.",
    "longer": "Expand the text slightly with natural connecting words. Do not invent facts.",
    "formal": "Rewrite in a polite, professional tone. Keep every fact.",
    "casual": "Rewrite in a relaxed, conversational tone. Keep every fact.",
    "grammar": "Only fix grammar, spelling and punctuation. Do not rephrase.",
    "emoji": "Add a few fitting emojis. Keep the wording.",
    "translate": "Translate the text into the requested language. Keep every fact.",
}


# ---------------------------------------------------------------------------
# Snippets and replacements
# ---------------------------------------------------------------------------
def expand_snippets(text: str, snippets: Iterable[dict]) -> str:
    """Replace 'textbaustein <name>' with the stored text."""
    by_name = {str(s.get("name", "")).strip().lower(): str(s.get("text", ""))
               for s in snippets if s.get("name")}
    if not by_name:
        return text
    pattern = re.compile(r"(?i)(?:textbaustein|snippet)\s+([\wäöüß -]{1,40})")
    out = text
    for m in reversed(list(pattern.finditer(text))):
        name = m.group(1).strip().lower()
        if name in by_name:
            out = out[:m.start()] + by_name[name] + out[m.end():]
    return out


def apply_replacements(text: str, replacements: dict) -> str:
    """Case-insensitive whole-word replacements (heard -> written)."""
    if not replacements:
        return text
    out = text
    for heard, written in replacements.items():
        if not heard:
            continue
        pattern = re.compile(r"(?<![\w-])" + re.escape(str(heard)) + r"(?![\w-])",
                             re.IGNORECASE)
        out = pattern.sub(str(written), out)
    return out
