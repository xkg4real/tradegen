# TRADEGEN PR4e 구현 준비 — PR34 병합 뒤 이어갈 작업

2026-11-13. 읽기 전용 대조 기준: PR34 head `a0b28d0fc0fee4a359f833f91a7c0f572777481e`. 이 문서를 작성할 때 P0b 전체 회귀가 진행 중이므로 결과·병합을 추정하지 않는다. **PR4e 코드·테스트는 아직 구현하거나 실행하지 않았다.** PR34 병합 확인 뒤 그 main에서 작업을 시작한다.

## 1. 바로 사용할 근거와 현재 상태

- 원 계획: `docs/superpowers/plans/2026-11-11-upbit-krw-universe-pr4e-runner-coordinator.md` Tasks1–14. 행 번호는 과거 fd85850 기준이라 실제 코드의 함수/문구로 위치를 찾는다.
- 원 계약: `docs/superpowers/specs/2026-11-11-upbit-krw-universe-design.md` §7/9/10/12/13/15.
- 준비된 필수 회귀: handoff의 `context/upbit-universe/gpt-20261113/pr4e-required-regressions.md` 및 `pr4e-required-regression-fragments.md`. 이 파일의 Python fragment는 준비 자료이며 실행 통과 증거가 아니다.
- 옛 preflight: `/workspace/tradegen-session/universe-1113/pr4e-preflight.md`. 그 문서의 “PR4d 기능 없음”, “v2 SIZE_FALLBACK” 설명은 현재 P0b 코드보다 오래됐으므로 아래 표와 수정사항을 우선한다.
- 최신 사용자 요구: 정상 호가/보유 내역을 용량 때문에 버리지 않음, 오류·재시작만으로 매도하지 않음, E 자체로 매도하지 않고 갱신 요청, 기존 손실 하한 유지. 이것을 다시 승인받을 항목으로 만들지 않는다.

| 의존성 | a0b28d0에서 확인 | PR4e에서 할 일 |
|---|---|---|
| PR4a odds batch/session binding/kill reason | 있음. `execution_control/universe_odds.py:146`의 run_batch는 positions/positions_asof 필수 | Runner/Coordinator가 실제 계약으로 호출 |
| PR4b universe profile/program/chooser | 있음 | 프로그램/규칙 해시·max_candidates를 구성에 연결 |
| PR4c IOC·종목별 terms·buy cap·symbol renewal·unlisted | 있음 | flat 재확인 뒤에만 종목 변경, 정상 exits 유지 |
| PR4d SlotUniverse/record_slot/recorded_allow | 있음. `live_history.py:940` 이후 새 기록은 v3 정책 필수 | 실제 기록된 allow를 소비; 새 타입/키워드 계약 사용 |
| P0a/P0b 무손실 객체·v3·strict head/replay | a0b28d0에 구현, full 검증 진행 중 | 보존; slot 용량/저장 오류는 명시적 기록 실패로 처리 |
| 저장 정책 파일의 owner/rehearsal 전달 | 있음. coordinator composition 및 owner/rehearsal의 history_storage 경로 | 원 계획 코드 조각을 복사하며 이 경로를 삭제하지 않음 |
| LiveHistory.decided_symbol | 아직 없음 | Task7의 작은 조회 seam 추가 |
| Runner entry_allow/universe batch/flat helpers | 아직 없음. `runner.py:186/287/398/506`은 원래 signature | Tasks2–4 구현 |
| Coordinator universe slot/status/events/odds | 아직 없음. 현재는 fixed slot 경로 | Tasks5–12 구현 |
| public alerts.toast/ToastQueue | 아직 없음. `alerts.py:216`에 private `_toast`만 있음 | Task1 구현 |
| owner odds 명령·universe rehearsal adapter | 아직 없음 | Tasks12–13 구현 |
| 보호 보유 및 E 무매도 행동 revision | 미완료 | PR4e가 완성했다고 주장하지 않음. 아래 최신 요구 연결을 별도 검증 |

