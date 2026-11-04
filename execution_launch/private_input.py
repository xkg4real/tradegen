"""Bounded Windows reads of explicit private input files; no write, environment or home lookup.

POSIX callers keep their descriptor-relative no-follow readers unchanged. On Windows the same
boundary is enforced by Win32 lexical rules, lstat metadata on every path component, a
canonical-path comparison and an opened-handle identity check. Errors carry one fixed code only.
Files on network shares, SUBST or mapped drives, volumes without file identity, 8.3 aliases,
reparse points (symlinks, junctions, mount points) and cloud placeholders are refused; there is
no override.
"""
from __future__ import annotations

import ntpath
import os
import re
import stat

# winnt.h FILE_ATTRIBUTE_RECALL_ON_OPEN / RECALL_ON_DATA_ACCESS have no stat names: cloud
# placeholders (OneDrive Files On-Demand) whose read would start a download.
_REFUSED_ATTRIBUTES = (stat.FILE_ATTRIBUTE_REPARSE_POINT | stat.FILE_ATTRIBUTE_OFFLINE
                       | 0x00040000 | 0x00400000)
_DRIVE = re.compile(r"[A-Za-z]:")
_SEPARATORS = re.compile(r"[\\/]")


class PrivateInputError(ValueError):
    """One fixed PRIVATE_INPUT_* code; never a path, file byte or operating-system text."""


def _require(condition, code):
    if not condition:
        raise PrivateInputError(code)


def _private(part, private):
    folded = part.casefold()
    return folded in private or folded == ".env" or folded.startswith(".env.")


def _checked_path(path, *, suffix, private):
    """Pure Win32 lexical check (ntpath only, so testable on any OS); returns the absolute form.

    Refused: a drive other than a lettered root (UNC, device and NT namespaces, drive-relative),
    reserved names (streams, trailing dots or spaces, DOS devices, wildcards, control characters),
    parent traversal, an empty component, another suffix and any private component.
    """
    _require(hasattr(ntpath, "isreserved"), "PRIVATE_INPUT_PLATFORM_UNSUPPORTED")  # Python 3.13+
    _require(type(path) is str and path and "\x00" not in path, "PRIVATE_INPUT_PATH_REFUSED")
    drive, root, _ = ntpath.splitroot(path)
    _require((not drive or (_DRIVE.fullmatch(drive) is not None and root))
             and not ntpath.isreserved(path) and ".." not in _SEPARATORS.split(path),
             "PRIVATE_INPUT_PATH_REFUSED")
    absolute = ntpath.abspath(path)
    drive, root, tail = ntpath.splitroot(absolute)
    parts = tail.split("\\")
    _require(_DRIVE.fullmatch(drive) is not None and root == "\\" and not ntpath.isreserved(absolute)
             and all(parts) and ntpath.splitext(parts[-1])[1] == suffix
             and not any(_private(part, private) for part in parts), "PRIVATE_INPUT_PATH_REFUSED")
    return absolute


def _regular(info, maximum):
    # st_ino == 0 means the volume has no usable file identity: refuse rather than skip the check.
    _require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_ino != 0
             and info.st_size <= maximum, "PRIVATE_INPUT_FILE_REFUSED")


def read_private_file(path, *, maximum, suffix, private):
    """Bytes of one explicit, local, singly-linked regular file on a lettered drive.

    Every prefix from the drive root down is lstat-checked for reparse, offline and recall
    attributes; the canonical path must equal the checked path (no 8.3 alias, SUBST or network
    drive); the opened handle must carry the identity the final lstat reported, so a file or
    parent swapped between the check and the open is refused; the read is bounded independently
    of the reported size.
    """
    _require(os.name == "nt", "PRIVATE_INPUT_PLATFORM_UNSUPPORTED")
    absolute = _checked_path(path, suffix=suffix, private=private)
    drive, root, tail = ntpath.splitroot(absolute)
    prefixes = [drive + root]
    for name in tail.split("\\"):
        prefixes.append(ntpath.join(prefixes[-1], name))
    try:
        for prefix in prefixes:
            info = os.lstat(prefix)
            _require(not info.st_file_attributes & _REFUSED_ATTRIBUTES,
                     "PRIVATE_INPUT_LINK_OR_PLACEHOLDER_REFUSED")
        _regular(info, maximum)
        identity = (info.st_dev, info.st_ino)
        _require(ntpath.normcase(os.path.realpath(absolute, strict=True)) == ntpath.normcase(absolute),
                 "PRIVATE_INPUT_ALIAS_REFUSED")
        descriptor = os.open(absolute, os.O_RDONLY | os.O_BINARY | os.O_NOINHERIT)
        with os.fdopen(descriptor, "rb") as handle:          # the baseline_store bounded-read idiom
            info = os.fstat(handle.fileno())
            _require((info.st_dev, info.st_ino) == identity, "PRIVATE_INPUT_IDENTITY_CHANGED")
            _require(not info.st_file_attributes & _REFUSED_ATTRIBUTES,
                     "PRIVATE_INPUT_LINK_OR_PLACEHOLDER_REFUSED")
            _regular(info, maximum)
            raw = handle.read(maximum + 1)
    except OSError:
        raise PrivateInputError("PRIVATE_INPUT_UNAVAILABLE") from None
    _require(len(raw) <= maximum, "PRIVATE_INPUT_TOO_LARGE")
    return raw
