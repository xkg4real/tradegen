# Explicit Cloud transport routing

The E1 inquiry transport and the E3 authenticated order transport can use the
managed Cloud sidecar without trusting ambient proxy, CA, `.netrc`, or authentication
settings. This change supplies routing configuration only. It does not approve a
venue, supply credentials, sign owner policy, arm a session, issue a capability,
or demonstrate connectivity.

## Configuration and lifecycle

`execution_network.route.build_managed_route` accepts these explicit nonsecret inputs:

- `policy_snapshot`: version 1 and `http_proxy` from the managed network policy.
- `runtime_status`: a current observation whose network policy state is `enforced`.
  Restricted mode requires exact names in `effective_allowed_hosts`; unrestricted
  mode still permits only the three pinned execution destinations below.
- `proxy_url`: exactly `http://proxy:8080`.
- `ca_bundle`: exactly `/etc/ssl/certs/ca-certificates.crt`; construction checks that
  this public system trust-store file exists. It does not read its contents.

The application passes its reviewed nonsecret Cloud settings explicitly. The
transport does not read environment values or search for configuration files.
Unsupported settings, stale or unenforced observations, absent CA files, and a
restricted policy with no approved venue host fail closed. A missing venue route
must be configured in Cloud by the owner; the application never modifies network
policy. Build a fresh configuration after policy changes or process restarts.

`inspect_configuration(..., route=route)` revalidates the supplied route against
its fresh runtime/startup observations and the public CA metadata. It may mark
the selected venue's probe environment configured; inquiry, account-evidence,
and execution readiness stay false. Inspection never activates the route.
`E1InquiryReader(..., route=route, clock=clock)` activates it only for one explicit
reader call, and requires an explicit callable clock in managed mode.

```python
from execution_network.route import build_managed_route, managed_route

route = build_managed_route(
    policy_snapshot=policy_snapshot,
    runtime_status=runtime_status,
    proxy_url=approved_proxy_url,
    ca_bundle=approved_ca_bundle,
)
with managed_route(route):
    # Run the separately authorized inquiry or controller operation here.
    pass
```

`ManagedRoute` is immutable configuration, not a security capability or authenticated
runtime observation. Construct it through the factory in production. The context
is local to the current execution context and restores the previous route even on
an exception. Callers must not keep it active across unrelated sessions. Runtime
readiness separately validates the platform observation; the managed sidecar is
the final network-policy enforcement point. Supplying a Python object cannot
authorize a blocked destination.

The exact destinations and TLS ports are `api.upbit.com:443`,
`openapi.koreainvestment.com:9443`, and `www.okx.com:443`. URL user information,
non-HTTPS schemes, other ports, hostname suffix lookalikes, fragments, and
whitespace are rejected before a requests session opens. Existing E1/E3 endpoint
and method allowlists still apply separately.

## HTTP invariants

Both existing `_send` seams obtain only `proxies` and `verify` from the reviewed
route helper. They retain one `requests.Session`, `trust_env=False`,
`allow_redirects=False`, the existing timeout and the existing method/body/auth
construction. Managed mode supplies the sidecar explicitly for both proxy scheme
keys and the verified system CA bundle. No proxy credentials, arbitrary proxy URL,
custom CA path, `verify=False`, `.netrc`, or ambient authentication is accepted.

The legacy default outside a managed context remains empty proxies and
`verify=True`. Cloud callers must select the managed route explicitly; default
direct mode is not a fallback from a failed or refused managed route. E3 makes one
send attempt. E1 retains its documented bounded GET retry rule, using the same
active route for both attempts; it never retries through a direct route. Unknown
delivery results retain the existing reconciliation behavior.

## Standalone inquiry support

`execution.transport.inquiry_clock(callable)` binds an explicit context-local
clock for standalone collectors. Each read must return an aware `datetime`,
normalized to UTC. No wall clock is selected automatically. The existing
`poll.main` clock seam is preserved, but an active explicit inquiry context takes
precedence for response receipts, OKX authentication and KIS token age even if
that legacy seam was previously installed. A standalone call without a supplied clock
continues to refuse when a clock is needed. The context yields a validated clock
reader and restores the previous binding on exit.

`Answer.raw_body` retains the original bytes alongside their existing SHA-256
digest. Its default is empty bytes for older synthetic fixtures, and its value is
excluded from the representation, as is the parsed body. Exact accounting codecs
must verify the raw digest and parse decimal JSON tokens themselves; a legacy
fixture's empty raw body is not exact account evidence. Raw responses remain
sensitive in-memory account data and are not intended for logs or handoff files.

The E1 Upbit allowlist adds only `GET /v1/order` for fill-detail reconciliation,
as documented by the [official single-order inquiry](https://docs.upbit.com/kr/reference/get-order).
The collector supplies `uuid`. POST and DELETE at that path remain refused, as do
neighbor paths. This addition does not alter the existing poll collection loop or
the E3 trading endpoints.

## Verification boundary

Synthetic tests cover exact proxy/CA configuration, current enforced observations,
blocked hosts, URL/port confusion, nested context restoration, absence of implicit
clock, invalid clock values, raw-response digest correspondence, explicit TLS and
proxy arguments, and failures that cannot fall back direct. Existing transport
source pins are extended narrowly to the reviewed route helper and retain negative
controls for arbitrary proxies, TLS bypass, redirects, and alternate sends.

These tests never open a network connection. They establish application behavior,
not venue reachability, account permissions, account balances, or live readiness.
