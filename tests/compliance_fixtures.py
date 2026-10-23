"""Fixtures for the compliance suite (compliance plan, contract section 3). Task 1 adds `temp_home`; later tasks add
the shipped-table, context, intent, owner-log and store fixtures."""
from __future__ import annotations

import contextlib
import os
import shutil
import tempfile
from pathlib import Path
from typing import Iterator


@contextlib.contextmanager
def temp_home() -> Iterator[Path]:
    """A fresh TRADEGEN_HOME for one test; the previous value comes back and the dir is removed afterwards."""
    home = Path(tempfile.mkdtemp(prefix="tradegen_home_"))
    saved = os.environ.get("TRADEGEN_HOME")
    os.environ["TRADEGEN_HOME"] = str(home)
    try:
        yield home
    finally:
        if saved is None:
            os.environ.pop("TRADEGEN_HOME", None)
        else:
            os.environ["TRADEGEN_HOME"] = saved
        shutil.rmtree(home, ignore_errors=True)
