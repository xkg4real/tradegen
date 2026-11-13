# TRADEGEN recovered selection — 사용자 명령 진입점 준비 조사

작성: 2026-11-13. 읽기 전용 조사다. `/workspace/tradegen-recovered-selection-1113`의 기존 CLI·운영 문서·검사와 현재 구현 중인 recovered consumer API 계약을 대조했다. 새 코드·검사·HEAD·PR·실제 홈·키·API 변경이나 실행은 없다. 이 계획을 구현 완료 기능으로 세지 않는다.

## 추천하는 다음 한 단위

**기존 `execution_launch.research_recovery_cli`에 명시적인 `select-recovered` 명령 하나를 추가한다.** 검증 완료한 새 `authenticate_recovered_study_selection`을 실제 입력 파일에서 호출하고, 연구용 선발 결과·release record ID·현재 검증 head만 JSON으로 보여준다. 운영 가이드와 실제 CLI 수직 검사를 함께 끝내는 범위다. 새로운 UI·scheduler·서명기·저장 엔진을 만들지 않는다.

새 core consumer와 CLI는 같은 승인된 작업 단위에서 병렬 구현한다. 두 소스·검사를 함께 동결한 뒤 새 집중 검사와 관련 회귀를 수행하는 것으로 결정됐다. 별도 core 검증 완료를 기다려 CLI 개발을 중단하지 않는다. 새 consumer의 의미나 실제 승인 검사를 CLI에서 재구현하지 않는다.

## 현재 연결과 빈틈

| 실제 파일/경로 | 현재 기능과 다음 연결 |
| --- | --- |
| `research_recovery_cli.py::_arguments/main` | `route-register`, `run-once`, `inspect`, `list-pending`. 성공 복구는 역사적 결과이며 selection 플래그가 모두 false다. `run-once`는 source 설정을 받지만 새 selection 명령에는 source가 필요 없다. |
| `research_incident_cli.py::main`의 `incident-aware-select` | 일반 `authenticate_incident_aware_selection`을 호출하므로 복구본도 논리적 bundle/raw 보류에 걸려 거절된다. 이 명령을 자동 recovered fallback으로 바꾸지 않는다. |
| `sealed_study_cli.py::main`의 `select-sealed` | 실제 연구·서명·factory 검증을 하지만 incident namespace를 받지 않는 별도 연구용 API다. 보류 우회 방법으로 안내하지 않는다. |
| `research_incident_cli.py::_selection_inputs` | 기존 bounded archive/profile/window/history policy/source review 읽기와 audit ID 처리. 반복 review 128개 상한, 문서에서 study ID 도출·중복 거절 등을 새 명령에도 재사용할 수 있다. |
| `research_recovery_cli.py::open_attempt_store/_destination`, `research_incident_cli.py::open_incident_store` | 실제 명시 roots·limits·head를 여는 기존 경로. 자동 provision/head 채택을 하지 않는다. |
| `docs/research-recovery-operator-guide.md` | 실제 route 등록 → run-once → inspect/list-pending까지의 PowerShell 흐름이 있다. 현재 “보류 해제·연구 선발 없음” 설명을 기존 명령의 범위로 유지하고 새로운 연구용 후속 절만 추가한다. |

검색한 Python 호출부에서는 이 연구/사건/복구 경로를 자동 호출하는 UI·scheduler 진입점을 찾지 못했다. 명시 CLI가 현재 사용자 흐름을 가장 작게 완성하는 caller다. 자동 scheduler는 이 작업의 전제가 아니며 여기서 복구 결과를 거래 Launcher에 전달하지 않는다.

## 정확한 명령 계약

```text
python -m execution_launch.research_recovery_cli select-recovered
  --attempt-root ROOT --attempt-backup-root ROOT --attempt-head-root ROOT
  --attempt-head-name NAME --attempt-limits FILE
  --incident-root ROOT --incident-backup-root ROOT --incident-head-root ROOT
  --incident-head-name NAME --incident-limits FILE
  --destination-root ROOT --destination-backup-root ROOT
  --destination-head-name NAME --destination-limits FILE
  --digest SHA --route-id SHA --incident-id SHA
  --archive-attestation FILE --profile FILE --window FILE --head-root ROOT
  [--history-storage FILE]
  [--source-review FILE ...] [--audit STUDY_ID=LOGICAL_ID ...]
```

