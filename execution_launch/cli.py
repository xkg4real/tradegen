"""Offline launch-profile diagnostics; never a signer, account reader or order loop.

    python -m execution_launch.cli
    python -m execution_launch.cli --template
    python -m execution_launch.cli --profile /explicit/profile.json --now 2026-10-23T01:00:00+00:00

Only an explicit bounded JSON file may be read. No environment, implicit home,
owner state, credentials or live network is consulted. Output contains fixed
field names and actions, never the supplied profile values or filesystem path.
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import stat
import sys

from core.compliance.model import KST
from execution_launch.profile import (
    MAX_PROFILE_BYTES, LaunchProfile, ProfileError, parse_profile_json,
    preflight_profile, profile_body,
)

_PRIVATE_COMPONENTS = frozenset({".tradegen", ".nextgen", ".ssh", ".aws", ".gnupg", ".azure", ".kube"})


class _ArgumentsError(ValueError):
    pass


def _arguments(argv):
    # Keep parsing local: argparse's localization/help path can inspect locale and
    # terminal environment variables, and its standard errors echo rejected input.
    values = sys.argv[1:] if argv is None else argv
    if type(values) not in (tuple, list) or any(type(item) is not str for item in values):
        raise _ArgumentsError
    args = {"template": False, "profile": None, "now": None, "help": False}
    seen, index = set(), 0
    while index < len(values):
        token = values[index]
        index += 1
        if token in ("--help", "-h", "--template"):
            name = "template" if token == "--template" else "help"
            if name in seen:
                raise _ArgumentsError
            seen.add(name)
            args[name] = True
            continue
        option, separator, inline = token.partition("=")
        if option not in ("--profile", "--now") or option[2:] in seen:
            raise _ArgumentsError
        name = option[2:]
        if separator:
            value = inline
        else:
            if index == len(values) or values[index].startswith("--"):
                raise _ArgumentsError
            value = values[index]
            index += 1
        if not value:
            raise _ArgumentsError
        seen.add(name)
        args[name] = value
    if args["template"] and (args["profile"] is not None or args["now"] is not None):
        raise _ArgumentsError
    return args


def _read_profile(path: str) -> bytes:
    """Read one explicit regular JSON file, refusing links and known private roots.

    Directory descriptors prevent a parent-link replacement from redirecting the
    read. Platforms without no-follow relative opens fail closed. No home lookup
    or environment-based state-root discovery is needed for the lexical denial.
    """
    candidate = Path(path)
    parts = candidate.parts
    if (not path or "\x00" in path or candidate.suffix != ".json" or ".." in parts
            or any(part.casefold() in _PRIVATE_COMPONENTS or part.casefold() == ".env"
                   or part.casefold().startswith(".env.") for part in parts)):
        raise ProfileError("PROFILE_FILE_REFUSED")
    absolute = Path(os.path.abspath(candidate))
    if any(part.casefold() in _PRIVATE_COMPONENTS or part.casefold() == ".env"
           or part.casefold().startswith(".env.") for part in absolute.parts):
        raise ProfileError("PROFILE_FILE_REFUSED")
    if (os.open not in os.supports_dir_fd or not hasattr(os, "O_NOFOLLOW")
            or not hasattr(os, "O_DIRECTORY")):
        raise ProfileError("PROFILE_FILE_PLATFORM_UNSUPPORTED")
    directory_fd = file_fd = None
    try:
        directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
        directory_fd = os.open(absolute.anchor, directory_flags)
        for component in absolute.parts[1:-1]:
            next_fd = os.open(component, directory_flags, dir_fd=directory_fd)
            os.close(directory_fd)
            directory_fd = next_fd
        file_fd = os.open(absolute.name,
                          os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | getattr(os, "O_CLOEXEC", 0),
                          dir_fd=directory_fd)
        info = os.fstat(file_fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_PROFILE_BYTES or info.st_nlink != 1:
            raise ProfileError("PROFILE_FILE_REFUSED")
        chunks, remaining = [], MAX_PROFILE_BYTES + 1
        while remaining:
            chunk = os.read(file_fd, min(remaining, 8192))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b"".join(chunks)
        if len(raw) > MAX_PROFILE_BYTES:
            raise ProfileError("PROFILE_JSON_TOO_LARGE")
        return raw
    except OSError:
        raise ProfileError("PROFILE_FILE_UNAVAILABLE_OR_REFUSED") from None
    finally:
        if file_fd is not None:
            os.close(file_fd)
        if directory_fd is not None:
            os.close(directory_fd)


def _emit_blocker(code: str, field: str, action: str) -> int:
    print(json.dumps({"profile_complete": False, "prerequisites_ready": False,
                      "execution_ready": False,
                      "issues": [{"code": code, "field": field, "action": action}]}, sort_keys=True))
    return 2


def main(argv=None) -> int:
    try:
        args = _arguments(argv)
        if args["help"]:
            print(__doc__)
            return 0
        if args["template"]:
            print(json.dumps(profile_body(LaunchProfile(schema_version=1, profile_id="example-unconfigured")),
                             indent=2, sort_keys=True))
            return 0
        if args["profile"] is None:
            return _emit_blocker("PROFILE_REQUIRED", "profile", "Supply an explicit launch profile or inspect --template.")
        if args["now"] is None:
            return _emit_blocker("EXPLICIT_NOW_REQUIRED", "now", "Supply an aware ISO8601 --now instant for freshness checks.")
        try:
            now = datetime.fromisoformat(args["now"])
            if now.utcoffset() is None:
                raise ValueError
            now.astimezone(timezone.utc)
            now.astimezone(KST)
        except (TypeError, ValueError, OverflowError):
            return _emit_blocker("EXPLICIT_NOW_INVALID", "now", "Use an aware ISO8601 instant within the supported calendar range.")
        profile = parse_profile_json(_read_profile(args["profile"]))
        report = preflight_profile(profile, now=now)
        print(json.dumps(asdict(report), sort_keys=True))
        return 2  # No owner context is loaded; this command cannot establish execution readiness.
    except _ArgumentsError:
        return _emit_blocker("CLI_ARGUMENTS_INVALID", "arguments", "Use --help for the supported offline command syntax.")
    except ProfileError as exc:
        return _emit_blocker(exc.code, exc.field, "Correct the explicit local profile input; no owner state was loaded.")
    except (OSError, ValueError, TypeError, RecursionError):
        return _emit_blocker("PROFILE_INPUT_UNAVAILABLE", "profile", "Review the explicit profile file and its schema locally.")


if __name__ == "__main__":
    raise SystemExit(main())
