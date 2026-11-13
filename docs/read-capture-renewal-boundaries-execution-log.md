# Read-capture renewal boundary correction

2026-11-13. PR54 added inert read-capture declarations and a frozen inquiry subset. The existing renewal validation boundary also pins those modules' import-time surfaces; its two pins were omitted from that change. The subsequent generation integration run exposed both failing renewal guard checks. These were stale transitive initializer pins, not a generation runtime failure. PR54's 485-case evidence did not include these two E2 checks.

After reviewing the actual new event/context declarations, the `get_ident` import, ContextVar/default expressions and the frozen nine-GET set, this change updates only the two exact initializer hashes in `tests/renewal_boundaries.py`. It adds six negative mutations covering an executable capture default, an executable ContextVar default, an import alias, mutable event declarations and expanded GET/POST capture scope. The pure CALLS inventory, source-I/O/clock/alias bans, existing negative controls and production code are unchanged.

Related validation: **105 PASS / 0 FAIL / 0 NOT_RUN**, one process, **35.472 seconds**. Scope: control and execution guards, actual instrument-refresh regressions, launch guards and two global read-only checks. Source fingerprint `683b75224c112203cebefdd3c2a446d2f605184b8476a2e5d53bb5035222bb12`, test HEAD `61b2b20bb4ae48ed063fb6007205cecf2f30fe02`, correction commit `29955935cb7e01a9e7178742ae971137789503e1`. Evidence: `tradegen-session/read-capture-boundaries-1113/read-capture-boundaries-final-*`. The earlier failures remain in `committed-generation-dev1-*`; its two separate calendar-test failures are not part of this patch.

Nineteen KEYLESS variables and isolated fixtures were used. Source and protected-home metadata remained unchanged from before imports/discovery through completion; QA output was restored. No real account, credentials, API, orders, signing or activation were used. Generation publication's final validation remains separate.

법률, 세무, 투자 조언이 아니며 면허를 가진 자문가가 아니다