## 2. 병합 직후 첫 점검

1. GitHub에서 PR34가 실제 merged인지, merge SHA가 무엇인지 확인한다. 검증한 PR head와 merge tree를 대조한다. 미병합이면 PR4e tracked edits를 시작하지 않는다.
2. 최신 handoff CURRENT/LEDGER와 main을 다시 읽고 다른 작업자가 같은 파일을 소유하지 않는지 확인한다. `gpt/universe-pr4e-runner-coordinator` 작업 트리를 확인된 main에서 만든다.
3. 아래 실제 signature를 확인하고 새 branch 실행 로그의 base SHA를 남긴다.
   - `run_batch(controller, template, bars, *, n, now, clock, positions, positions_asof)`
   - `record_slot(book, account, *, trade_symbol, universe, tick_size, positions)`
   - v3 `storage_policy`가 `HistoryChain`/`LiveHistory`/composition에 같은 값으로 전달됨
   - `parse_term_receipts`의 `TERMS_MARKET_INACTIVE`, `allow_symbol_change`, `within_buy_cap`
4. 기존 `tests/launch_acceptance.py`의 `launch_floor_state_check`, `launch_clock_check`, `launch_universe_history`, `launch_evidence_objects`, `launch_history_storage`, `launch_lossless_history`를 모두 유지한다.
5. `coordinator.py`, `live_history.py`의 CRLF를 보존한다. 나머지 현재 대상과 새 파일은 LF를 유지한다. main과 작업본의 실제 bytes로 확인한다.

## 3. 구현 순서와 파일 소유

### A. 알림 seam — 원 Task1

변경: `core/compliance/alerts.py`, 새 `execution_launch/toast_queue.py`, `tests/compliance_cli.py`, 새 `tests/launch_toast_queue.py`.

- public `toast(title, body)`는 기존 `_toast` seam으로 전달한다. Coordinator에 PowerShell 실행을 넣지 않는다.
- FIFO 큐는 첫 put에서 worker를 시작하고 idle이 되면 종료한다. 생성자는 thread를 시작하지 않는다. toast 실패는 해당 알림만 실패시키고 다음 알림을 처리한다.
- root가 `tests/launch_guards.py`의 정확한 clean import 예제와 `launch_acceptance` registry를 통합한다.

완료 검사: `test_toast_wrapper_calls_the_seam_and_never_powershell_itself`, `test_put_returns_while_a_toast_is_showing_and_order_is_kept`, `test_a_failing_toast_is_dropped_and_the_next_one_still_shows`, `test_construction_starts_no_thread_and_the_worker_ends_when_idle`. 실제 사용자 알림 발송은 하지 않는다.

### B. Runner — 원 Tasks2–4, 한 작업자

변경: `execution_launch/runner.py`, 새 `tests/launch_runner_universe.py`.

1. `tick(..., entry_allow=None)`와 `run(..., entry_allow=None)` 연결. universe 매수만 slot allow·현재 snapshot·session에 묶인 batch/종목을 검사한다. 거절은 blocked이며 runner를 영구 중지하지 않는다.
2. 전략 매도와 `submit_exit`는 entry allow/snapshot이 없어도 기존 매도 검사를 계속한다. 같은 종목의 active sell이 있으면 두 번째 매도는 blocked, 새 요청 없음.
3. pure `active`, `dust`, `flat_in`을 추가한다. `refresh_instrument_rules(..., account=None)`에서 cross-coin renewal을 적용하기 직전 동일한 flat 조건을 재검사한다. unsettled/UNKNOWN IOC sell과 계좌보다 새로운 주문 상태는 종목 전환을 막는다.
4. `prepare_launch_session(..., universe_batch=None)`가 universe template·snapshot·batch binding을 전달하도록 한다. 코드/검토/기존 owner authority 검증을 생략하지 않는다.

