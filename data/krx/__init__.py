"""Read-only Korean market data: KIS quotes, OpenDART filings, KRX snapshots."""
from data.krx.gateway import Answer, KRXGateway

__all__ = ["Answer", "KRXGateway"]
