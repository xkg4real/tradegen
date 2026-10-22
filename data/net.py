"""The HTTP session the history and analysis clients share.

A bare `requests.get` gives up on the first connection reset or 502. This
session retries an idempotent GET twice — once immediately, then after one
second — and keeps connections open between calls.

Deliberate limits:

  * **Only connection failures and 502 / 503 / 504 are retried.** A 429 is not:
    `Retry-After` is ignored here (a daily-quota 429 can ask for hours, which
    would park the calling thread), and hitting a rate-limited provider again
    at once only deepens the breach — Binance escalates that to an IP ban. A
    500 is not either: KIS reports application errors (per-second limit,
    expired token) as HTTP 500, and replaying those triples the traffic for
    nothing.

  * **POSTs are never replayed on a response or a read error.** The KIS token
    endpoint is itself rate-limited, and issuing a token twice is not harmless.
    (A connection that never reached the server is still retried, for any
    method — nothing was processed.)

  * **The engine's quote path does not use this session.** `FMPQuoteClient`,
    `KISClient.quote` and the KRX snapshot make exactly one attempt: the
    engine's own grace window (`config.NO_DATA_GRACE_TICKS`) is the retry
    there, and stacking the two would turn one 12-second timeout into about
    37 seconds per symbol per pass.

Worst case for one call here when the network is fully down: three attempts,
so about three times `config.HTTP_TIMEOUT_SECONDS` plus one second.

urllib3 logs each retry with the full request URL, and for FMP and OpenDART
the URL carries the API key. Its loggers are raised to ERROR so a future log
handler, even one at DEBUG, cannot write a key to disk.
"""
from __future__ import annotations

import logging

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

RETRY = Retry(
    total=2,
    backoff_factor=0.5,
    status_forcelist=(502, 503, 504),
    allowed_methods=("GET",),
    respect_retry_after_header=False,
    raise_on_status=False,
)

logging.getLogger("urllib3").setLevel(logging.ERROR)

session = requests.Session()
for _scheme in ("https://", "http://"):
    session.mount(_scheme, HTTPAdapter(max_retries=RETRY))
