"""The universe snapshot store and its command (spec section 5): temporary state only and synthetic public answers
through the fake transport._send; no venue call, key or real home."""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

from core.compliance import owner
from execution_launch import universe_store as US
from tests import accounts_universe as AU

SHA_A, SHA_B = "a" * 64, "b" * 64


def refused(call, code):
    try:
        call()
    except US.UniverseStoreError as exc:
        assert str(exc) == code, (str(exc), code)
    else:
        raise AssertionError(f"not refused: {code}")


def names():
    return sorted(path.name for path in owner.universe_dir(AU.DAY).iterdir())


def test_a_rebuild_adds_a_file_and_leaves_the_earlier_one_intact():
    first = US.write_snapshot(b"first", AU.DAY, SHA_A)
    second = US.write_snapshot(b"second", AU.DAY, SHA_B)
    assert first == owner.universe_path(AU.DAY, SHA_A) and second == owner.universe_path(AU.DAY, SHA_B)
    assert first.read_bytes() == b"first" and second.read_bytes() == b"second"
    assert names() == [SHA_A + ".json", SHA_B + ".json"]


def test_an_existing_snapshot_is_refused_and_never_replaced():
    path = US.write_snapshot(b"first", AU.DAY, SHA_A)
    refused(lambda: US.write_snapshot(b"other", AU.DAY, SHA_A), "UNIVERSE_SNAPSHOT_EXISTS")
    assert path.read_bytes() == b"first" and names() == [SHA_A + ".json"]


def test_a_snapshot_that_appears_during_the_write_is_kept_and_the_temporary_file_removed():
    """Windows rename refuses an existing name (the owner PC); see the ponytail note in write_snapshot for POSIX."""
    if os.name != "nt":
        return
    real = US.checked_target

    def racing(path, what="path", *, within=None):
        if what == "universe snapshot":
            Path(path).write_bytes(b"racer")
        return real(path, what, within=within)

    with patch.object(US, "checked_target", racing):
        refused(lambda: US.write_snapshot(b"mine", AU.DAY, SHA_A), "UNIVERSE_SNAPSHOT_EXISTS")
    assert owner.universe_path(AU.DAY, SHA_A).read_bytes() == b"racer" and names() == [SHA_A + ".json"]


def test_bad_arguments_are_refused_before_any_write():
    for raw, day, sha256 in ((b"", AU.DAY, SHA_A), ("text", AU.DAY, SHA_A), (b"x", "2026-11-11", SHA_A),
                             (b"x", AU.DAY, "A" * 64), (b"x", AU.DAY, "a" * 63), (b"x", AU.DAY, None)):
        refused(lambda: US.write_snapshot(raw, day, sha256), "UNIVERSE_STORE_INPUT_INVALID")
    assert not owner.universe_dir(AU.DAY).parent.exists()
