# TRADEGEN — 확정 계좌 세대의 재시작 연결 준비

작성일: 2026-11-13. 읽기 기준: `origin/main` **19f6775**(PR #56 병합), 해당 구현 트리 `tradegen-committed-generation-1113`의 49796a6. 이 문서는 구현 제안이다. 새 코드·검사·네트워크·실계좌 접근은 수행하지 않았으며, 진행 중인 recovered-selection 검증 트리는 변경하지 않았다.

다음 최소 수직 단위는 **확정 입력과 commit 결과를 지속 보관하고, 재시작 시 실제 저장소·독립 head·Journal과 대조한 뒤 신선한 세대를 기존 Controller/Runner에 연결하는 rehearsal 시작 절차**다. PR #56의 세대 게시를 다시 만들거나, 저장된 잔고를 현재 계좌로 간주해 controlled 모드를 여는 작업이 아니다. 정상 재시작뿐 아니라 오래된 관측·미완료 commit·불확실 주문을 각각 구분해서 종료하는 경로까지 이 단위의 완료 조건으로 삼는다.

## 1. 이미 구현된 것과 실제 빈틈

| 현재 코드 | 이미 있는 기능 | 이번에 연결할 부분 |
| --- | --- | --- |
| `guard_capture_archive.py::archive_guard_capture_packet/read_guard_capture_packet/replay_guard_capture_archive` | 실제 BundleStore의 원본·별도 백업·catalog/head를 통한 전체 capture packet 보관/재읽기. 원시 receipts, 이전 baseline, staged path·coverage 등을 원래 시각으로 재생한다. | 전체 guard package의 policy·원 owner 관찰·평가 시각·세 predecessor heads·실제 commit receipt를 연결하는 폐쇄형 보관 형식은 없다. capture 원본 저장 기능 자체는 재사용한다. |
| `guard_capture_material.py::prepare_guard_capture_material` | 실제 보관 원문을 collector로 재생하여 account capture/valuation/path/coverage/interval을 재도출한다. | 역사 재생은 출처 인증이나 현재 사용 허가가 아니다. 현재 시각으로 재표시하지 않고 새 package 보관과 연결한다. |
| `continuous_guard_commit.py::commit_continuous_guard/classify_restart` | 실제 PREPARE → 필요한 halt → baseline/head → guard/head → COMPLETE, 동일 package 재시도, pending/divergence 분류. | 재시작한 프로세스가 동일 package 및 predecessor를 정확히 다시 확보하는 durable 연결이 없다. |
| `committed_account.py::CommittedAccountProvider.read/publish_committed` | 실제 열린 Journal Transaction, 두 store/head, PREPARE/COMPLETE와 receipt prefix를 검사한다. 직접 successor를 같은 provider에 게시하며 read/publication은 baseline을 전진시키지 않는다. | 저장된 원 package/receipt에서 새 프로세스의 실제 provider를 구성하고, startup 작업에 전달하는 composition이 없다. |
| `controller.py`, `runner.py` | 실제 완료 시각·현재 owner/권한 검사, paired committed observation, 세대 제한을 reserve/dispatch에 전달, 독립 reducing 경로, 미전송/불확실 상태 및 재전송 방지. | 이미 완성된 이 경계를 재사용해야 한다. 새 startup 결과나 boolean을 별도 주문 허가로 만들 필요가 없다. |
| `coordinator.py::__init__/_publish/_monitor` | rehearsal scheduler, startup/gap 모니터, 실제 주문 대조 호출. | 여전히 `ContinuousAccountProvider`를 만들고 `_publish`에서 호출한다. 그 provider의 `__call__`은 `advance_account_baseline`과 store commit/head CAS를 수행한다. guard commit 후 이 경로를 재사용하면 이중 전진하거나 다른 interval로 오인할 수 있다. |

`CommittedAccountProvider` 생성자는 원 입력을 분리 보관할 뿐 실제 현재 head를 검증해 운영 권한을 발급하지 않는다. 동일 프로세스에서는 기존 provider/Controller/Runner 객체 identity를 유지해야 한다. 재시작한 프로세스에서는 검증된 동일 원본으로 새 실제 객체를 한 번 구성하고 그 뒤 교체하지 않는다는 뜻이지, 이전 Python 객체 identity를 디스크에 보존한다는 뜻은 아니다.

## 2. 최소 구현 범위와 순서

**A. commit 전 입력 기록, commit 후 결과 기록을 기존 보관 저장소에 추가한다.** 새 전용 파일 쓰기 엔진을 만들지 않는다. 기존 BundleStore의 명시 provision, bounded object/manifest, 원자 확정·백업 재읽기·독립 head를 사용한다. runtime 자동 seed/adopt와 최신 파일명/mtime 추정은 금지한다.

- 입력 기록은 정확한 capture archive digest/packet digest/material digest, 원 baseline digest, policy, `owner_before`/`owner_after`, 원 `package['now']`, 세 predecessor heads와 전체 package digest를 묶는다. material의 기존 다섯 입력과 baseline은 실제 archive 재생 결과에서 얻고 대조한다. 모든 원문과 타입을 복구할 수 있는 strict versioned codec이 필요하며 pickle이나 임의 dataclass 로딩은 사용하지 않는다.
- 보관된 owner/coverage 값은 **과거 주장**이다. 로컬 저장 성공·hash·타입이 현재 실제 owner/출처 인증을 대신하지 않는다. 개인키·주문키·HTTP 인증 헤더는 저장하지 않는다.
- 먼저 입력 묶음을 실제 저장·백업·재읽기한다. 그 뒤 보관 lock을 놓고 기존 `commit_continuous_guard`를 호출한다. 실제 반환 receipt와 해당 PREPARE/COMPLETE 대응을 다시 읽은 결과만 별도 불변 결과 기록에 추가한다. 결과 기록은 원 입력 digest를 참조한다. 원 기록 덮어쓰기 없이 동일 내용 재시도와 충돌을 구분한다.
- `receipt.control_head`는 COMPLETE 행 자체가 아니라 완료 후의 유효한 prefix 끝일 수도 있다. 원 receipt, 실제 COMPLETE hash, 현재 관찰한 head를 서로 다른 값으로 보존한다. 정상 후속 risk/kill/fill 행을 이유 없이 거절하거나, receipt를 현재 끝으로 몰래 갱신하지 않는다.

**B. 시작 시 먼저 실제 durable 상태를 분류한다.** 실제 Journal이 검증한 행과 별도 guard/baseline heads를 읽어 기존 `classify_restart`를 사용한다. package 선택은 명시 기록 식별자와 실제 PREPARE의 input/transaction 바인딩으로 결정한다. 최신 balances나 경로 탐색으로 head를 만들지 않는다.

- 완료 결과와 원본이 모두 있으면 실제 store·head·전체 입력·Journal pair/prefix를 대조한다. constructor 호출만으로 `READY`를 반환하지 않는다.
- PREPARE가 있고 결과 기록이 없으면 원 입력이 먼저 보관돼 있어야 한다. `PENDING_*`는 거래 준비 완료가 아니다. 기존 동일-package commit 재시도 규칙만 적용할 수 있고, torn journal/temp file·DIVERGENCE·알 수 없는 head에는 자동 수리/채택을 하지 않는다.
- 실제 COMPLETE까지 성공했지만 결과 보관 응답이 유실된 경우, 보관 원 package와 실제 durable 상태로 기존 commit의 CONSISTENT 재시도 경로를 검증해 실제 replay receipt를 얻을 수 있다. 이는 잃어버린 최초 receipt를 추정한 복사본이 아니다. `replayed` 및 그때 실제 확인한 prefix를 새 결과 기록에 명시한다. 거래 재전송은 발생하지 않는다.
- 보관 복원과 현재 사용 판정은 나눈다. 원본이 정확히 복원돼도 현재 freshness/owner epoch/한도/서울 날짜/22시 경계를 통과하지 못하면 현재 계좌 관측으로 사용할 수 없다.

**C. 신선한 세대를 실제 startup 대조에 연결한다.** 새 경로는 rehearsal 전용으로, 별도 startup composer가 같은 Journal·guard/baseline store·독립 heads·명시 clock과 정확한 provider를 소유하게 한다. 기존 legacy `_publish`와 혼합하지 않는다.

1. 이미 완료된 신선한 세대는 실제 active Journal transaction 안의 `provider.read`와 기존 Controller 현재 owner/완료clock 검사를 거쳐 사용한다. 오래된 세대는 역사 자료/후속 세대의 predecessor로만 보존한다.
2. 새 자료가 필요한 경우 실제 candidate 수집 및 원본 보관 → 실제 guard commit 완료 → 결과 보관/재읽기 → **별도의 실제 Journal transaction** 안 `publish_committed` 순서로 연결한다. commit은 스스로 Journal transaction을 열므로 열린 transaction 안에서 다시 호출하지 않는다. BundleStore lock을 잡고 Journal을 기다리거나, provider publication lock을 별도로 만들어 역순을 만들지 않는다.
3. publication 이후 Controller/Runner는 이미 구현된 actual paired read와 원 transaction ID 제한을 그대로 사용한다. 새 startup 경로에서 baseline advance/commit/CAS를 두 번째로 호출하지 않는다. 게시 전 실패는 기존 provider를 유지하며, 이미 이동한 head 때문에 옛 reader가 거절하는 상태를 숨기지 않는다.
4. **보유·미체결 대조 결과를 실제 상태로 보고한다.** 기존 `Runner._reconcile`/`Controller.reconcile`을 재사용한다. 자기 namespace의 RESERVED는 기존 로컬 취소만, DISPATCHING/UNKNOWN/ACKNOWLEDGED/PARTIAL은 실제 상태 조회와 정확한 fill/fee/client identity 대조를 한다. 재시작이나 저장 장애를 매도 신호로 만들지 않는다.
5. `Controller.reconcile`도 현재 committed account와 owner epoch를 먼저 요구한다. stale 원본만 있는데 broker 상태를 조회했다는 이유로 계좌를 fresh로 만들 수 없다. 조회 결과의 누적 체결이 보관 endpoint의 authoritative fills와 다르면 현재 구현은 일치 상태로 확정하지 않는다. 그때는 해당 fill을 포함한 새 계좌 세대를 먼저 만들고 다시 대조한다. 옛 endpoint 뒤에 `fill/reconciled` 행이 붙었다는 사실만으로 옛 계좌를 갱신하지 않는다.
6. source의 전체 보유/주문 목록과 로컬 주문 상태를 비교해 외부 주문·식별 불가·누락·부분 체결 잔량을 남긴다. 로컬 Journal에 없는 주문을 삭제하거나 자동으로 우리 주문으로 채택하지 않는다. 해소되지 않은 대조 상태를 `READY`로 보고하지 않는다. 새 진입 차단과 기존 정책하의 보유 감시/독립 reducing 가능 여부를 분리한다.

첫 구현은 **한 번의 재시작 복원 → fresh successor 확정/게시 → 실제 대조 → 준비/보류 결과 반환**으로 완결한다. 이를 모든 monitor/slot/terms-renewal 스케줄에 연결하거나 controlled mode를 해제하는 작업은 다음 단계다. 결과에는 `execution_ready=False`를 유지한다. 이것은 비권한 결과 표시이며 검증을 대신하는 boolean은 아니다.

## 3. 정확 복원·새 세대·새 운영 설계가 필요한 경우

| 관측 상태 | 허용되는 처리 | 금지되는 추정 |
| --- | --- | --- |
| 원 보관 bytes 및 실제 commit 상태가 일치, 아직 fresh | 원 시각 그대로 실제 provider/Controller 검사 후 rehearsal 대조 | constructor 성공을 승인/운영 준비로 간주 |
| 원본 bytes는 정확하지만 현재 stale | 역사 재생·원본/주문 상태 보존, 새 현재 세대 필요 표시 | `observed_at`/owner 관찰/서버 시각을 지금으로 변경 |
| 원 receipt만 유실, 실제 COMPLETE와 원 입력·heads가 일치 | 실제 CONSISTENT 재검증으로 관찰한 replay receipt를 별도 기록 | 잃어버린 최초 receipt의 prefix·시각을 창작 |
| 정확한 보관 사본이 있으나 현재 primary/독립 head가 손상 | 손상 분리, 정확 복원 후보와 기존 anchor 대응 확인; 지원되지 않는 쓰기 복구는 명시 보류 | 연구용 서명 복구 API를 계좌 head의 승인으로 전용, head 재초기화/낮춤 |
| 단절 없이 유효한 직접 successor 자료가 존재 | 기존 PR56 direct-successor 검사 후 게시 | 세대를 건너뛰거나 서로 다른 source epoch를 동일 stream으로 표시 |
| recorder가 멈췄거나 긴 중단 중 자료가 없음 | 관측 공백·영향 범위를 보존, 신규 진입 차단, 별도 source/역사 catch-up 설계 필요 | REST 재조회로 당시 호가·지연·실패·중간 평가 최고점/저점을 복구했다고 주장 |

정확 복구는 신뢰할 수 있는 기존 별도 anchor/catalog와 연결된 전체 파일·hash가 기준이다. 계좌 세대 기록은 자동으로 owner 서명된 연구 artifact가 되는 것이 아니다. primary/backup/head 전체가 같은 과거로 함께 대체되는 공격까지 막았다고 주장하지 않는다. 기존 보관 기능이 지원하지 않는 계좌 checkpoint 자동 복구를 이번 접합부에 끼워 넣지 않는다.

장시간 중단은 특히 자동 처리할 수 있다고 가정하면 안 된다. `continuous.py::validate_path`는 한 구간과 watermark 수신 폭을 최대 30초로 제한한다. `continuous_guard.py`는 `path.start == baseline.asof`, 같은 stream epoch/연속 sequence, 시작을 둘러싼 원 owner 관찰, 신선한 끝 시각을 요구한다. `commit_continuous_guard`의 FRESH commit에도 실제 commit 시점의 30초 검사가 있다. 따라서 이미 확정된 pending 작업의 정확 마무리와, 며칠 전부터 빠진 구간을 지금 새로운 FRESH commit으로 채우는 것은 다르다. 후자는 현재 구현 범위가 아니며 timestamp 재작성으로 해결하지 않는다.

## 4. 실제 Upbit 근거로 아직 충족하지 못하는 계약

이는 단순 구현량이 남은 문제가 아니다. 현재 저장소의 계약은 다음 근거를 요구하며, 이번 읽기 작업에서 외부 API 계약이나 실제 공급자를 검증하지 않았다.

- `collector.py::CoverageEvidence`는 조회 구간 전체에 manual/API 체결·transfer·reward·잔고 변동이 없다는 사전 계좌 fence와 credential/main-pocket identity, origin 이후 보존 이력 등을 요구한다. `upbit_collector.py::_validate_proofs`는 이 검토된 주장과 원 holdings/open-orders가 비어 있던 anchor를 검사한다. 기존 보유 계좌의 현재 잔고를 새 zero anchor로 만들 수 없다.
- 같은 파일의 수집 끝 fence는 여러 race를 탐지하지만 명시적으로 **ABA 가능성**을 남긴다. GET 성공/JWT 인증, 앞뒤 balances 일치, pagination 완료, REST Date·수신 시각은 누락된 동시 체결/자산 이동이 없었다는 증명이 아니다.
- `continuous.py`의 `complete-ordered-account-marks-and-fills-v1` 계약은 opening marks, 모든 mark/fill의 공통 순서, 끝 watermark, 누락된 계좌 변화가 없음을 인증해야 한다. 파일 자체가 Upbit book snapshots/trade IDs/heartbeat/로컬 sequence가 gap-free venue sequence가 아니며 **production coverage verifier를 제공하지 않는다**고 명시한다.
- PR #54/#55의 read batch는 요청 전후·raw 응답·실패를 실제 보관하지만 `source_authenticated`, `coverage_verified`, `execution_ready`는 모두 False다. 그 기록은 관측한 응답의 증거이지, 관측하지 못한 이벤트의 부재 증거가 아니다.
- `ContinuousUpbitCandidateSource.__call__`의 `CONTINUOUS_LIVE_RISK_INTEGRATION_REQUIRED`와 현재 Coordinator/committed Runner의 rehearsal 제한을 유지한다. 임의 `VerifiedCoverage`, 로컬 서명·hash, `complete=True`, 성공 callback으로 해제하지 않는다.

필요한 후속 설계 결정은 **현재의 강한 연속 extrema 계약을 실제 어떤 공급자·거래소 근거와 운영 통제로 충족할 수 있는지**다. 확보할 수 없다면 지원 가능한 source 계약/중단 복구 방식/적용 시장을 별도로 설계해야 한다. 지금 REST에 없는 보장을 코드로 생성할 수는 없다. 샘플 관측 기반으로 정의를 바꾸는 일은 원금·최고점 보호 요구에 영향을 주므로 이번 저장·재시작 단위에서 조용히 변경하지 않는다. 이 문서는 현재 API로 영원히 불가능하다는 외부 조사 결론도 내리지 않는다.

## 5. 제안 파일 소유와 필수 검사

아래 파일명/API는 **새 제안**이며 현재 존재하거나 구현됐다는 뜻이 아니다.

| 소유 | 최소 변경 |
| --- | --- |
| 형식 | 새 `execution_launch/guard_generation_format.py`: 입력/commit 결과의 bounded canonical codec. 기존 capture packet 참조와 정확 package 복원, 원 시각·predecessor/receipt 역할 구분. |
| 보관 접합 | 새 `execution_launch/guard_generation_archive.py`: 기존 BundleStore에 입력 사전보관/결과 후보관/실제 재읽기. `retain_guard_input`, `record_guard_completion`, `read_guard_generation` 수준의 명시 API. 자체 승인·head 초기화·새 writer 없음. |
| 시작 composition | 새 `execution_launch/committed_startup.py`: 실제 저장소 분류, 동일 provider의 직접 successor 게시, rehearsal 실제 대조 및 명확한 보류 결과. 기존 Coordinator에는 독립 명시 startup 경로를 연결할 때만 좁게 수정하고 legacy `_publish`는 호출하지 않는다. |
| 독립 검사/등록 | 새 codec/archive/startup 검사 파일. root가 허용 writer/CAS·source closure·독립 signer parity와 acceptance registry를 검토한다. 새로운 의존 파일이 승인 대상 source closure에서 빠지지 않게 한다. |

검사는 임시 실제 signed owner log·Journal·guard/baseline store와 별도 heads·실제 commit/provider/Controller/DryRunAdapter를 사용한다. source/coverage 입력은 명시 합성이며 production issuer 양성 검사로 보고하지 않는다.

- 두 프로세스 수명을 흉내 낸 객체 재구성: 보관 원본 → 실제 commit → 새 실제 provider → 대조. baseline/guard 상태·high/floor/daily stop/halt·원 시각 유지, read/publication 추가 advance/CAS=0, 기존 세대 제한 유지.
- 입력 보관 전/중, PREPARE 뒤, 각 store/head 사이, COMPLETE 뒤 결과 기록 전/중, 게시 전/후의 중단. 원 불완전 기록 보존, 동일 입력만 재시도, 다른 입력·head·잘못된 prefix·중복 COMPLETE 거절. 중첩 Journal 호출=0 및 lock 역순 없음.
- 정확 receipt suffix 복원, 정상 후속 risk/kill 행, pending 및 torn 기록, 전체 원본 누락/부분 백업 손상. 실제 현재 저장소를 읽지 않는 canned result/verify-success 대체 금지.
- stale 30초 경계, 완료 중 시간 초과/역행, 서울 날짜·22시, current owner/code/effective limits 변경, 다음 stream epoch/중간 세대 누락. 과거 값으로 current 승인이나 관찰을 발급하지 않음.
- 실제 RESERVED 로컬 취소, UNKNOWN/DISPATCHING 보존·자동 재전송 0, partial fill의 누적 수량·fee·identity, capture 뒤 늦은 체결, 계좌의 외부 미체결/보유 불일치. 해당 새 실제 계좌 세대를 얻기 전 대조 완료 주장 금지.
- 실제 같은 provider에서 새 세대 이후 정상 독립 reducing 대조, 진입 daily-stop/kill과 보유 관리 구분. 원 위험 하한 완화·저장 장애/기한 도달만으로 자동 매도 0.
- source issuer가 없는 운영 요청은 기존 거절 유지. Windows native 실제 실행/전원 장애 복구는 Linux 합성 검사와 구분해 별도 NOT_RUN으로 기록한다.

새 사용자 입력 없이 위 코드·격리 회귀를 진행할 수 있다. 실운영 source 계약, 원 계좌 anchor/보존 이력, 실제 Windows 경로·지속 실행·권한 확인은 추정할 수 없으며, 다음 단계의 완료 보고에서도 별도 미해결 조건으로 남겨야 한다.