완료 검사: 원 계획 Tasks2–4의10개 runner tests와 기존 `launch_runner`, `launch_instrument_refresh`, `launch_deployment`/준비 경계. fixed profile이 entry_allow를 무시하는 기존 의미, held dust 경계, 같은 종목 session rules binding, uncertain sell이 해소되기 전 cross-coin 금지까지 확인한다.

A와 B는 다른 파일이므로 병렬 작업 가능하다. signed fixture를 쓰는 검사는 대상 소스가 잠시 고정된 뒤 실행한다.

### C. Coordinator 기초·종목 선택 — 원 Tasks5–7, 한 작업자

변경: `execution_launch/coordinator.py`, 새 `tests/launch_coordinator_universe.py`, Task7만 `execution_launch/live_history.py`의 조회 seam 추가.

1. 명시적 slot_source/program/toast와 universe status 필드10개를 추가한다. 72h 초과 창은 거절한다. 기존 controlled-mode 거절 및 inert construction을 유지한다.
2. `_disarm_locked`로 기존 disarm의 작업 lock 내부 부분을 분리한다. 일반 owner disarm은 기존 재발행을 유지하고, slot 안의 event는 이미 발행된 frame을 불필요하게 다시 수집하지 않는다.
3. terms/quote를 현재 trade_symbol로 읽는다. `_held=None`은 아직 계좌 확인 전이며 flat으로 추정하지 않는다. held 때의 terms 오류와 flat 때의 buy-only block을 분리한다.
4. `_holdings` 및 `_universe_monitor`에서 현재 계좌와 미체결 상태를 기준으로 trade coin을 선택한다. 이전 종목에서 flat이고 pending renewal이 없을 때만 새 종목으로 갱신한다. 실패한 갱신은 사실과 block을 유지하고 다음 monitor에서 재시도한다.
5. `LiveHistory.decided_symbol()`은 마지막으로 확정된 chooser `_state.held`를 반환하는 seam이다. 이것 자체가 주문 권한이 아니다. 실제 frame 검증은 P0b verifier가 계속 담당한다.

완료 검사: construction 무효값·72h 경계·lazy toast·종목별 조회·보유/extra/unlisted·종목 선택·cross-coin flat·UNKNOWN IOC sell·재시작 후 보유 종목·renewal 재시도. P0b history identity/replay/정책 전달 테스트를 함께 유지한다.

### D. 사건·slot 실행 — 원 Tasks8–11 + 필수 보정 C3

변경: 같은 Coordinator 소스/테스트. B의 runner interface와 C의 구성 이후에 통합한다.

- 현재 계좌 발행 → flags/tickers/book → allow/events 계산 → 실제 v3 history 기록 → 각각의 사건 처리 → 성공한 기록/유효한 book이 있을 때 runner tick 순서를 고정한다.
- history 기록 실패도 사건 처리를 생략하지 않는다. 해당 슬롯은 실패로 표시하고 전략 slot 재개를 막되 monitoring/명시적 관리 경로를 가짜 HOLD나 자동 매도로 바꾸지 않는다.
- `HISTORY_BOOK_OFF_TICK`, `HISTORY_BOOK_MARKET_MISMATCH` 두 가지 **실제 호가 검증 오류**만 None으로 한 번 재기록할 수 있다. `HISTORY_STORAGE_LIMIT_EXCEEDED`, `HISTORY_STORAGE_UNAVAILABLE` 및 다른 저장 오류를 book=None 재시도로 처리하지 않는다.
- `entry_allow`는 성공적으로 기록된 `history.recorded_allow`를 전달한다. 이전 계획의 “SIZE_FALLBACK 뒤 allow=[]” 분기는 삭제한다. 큰 정상 행도 flags/tickers/book/allow가 보존되는 P0b 계약을 따른다.
- inactive 사실로 `_vanished=True`가 된 상태는 아래 C3 순서를 보장한다. `Controller.kill`은 정지/무장 해제 기록이며 시장가 주문과 다르다. 성공을 확인하지 못하면 disarm_failed를 sticky하게 표시한다.
- extra holding, 경고, uncertain flag, remainder, missed slot을 별도 상태로 드러낸다. unknown/조회 실패를 유효한 warning이나 SELL 판단으로 승격하지 않는다.

