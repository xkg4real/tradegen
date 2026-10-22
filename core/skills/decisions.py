"""Turn a workflow's `decision_question` into the answers it actually names.

The eleven workflows carry twenty-four `decision_gate` steps, and not one of
them declares its answers. There is no `decision_options` key anywhere in the
YAML — the permissible answers live inside the prose of `decision_question`:

    Given today's breadth, uptrend participation, and top risk, is new swing
    trade risk allowed, restricted, or cash-priority?

The cockpit used to answer that with two buttons, `Continue` and `Stop here`,
which is not an answer to the question asked. This module reads the options out
of the author's own sentence so the buttons can be `Allowed` / `Restricted` /
`Cash-priority`.

**The governing rule is that NEXTGEN never adds a word the question did not
use.** Every option below is a verbatim slice of `decision_question`. Where the
sentence does not enumerate a closed set — most gates do not; they ask "which
candidates…", which is answered per candidate and not by a button — this module
says so, and the caller falls back to a free-text answer. Guessing at options
for an open question would be the cockpit inventing a contract on the workflow
author's behalf, which is the one thing it must not do.

Two shapes are recognised, and only two:

  * **A declared vocabulary.** A run of machine-style tokens separated by
    slashes, as in `(CLEAN-PASS / PASS-CAUTION / CONDITIONAL-PASS)`. When one is
    found, the rest of the question is swept for other tokens of the same shape,
    because the negative half of the vocabulary is usually stated outside the
    parentheses ("a HOLD-REVIEW, STEP1-RECHECK, or FAIL verdict is fail-closed").

  * **A prose enumeration.** A trailing `A, B, or C?` list of bare option
    phrases. This one needs care: `pass the written-plan, predefined-stop,
    position-size, … checks?` has the same comma shape but is a checklist, not
    an answer set. The tell is the determiner in front of it — an enumeration
    hanging off `the` is a noun phrase — plus the requirement that every item be
    a bare phrase with no article, preposition, or conjunction inside it.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

MAX_OPTIONS = 6

# A machine-style token: CROWDED_LONG, CLEAN-PASS, STEP1-RECHECK, FAIL.
# The lookaround keeps `COT` out of `COT-index` — an acronym glued to a
# lowercase word is part of that word, not a member of a vocabulary.
_TOKEN = r"[A-Z][A-Z0-9]*(?:[_-][A-Z0-9]+)*"
_TOKEN_RE = re.compile(rf"(?<![\w-])({_TOKEN})(?![\w-])")
_RUN_RE = re.compile(rf"(?<![\w-]){_TOKEN}(?:\s*/\s*{_TOKEN})+(?![\w-])")
_PARENTHETICAL = re.compile(r"\(([^)]*)\)")

# Words that mark an item as part of a sentence rather than an answer to it.
_STRUCTURAL = {
    "a", "an", "the", "this", "that", "these", "those", "its", "their", "his",
    "her", "our", "your", "of", "to", "in", "on", "at", "by", "for", "with",
    "from", "into", "over", "under", "than", "as", "is", "are", "was", "were",
    "be", "been", "if", "not", "no", "any", "each", "all", "more", "most",
    "which", "what", "who", "whom", "whose", "when", "where", "why", "how",
}
_DETERMINERS = {"a", "an", "the", "this", "that", "these", "those", "its",
                "their", "his", "her", "our", "your"}
_LEADING = re.compile(r"^(?:and|or|and/or)\s+", re.IGNORECASE)
_DASH = re.compile(r"\s+[—–]\s+|\s+-\s+|:\s+")


@dataclass(frozen=True)
class Option:
    """One answer the question names. `value` is what gets recorded."""
    value: str

    @property
    def label(self) -> str:
        """Button text. Capitalised for prose options, left alone for tokens."""
        if self.value.isupper():
            return self.value
        return self.value[:1].upper() + self.value[1:]


@dataclass(frozen=True)
class Choice:
    question: str
    options: tuple[Option, ...] = ()
    source: str = ""            # "vocabulary" | "enumeration" | ""

    @property
    def closed(self) -> bool:
        """True when the question names its own answers and buttons can be
        rendered for them. False means the gate takes a written answer."""
        return len(self.options) >= 2

    @property
    def values(self) -> tuple[str, ...]:
        return tuple(o.value for o in self.options)


# --------------------------------------------------------------------------- #
# Shape 1: a declared token vocabulary
# --------------------------------------------------------------------------- #
def _vocabulary(question: str) -> tuple[Option, ...]:
    parenthesised = {m.group(1).strip() for m in _PARENTHETICAL.finditer(question)}
    anchor: Optional[re.Match] = None
    for run in _RUN_RE.finditer(question):
        text = run.group(0)
        tokens = [t.strip() for t in text.split("/")]
        if any(len(t) < 3 for t in tokens):
            continue
        # Two bare acronyms side by side ("delayed EP / PEAD watch") are a
        # phrase, not a vocabulary. Require either three or more members, a
        # separator inside a member, or the whole run in parentheses.
        separated = any("_" in t or "-" in t for t in tokens)
        if len(tokens) < 3 and not separated and text.strip() not in parenthesised:
            continue
        anchor = run
        break
    if anchor is None:
        return ()

    # The vocabulary's negative half is usually stated outside the parentheses,
    # so sweep the whole question rather than only the run that anchored it.
    # Document order, so the tier the question is named after leads the row.
    found: list[str] = []
    for match in _TOKEN_RE.finditer(question):
        token = match.group(1)
        if len(token) < 4 and "_" not in token and "-" not in token:
            continue
        if token not in found:
            found.append(token)
    return tuple(Option(t) for t in found[:MAX_OPTIONS])


# --------------------------------------------------------------------------- #
# Shape 2: a trailing prose enumeration
# --------------------------------------------------------------------------- #
def _bare_phrase(text: str) -> bool:
    """True for `cash-priority`, `journaled only`, `market environment`.
    False for `risk to the EP-day low` or `which are rejected` — anything
    carrying the grammar of a sentence is part of one."""
    words = text.split()
    if not (1 <= len(words) <= 3):
        return False
    return not any(w.strip(",.").lower() in _STRUCTURAL for w in words)


def _enumeration(question: str) -> tuple[Option, ...]:
    head = question.split("?")[0]
    if "?" not in question:
        return ()
    head = _PARENTHETICAL.sub(" ", head)
    parts = [p.strip() for p in head.split(",")]
    if len(parts) < 2:
        return ()

    # Walk backwards while the items still look like answers.
    collected: list[str] = []
    stopped_at: Optional[str] = None
    for part in reversed(parts):
        candidate = _LEADING.sub("", part).strip()
        if _bare_phrase(candidate):
            collected.append(candidate)
            continue
        stopped_at = part
        break
    if len(collected) < 1 or stopped_at is None:
        return ()

    # The first option is fused to the question stem: "…is new swing trade risk
    # allowed" or "…of the outcome — thesis quality". Recover it from whichever
    # boundary the stem provides.
    tail = _DASH.split(stopped_at)[-1].strip()
    words = stopped_at.split()
    if _bare_phrase(tail) and tail != stopped_at.strip():
        head_option, preceding = tail, stopped_at[:stopped_at.rfind(tail)].split()
    elif words:
        head_option, preceding = words[-1], words[:-1]
    else:
        return ()
    if not _bare_phrase(head_option):
        return ()
    # `pass the written-plan, predefined-stop, …` is a list of things, not a
    # list of answers, and the determiner is what says so.
    if preceding and preceding[-1].strip(",.").lower() in _DETERMINERS:
        return ()

    values = [head_option] + list(reversed(collected))
    values = [v.strip(" .") for v in values if v.strip(" .")]
    if len(values) < 2:
        return ()
    seen: list[str] = []
    for value in values:
        if value.lower() not in {s.lower() for s in seen}:
            seen.append(value)
    return tuple(Option(v) for v in seen[:MAX_OPTIONS])


def options_for(question: str) -> Choice:
    """Read the answers a decision question names. Empty options mean the
    question is open and must be answered in words, not by a button."""
    text = " ".join((question or "").split())
    if not text:
        return Choice(question="")
    # Several gates are imperative instructions rather than questions ("Register
    # each fade whose sizer output is SIZED…"). Those name a vocabulary without
    # asking the operator to pick from it, and turning that into a row of
    # buttons would misread the step. A gate with no question mark has no
    # options, only an outcome to write down.
    if "?" not in text:
        return Choice(question=text)
    vocabulary = _vocabulary(text)
    if len(vocabulary) >= 2:
        return Choice(question=text, options=vocabulary, source="vocabulary")
    enumeration = _enumeration(text)
    if len(enumeration) >= 2:
        return Choice(question=text, options=enumeration, source="enumeration")
    return Choice(question=text)