`--head-root`는 기존 sealed-study 명령과 같은 **독립 LiveHistory head root**다. 목적지 catalog head와 혼동하지 않도록 help와 PowerShell 변수명을 구분한다. audit는 목적지 확정 graph에 이미 포함된 논리 파일 ID다. `--source-review`는 기존 서명 문서이며 새 서명 요청이 아니다. NO_SELECTION 연구에는 적격 review가 0개일 수 있고, 정확한 문서 집합은 실제 core가 판단한다.

이 명령은 `--source-root`, `--source-backup-root`, `--source-head-name`, `--source-limits`를 요구하거나 허용하지 않는다. 성공한 목적지와 원 signature artifact가 있으면 원 source가 없어도 호출할 수 있어야 한다. `--now`, provider/context/평가 결과/승인 bool, 개인 키·거래키·password, 자동 활성화·전송·delivered·provision 옵션도 거절한다.

기존 `parse_options`는 operator utility가 쓰는 정확한 non-repeated 계약이므로 그대로 유지한다. 새 subcommand만 기존 incident CLI의 bounded required/optional/repeated parser를 사용한다. 새 명령을 위해 기존 다른 명령의 옵션 허용 범위를 넓히지 않는다. 입력 문서를 모두 bounded로 읽고 검증한 다음 기존 store factory를 호출한다. 실제 UTC `datetime.now(timezone.utc)` clock과 그 **같은 객체**로 `CurrentOwnerAuthority(clock=clock)` 하나를 명령 내부에서 만든다. CLI 인자로 시간을 주입하지 않는다.

actual 호출은 다음 한 번이다.

```python
authenticate_recovered_study_selection(
    destination, args['digest'], incident_store=incidents, attempts=attempts,
    route_id=args['route-id'], incident_id=args['incident-id'],
    **selection_inputs, clock=clock, authority_provider=authority,
)
```

`run_recovery_once`나 signer를 재호출하지 않는다. 현재 original approval·철회·expiry·single actual evaluation·release commit·최종 head/clock 검사는 core가 수행한다. 기존 `inspect`가 보이는 terminal 성공만으로 결과를 합성하지 않는다. 명령은 연구 release 기록과 기존 history binding/owner 검증 상태를 쓸 수 있으므로 “읽기 전용 명령”이라고 소개하지 않는다.

## 출력과 실패

exact `RecoveredSelectionAssessment` 타입·scope와 operational false flags를 확인하고, 출력은 safe summary allowlist로 만든다. 실제 nested selection의 status/reasons·selected study ID, route/attempt/incident/bundle IDs, destination binding, release_record_id, incident/attempt heads와 sequence, 검증 완료 시각, research_selection_ready를 보여준다. 원본 payload·경로·서명 원문·owner log·금액·전체 profile·개인 키는 출력하지 않는다.

SELECTED라면 실제 ready와 non-null release record가 일치해야 한다. NO_SELECTION 계열은 실제 status를 그대로 표시하고 ready=False·release_record_id=None을 요구한다. output의 `current_operational_use`, `execution_ready`, `automatic_operational_recovery_supported`, `network_delivery_performed`는 false다. global quarantine_released=True 또는 “거래 가능” 문구는 없다.

정상 SELECTED/NO_SELECTION 응답은 기존 CLI처럼 exit 0, 고정 REFUSED/중단은 exit 2다. 일반 OS/경로/예외 메시지는 기존 redaction 규칙으로 고정 진단으로 바꾸며, 거절을 일반 selector 재시도나 원 source 재수집으로 대체하지 않는다. 다른 명령의 출력·exit code·역사적 의미는 유지한다.

## 실제 사용자 흐름과 파일 분할