C3 필수 회귀:

1. 양수 평가액의 코인을 보유한 상태에서 terms inquiry 실패 → `_terms_blocked=True`.
2. 다음 refresh가 `TERMS_MARKET_INACTIVE` → `_vanished=True`여도 `_terms_blocked` 사실은 지우지 않는다.
3. 다음 slot의 초기 terms gate가 이 알려진 vanished 사건까지 막지 않도록 한다. fresh publish → history 시도 → vanish 처리/stop → kill 한 번을 실행한다.
4. 그 slot과 반복 호출에서 runner tick/adapter request는 없다. false/raising kill은 sticky failure. 일반 held inquiry 실패는 기존 게이트를 계속 지킨다.

원래 계획은 2까지만 검사하고 3의 초기 gate가 사건 경로를 막는 버그가 있으므로 그대로 복사하면 안 된다. 준비된 `test_terms_failure_then_inactive_reaches_one_disarm_after_fresh_record_without_a_tick`를 실제 fixture 계약에 맞춰 통합한다.

새 P0b 연결 회귀:

- 크기가 큰 정상 receipt/holdings를 넣은 coordinator slot이 실제 history의 정상 allow를 사용한다.
- 저장 quota/쓰기 장애는 한 번의 record 시도, 명시적 저장 상태, tick 없음, events 실행, 기존 evidence 손상 없음으로 끝난다. None 호가로 잘못된 두 번째 기록을 만들지 않는다.
- 무관 orphan/pending 때문에 기존 확정 frame 읽기를 막지 않는 P0b 규칙과, 다음 새 기록의 quota refusal을 구분한다.
- suspend/missed slot 이후 소급 슬롯을 생성하거나 head를 자동 seed하지 않는다.

### E. Odds·준비·콘솔 — 원 Task12 + 필수 보정 C1/C2

변경: `coordinator.py`, `tools/owner/launch.py`, Coordinator 테스트. 이미 P0b에서 추가한 history-storage 설정/CLI 경로는 보존한다.

`Coordinator.odds_batch`의 정확한 순서:

1. 현재 snapshot 참조·bars 요청 시각·서울 날짜를 복사한다.
2. `_work`를 잡지 않고 `read_bars(top_n, now=bars_time, clock=...)`를 실행한다.
3. 완료 후 `self._observation`을 **한 번만** 로컬 변수에 복사한다.
4. 그 다음 fresh now를 얻는다. clock rollback, 서울 날짜 변경, observation 부재/미래/30s 초과를 거절한다.
5. 동일 observation의 `.positions`와 `.asof`를 실제 `run_batch(...positions=...,positions_asof=...)`에 전달한다.

계좌 provider/Controller.account_provider/_publish를 호출하지 않는다. `latest_frame.accounts[0].positions`는 holding tuple이며 여기의 `core.compliance.model.Positions` 계약과 다르다. run_batch 자체의 시작/완료 시각 및 authority 재검사를 유지한다.

필수 검사: 기존 work lock을 다른 thread가 잡고 있어도 완료, observation read 정확히1회, provider 호출0회, 30s와30s+1µs/미래 경계, bars45s 뒤 새 observation 성공, Seoul midnight 교차 거절, 같은 날짜 clock rollback, 오류 문자열 비공개. 원 계획의 fake run_batch도 실제 signature로 고친다.

OwnerRuntime의 `odds` 결과는 준비용 batch로 저장하고 `prepare`에 전달한다. 연구 검토/코드 승인/arm으로 자동 확장하지 않는다.

### F. Rehearsal 연결 — 원 Task13

변경: `tools/owner/rehearsal.py`, `tests/launch_owner_rehearsal.py`.

