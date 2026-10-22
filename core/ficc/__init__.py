"""QUANTGEN FICC analytics core — rates, bonds, FX, and the macro read.

Built for the OTM FICC & Quant curriculum: pricing, structuring and trading
analytics for rates and FX derivatives, with the same rules the equity core
already follows. Everything here is deterministic given its inputs and runs
without network access — market data arrives only through `core.ficc.data`,
which is the single module that talks to a provider (FRED and Yahoo, both
keyless) and which always answers with a labeled source, SYNTHETIC included.

Conventions, used by every module in this package:

  * Rates, yields, spreads and vols are **decimals** (0.045, not 4.5). The UI
    converts to percent and basis points; the core never does.
  * Tenors are **years** as floats; `common.parse_tenor` turns "3m"/"10y"/"5y5y"
    into numbers.
  * Zero rates are **continuously compounded**; discount factor = exp(-z·t).
  * Money is in the instrument's currency; `notional` defaults to 1,000,000.
  * Single-curve framework: one curve both projects and discounts. This is the
    ponytail simplification the whole package shares; a dual-curve (OIS
    discounting) upgrade slots in behind `YieldCurve` without touching callers.
"""
