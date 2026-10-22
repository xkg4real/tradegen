"""QUANTGEN quantitative analytics core.

Everything in this package is deterministic given its inputs and runs without
network access — market data arrives through `history.load_history`, which is
the only module that talks to a provider. The analysis modules (montecarlo,
risk, optimize, signals, backtest) take price series in and hand structured
results out, so every one of them is testable offline against synthetic data.

`insights` turns those structured results into written analysis: a local
deterministic narrative always, and a Claude-generated deep read when an
ANTHROPIC_API_KEY is configured. `gsq` wraps the optional gs_quant session.
"""