운영 가이드의 기존 ① 사전 route 등록 ② `run-once` ③ 실제 성공 outcome 확인 뒤에 ④ 명시 `select-recovered` ⑤ 출력 연구 결과 확인 절을 붙인다. 기존 `$AttemptArgs`, `$IncidentArgs`를 재사용하고 새 `$RecoveredSelectionArgs`에는 destination·연구 문서만 넣는다. source 설정을 포함한 기존 `$RecoveryArgs`를 그대로 전달하는 예시는 만들지 않는다. 개인 경로 대신 `<...>` placeholder를 사용한다.

실제 수정 범위는 `execution_launch/research_recovery_cli.py`, `docs/research-recovery-operator-guide.md`, 새 `tests/launch_recovered_selection_cli.py`다. 공용 bounded `_selection_inputs`/parser는 기존 것을 재사용하고 다른 명령의 동작은 변경하지 않는다. registry/엄격한 import/쓰기 guard 변경이 정말 필요하면 root가 정확한 범위만 검토한다. 새로운 출처·승인 verifier나 CLI 내부 평가 결과 cache는 없다.

## 수직 검사

- 기존 `tests/launch_research_recovery_cli.py`의 actual temporary store·서명·route/run fixture와 `tests/launch_sealed_study_cli.py`의 actual current owner/서명·fixed/carry evaluator·factory/history 기반을 재사용한다. 새 recovered integration fixture가 동결되면 그것을 우선 공용으로 사용한다. 양성 검사에서 core/issuer/서명 verifier를 성공 fake로 대체하지 않는다.
- 실제 source 손상 → 실제 복구 terminal → source 제거 → 새 CLI → 실제 current 검사·단일 evaluation·release 기록·SELECTED 출력. private signer/키 읽기 추가·source 구성·provision·HTTP·주문·알림 호출 0을 검사한다.
- 실제 NO_SELECTION은 record 없음·ready false, 추가 incident/만료·현재 signed revocation/artifact 손상은 고정 거절. 일반 `incident-aware-select`는 이전처럼 held를 거절한다.
- 같은 route 재호출은 기존 record identity를 보존하되 현재 검증을 반복한다. 실제 record/head 실패나 late revocation을 성공으로 출력하지 않는다. 이미 남은 역사적 복구 결과도 거절 후 현재 권한으로 표시하지 않는다.
- source/clock/key/provider/activate 옵션·중복/누락/알 수 없는 옵션·과도한 반복·잘못된 audit·원문/limits 초과는 적절한 사전 경계에서 거절한다. 도움말은 I/O 0, private 예외 redaction, 실제 한 clock/provider, strict result consistency와 기존 명령 전체 회귀를 포함한다.

## 입력 없이 개발할 부분과 실제 운영 조건

CLI 연결·bounded parser/출력·가이드·실제 임시 fixture 회귀는 추가 사용자 결정 없이 개발 가능하다. 실제 실행은 명시 목적지/incident/attempt/history 설정, 실제 복구 성공 기록, 기존 유효 archive/source 승인과 현재 profile/window가 필요하다. 값이 없으면 거절하며 기본 owner 경로·승인·현재 시장 관측을 추측하지 않는다. 정확 복구 때문에 새 서명을 요구하지 않지만 코드 변경·만료·철회·자료/규칙/window 변경에 필요한 기존 승인 조건은 유지한다.

이 명령까지 끝나면 **복구 후 연구용 선발을 사람이 한 번 호출하는 흐름**이 연결된다. 실계좌 source/coverage·account/guard publication·운영 Launcher·거래 활성화·보호 보유/미체결 대조가 끝났다는 뜻은 아니다. UI/scheduler는 이후 이 same public consumer를 명시적으로 호출할 수 있으나 자동 활성화와 묶지 않는다. 사용자의 손실 하한과 “오류·재시작 자체는 매도 신호가 아님” 요구는 그대로 유지한다.

법률, 세무, 투자 조언이 아니며 면허를 가진 자문가가 아니다
