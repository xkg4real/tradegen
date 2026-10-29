"""Fixtures for the odds suite (odds plan, contract section 3.2). Task 1 adds the CHUNK and pilot swaps; Tasks 5, 9
and 13 add the venue, series, plan, context and input fixtures. Not in MODULES, and no name here starts with test_.
Each swap imports its modules when entered, so this file imports nothing from core/odds at load."""
from __future__ import annotations

import contextlib
import importlib
from typing import Iterator


@contextlib.contextmanager
def chunk(n: int = 2_000) -> Iterator[None]:
    """core.odds.simulate runs n paths per chunk: CHUNK = n, every DEFAULT_PATHS track = n and GARCH_SUB =
    min(GARCH_SUB, n), all three put back in finally; so a pipeline or CLI test that passes no path count runs one
    small chunk. import_module reads sys.modules, so the swap reaches the module that is loaded there."""
    sim = importlib.import_module("core.odds.simulate")
    saved = sim.CHUNK, sim.DEFAULT_PATHS, sim.GARCH_SUB
    sim.CHUNK, sim.DEFAULT_PATHS, sim.GARCH_SUB = n, {track: n for track in saved[1]}, min(saved[2], n)
    try:
        yield
    finally:
        sim.CHUNK, sim.DEFAULT_PATHS, sim.GARCH_SUB = saved


@contextlib.contextmanager
def pilots(n: int = 2_000, nodes: int = 64) -> Iterator[None]:
    """The GARCH pilot and the tilt pilot run n paths and check 1 uses `nodes` quantile nodes: models.PILOT_PATHS,
    simulate.TILT_PILOT and models.PILOT_NODES, all three put back in finally. Task 8's pilot tests run without it,
    at 20,000 paths and 512 nodes."""
    models = importlib.import_module("core.odds.models")
    sim = importlib.import_module("core.odds.simulate")
    saved = models.PILOT_PATHS, sim.TILT_PILOT, models.PILOT_NODES
    models.PILOT_PATHS, sim.TILT_PILOT, models.PILOT_NODES = n, n, nodes
    try:
        yield
    finally:
        models.PILOT_PATHS, sim.TILT_PILOT, models.PILOT_NODES = saved
