"""The E1 key reader (E1 spec 4; contract section 5; E2, E27): named values from the repo-root .env, read by a small
standard-library parser. A name present in the environment decides alone, so a blank or <placeholder> value there is
missing even when .env holds that name (the KEYLESS prefix relies on it). Values go back only to the caller; nothing
here logs, prints or stores one, and an error names the key, never its value."""
from __future__ import annotations

import os
import re
from collections.abc import Sequence
from pathlib import Path

_ENV_FILE = Path(__file__).resolve().parents[1] / ".env"     # seam: the suite points it at a missing temp file
_NAME = re.compile(r"[A-Z][A-Z0-9_]*")


class KeyMissing(Exception):
    """A named key is not set; the message names it and never holds a value."""

    def __init__(self, name: str):
        super().__init__(f"{name} is not set in .env or the environment")
        self.name = name


def read(names: Sequence[str]) -> tuple[str, ...]:
    """The values of `names`, in order. A name in os.environ decides alone (blank or <placeholder> is missing); any
    other name comes from .env, which is read at most once per call and only then (a missing file is empty).
    KeyMissing names the first missing name; anything but a sequence of upper-case variable names is
    ValueError("keys: bad name"), raised before anything is read."""
    if isinstance(names, str):
        raise ValueError("keys: bad name")
    names = tuple(names)
    if not all(isinstance(n, str) and _NAME.fullmatch(n) for n in names):
        raise ValueError("keys: bad name")
    values, file = [], None
    for name in names:
        if name in os.environ:
            value = _clean(os.environ[name])
        else:
            if file is None:
                try:
                    text = _ENV_FILE.read_text(encoding="utf-8-sig")     # utf-8-sig: a Notepad BOM (E27)
                except FileNotFoundError:
                    text = ""
                file = _parse(text)
            value = _clean(file.get(name, ""))
        if not value:
            raise KeyMissing(name)
        values.append(value)
    return tuple(values)


def _parse(text: str) -> dict[str, str]:
    """KEY=VALUE lines: blank lines and # comments skipped, a leading `export ` dropped, a quoted value ends at its
    matching quote (anything after it is ignored), an unquoted one at the first whitespace followed by # (as
    python-dotenv, which config.py applies to the same file); no expansion; a later line wins."""
    out = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):]
        key, sep, value = line.partition("=")
        if not sep:
            continue
        value = value.strip()
        if value[:1] in ("'", '"'):
            value = value[1:].partition(value[0])[0]
        else:
            value = re.split(r"\s#", value, maxsplit=1)[0].rstrip()
        out[key.strip()] = value
    return out


def _clean(value: str) -> str:
    """`value` stripped; an unedited <placeholder> reads as "" (missing), as config._clean reads it."""
    value = value.strip()
    return "" if value.startswith("<") and value.endswith(">") else value