- `_QuoteSource.read(symbol=None)`, `_TermsSource.read(symbol=None)`로 종목을 호출 시점에 전달한다. fixed profile의 인수 없는 호출은 그대로 유지한다.
- `_SlotSource`가 guarded flags/tickers 조회를 제공한다. 각 read 앞뒤의 기존 signed read guard를 유지한다.
- `build_rehearsal`이 program/slot source를 Coordinator에 넘긴다. P0b의 `history_storage` 선택 설정과 composition 전달은 유지한다.
- preparation_provider는 여전히 없다. rehearsal odds/prepare가 실제 세션 준비나 매수를 가능하게 만들지 않는다.

완료 검사: 종목별 route, 매 조회 앞/뒤 guard, guard 실패 시 외부 호출 없음, fixed route 동일, 저장 정책 구성 회귀, owner exit/cancel 기존 동작. 실제 API는 호출하지 않고 fake transport로 검증한다.

## 4. 최신 요구 때문에 원 계획을 그대로 쓰면 안 되는 부분

| 원 계획 위치 | 수정할 내용 | 필요한 검사 |
|---|---|---|
| Contract notes 및 Tasks9/10 | SIZE_FALLBACK 전제 제거. v3 저장 실패는 호가 None 경로와 구분 | 큰 정상 자료 보존, quota 오류 재시도0회 |
| Task7 `_universe_monitor`의 window-end toast | “기한이 끝났으니 submit_exit/앱으로 매도” 지시를 기본 행동으로 쓰지 않음. 감시·승인 상태와 갱신 필요를 표시 | deadline 알림/갱신 handler 자체의 runner/exit 호출 없음만 검사. 갱신 요청 중복 방지·무승인 기간 연장 금지. 전체 final-slot 무매도 검증은 아래 후속 필수 조건 |
| Task8 warning/remainder toast | “추가 매수해 최소 주문액을 맞춘 뒤 매도”를 자동/기본 해결 절차로 지시하지 않음. 잔량·최소액·실행 가능성·사용자 관리 필요를 설명 | toast 처리에서 주문 없음, 추가 입금/매수 없음 |
| Task6–10 terms 상태 | C3 stale `_terms_blocked`가 inactive 사건을 가로막지 않도록 하되 invalid terms를 유효하다고 만들지 않음 | held inquiry failure→inactive→record/events/kill 순서 |
| Task12 odds | 이미 바뀐 run_batch 인자·한 observation·fresh clock 순서 반영 | C1/C2 5개 준비 회귀 + rollback |
| Task13 설정 | P0b history_storage 설정을 원 계획의 구형 exact-key parser로 되돌리지 않음 | 정책 누락/불일치 거절, 정상 전달 |
| PR 설명의 after-merge 서명 절차 | 매 PR마다 code-approve 요구하지 않음. 필요한 최종 코드/행동 변경 뒤 한 번 승인하는 현재 흐름 유지 | 문서 검토. merge가 실서명/arm이 아님 명시 |

E 이후의 완전한 보호 보유·자동 갱신 승인 UI/Telegram/WebAuthn은 원 PR4e의 구현 내용이 아니다. PR4e에서 기한 자체의 자동 매도 기능을 새로 만들거나, 메시지만 바꾸고 전체 E 요구를 구현했다고 표시하지 않는다.

위 Task7의 검사는 **deadline 알림/갱신 handler 자체가 exit 또는 runner를 호출하지 않는다는 부분 검사**다. §D의 정상 slot 경로는 마지막 bar에도 runner를 호출할 수 있고, 현재 driver에는 terminal target=0가 남아 있다. 따라서 이 부분 검사를 통과해도 실제 final slot에서 기한만으로 SELL하지 않는다는 전체 요구를 통과한 것이 아니다.

현 driver의 terminal target=0와 A1의 오류→매도 조항은 후속 행동 revision에서 반드시 수정·검증한다. **새 live/arming composition에는 해당 행동 revision의 명시적 binding과 검증된 final-slot 경로가 없으면 구성을 거절하는 gate가 필요하다.** PR4e의 기존 controlled-mode 거절을 완화하거나, storage revision·알림 수정·부분 unit 결과만으로 이 gate를 통과시키지 않는다. 이 문서가 gate를 구현했다고 주장하는 것은 아니다.

