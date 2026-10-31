"""Deterministic mock adapter; consumes the real capability, never opens HTTP.

An acknowledgment is deliberately not a fill. Tests or an offline scenario supply
explicit status and fill evidence separately through the account provider.
"""
from __future__ import annotations

from collections import deque
from execution_control.capability import consume_capability
from execution_orders.model import AdapterResult, validate_request


class DryRunAdapter:
    def __init__(self, codec, *, results=()):
        self.codec = codec
        self.results = deque(results)
        self.requests = []
        self.identities = {}

    def prepare(self, order, rules):
        return self.codec.prepare(order, rules)

    def prepare_cancel(self, order, venue_order_id, **kwargs):
        return self.codec.prepare_cancel(order, venue_order_id, **kwargs)

    def prepare_status(self, order, venue_order_id, **kwargs):
        return self.codec.prepare_status(order, venue_order_id, **kwargs)

    def dispatch(self, request, capability, *, now):
        validate_request(request)
        consume_capability(capability, request)
        self.requests.append(request)
        if self.results:
            result = self.results.popleft()
            if isinstance(result, Exception):
                raise result
            if type(result) is not AdapterResult:
                raise ValueError('invalid simulated response')
            return result
        identity = self.identities.setdefault(request.client_id, 'dry-' + request.client_id)
        return AdapterResult(status='accepted' if request.operation != 'status' else 'open',
                             code='dry_run', venue_order_id=identity, client_id=request.client_id)