후속 완료 검사에는 실제 Coordinator → 마지막 slot → 인증된 history/driver → dry controller 경로에서, 유효한 별도 전략/위험 매도 신호가 없는 E 만료만으로 SELL·EXIT가 만들어지지 않는 end-to-end 회귀가 필수다. 이 검사를 부분 검사로 대체하거나 미실행 상태를 PASS로 보고하지 않는다. 해당 행동 변경·검증·구성 gate가 완료되기 전 실제 활성화 준비 완료로 표시할 수 없다.

## 5. 검증·공유 파일·완료 조건

- root 단일 소유: `tests/launch_acceptance.py`, `tests/launch_guards.py`, 최종 실행 로그/PR 설명/전체 검증. 새 테스트 module3개를 추가하면서 기존 P0b registry를 빼지 않는다.
- Coordinator 담당자만 `coordinator.py`와 새 Coordinator 테스트를 수정한다. console 파일은 Task12 때 해당 담당자에게 순차 배정한다. Runner 담당자는 B의 파일만, toast 담당자는 A 파일만, rehearsal 담당자는 F 파일만 수정한다.
- 단계마다 위 지목 테스트와 영향을 받는 기존 모듈을 실행한다. 기존 isolated KEYLESS launcher를 새 작업 트리 경로로 명시 설정하고 실제 계좌·키·home 내용을 사용하지 않는다.
- 마지막 소스를 동결한 뒤 원 Task14의 compliance_guards/compliance_cli/control_guards/accounts_guards/launch_guards/owner_guards/execution_guards를 실행한다. 불필요한 initializer pin 재생성이나 일반 writer 허용 확대는 하지 않는다.
- launch suite 및 필요한 full suite의 PASS/FAIL/NOT_RUN과 실제 head/fingerprint를 기록한다. QA 출력은 원래 bytes로 보존하고 테스트 결과를 임의로 커밋하지 않는다.
- 시간 측정/실계좌 결과와 unit 결과를 구분한다. fake LiveHistory·source review·prepared session으로 통과한 시험을 실제 universe 주문 성공이나 전향 연구 통과로 표시하지 않는다.
- 72h 창 제한은 renewal registry4096개 초과가 절대 발생하지 않는다는 증명이 아니다. 60s 슬롯과 재시도는 이 숫자를 넘을 수 있다. 전환/재시도 수를 측정하고 capacity refusal을 테스트하되 한도를 몰래 높이지 않는다.
- 예상 PR 핵심 runtime은7개 파일(alerts,toast_queue,runner,coordinator,live_history,owner launch,owner rehearsal)과 해당 테스트/문서다. 추가 연결이 필요하면 실제 의존성 근거를 남긴다. 실제 diff 기준으로 확정하고 중복된 파일 수를 성과로 합산하지 않는다.

완료 시 의미: universe orchestration과 dry/fake 경계가 검증된 PR4e. **PR5 연구/인증, 보호 보유 행동 revision, 실계좌의 완전한 held/fill provenance, PLB와 owner 상태 증거, 최종 서명·활성화는 별도 미완료 항목**이다. 이 준비 문서는 작업을 중단하거나 새 포괄 승인을 요청하는 문서가 아니다.

법률, 세무, 투자 조언이 아니며 면허를 가진 자문가가 아니다.

## P0b 검증 후 상태 갱신

동일 코드 a0b28d0의 전체 회귀 완료: 2660 PASS / 0 FAIL / 135 NOT_RUN (전체 2795개; 환경 재시작 뒤 동일 소스의 나머지 검사를 재개). 앞부분의 검사 진행 중 표기는 계획 작성 시점이다. 이 문서의 후속 구현·검사를 수행했다는 뜻은 아니며 실제 PR34 병합 결과는 CURRENT와 GitHub에서 확인한다.
