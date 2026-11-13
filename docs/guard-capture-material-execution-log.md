# P2 I3a 실행 기록 — 원본 수집 자료와 guard 입력 재현

작성일: 2026-11-13. 개발 기준: `ed1b4567fbd8161f1998a56241993880afccbb71`, 작업 브랜치 `gpt/continuous-capture-material`. PR47 main을 통합한 `933a7bc8c38c9eff0a5bd08f29e95ac8794dc172`에서 관련 274개가 한 프로세스에서 모두 통과했다. 실거래 준비 완료를 뜻하지 않는다.

## 구현된 범위

`ContinuousUpbitCandidateSource.collect`는 원래 수집한 응답 바이트·요청 경로와 매개변수·영수증 시각·정규화 계좌·manifest를 분리된 스냅샷으로 보존한다. 최초 anchor, coverage, fee 자료, 수집 시작 요청 시각, collector 내부의 실제 시작·완료 시각 두 개, 최초 응답 시각, preview 평가 시각도 유지한다. 내부 시작 시각은 과거 주문 조회 범위에 영향을 주므로 최초 응답 시각이나 새 시각으로 대체하지 않는다. 원래 포착한 계좌와 경계 시각에 경로로 재구성한 endpoint 계좌를 구분한다.

새 `prepare_guard_capture_material`은 메모리 안에서 실제 `collect_upbit`를 다시 실행한다. 원래 응답을 정확한 순서·경로·매개변수·scope로 한 번씩 소비하며 누락·추가·재정렬·남은 응답을 거절한다. 재현된 계좌와 원본 보존 계좌, manifest 및 preview 전체를 타입까지 비교하므로 해시만 다시 계산한 계좌 교체나 `Decimal(1)` 대신 `True`를 넣는 변조를 허용하지 않는다. 실제 FIFO·수수료·기초 현금·보유량·구간 체결에서 `AccountCaptureInputs`와 `ValuationInputs`를 도출한다.

기존 `VerifiedCoverage`는 요청·경로·계좌·원래 검증 시각에 연결된 외부 주장으로만 재검사한다. 재현 과정은 새 source verifier를 호출하거나 인증 성공을 만들어 내지 않는다. 결과의 `execution_ready`와 `source_authenticated`는 항상 `False`다. 전체를 일관되게 새로 만든 자료도 별도의 감사용 자료일 뿐 실제 거래소 출처 증명이 아니다.

## 입력·시각·R6 경계

- 복사·JSON 해석·collector 재실행 전에 응답 2,000개, 개별 8 MiB, 총 64 MiB 및 계좌·행·경로 크기를 제한한다. 정규화된 자료도 깊이·노드·문자열·바이트·정수 폭을 제한하며 선언되지 않은 dataclass 속성을 거절한다. Decimal은 자릿수·지수 범위를 먼저 확인한 후 비교한다. 크기 초과는 admission 거절이며 자료 손상이라고 표시하거나 정상 내용을 잘라내지 않는다.
- 원래 외부 시작 → collector 내부 시작 → 최초 응답 → collector 완료 → preview 시각의 순서를 검사한다. 새 `now`는 나이 확인에만 사용하며 관측 시각을 갱신하지 않는다. 날짜 경계·22시·반개구간 체결·기존 30초 신선도 검사를 유지한다. 호출자가 전달한 `now`만 사용하므로 이 결과 자체가 처리 완료 시점의 운영 신선도를 보증하지 않는다.
- R6: 자정 수집에 사용한 임시 `RiskBaseline`은 공개 capture나 stage에 보존하지 않는다. 원래 입력으로 재도출하고 저장된 digest와 비교한다. `path_source`에 전달되는 capture에도 임시 baseline이나 bundle이 없다. 이전 상태·anchor·fee·capture는 외부 통합 호출 전에 분리하며 기존 약한 참조 회귀 경계를 유지한다.
- `account_interval.py`는 CRLF를 보존했다. 새 helper는 파일·head·owner 상태·현재 시계를 읽거나 commit·publication·주문을 수행하지 않는다. 수집 단계의 기존 경로 감사 파일 저장은 그대로이며 전체 수집 패킷 저장으로 설명하지 않는다.

## 첫 개발 검증 결과 — 최종 아님

`capture-material-dev1`: **56개 중 55 PASS, 1 FAIL, 0 NOT_RUN**, 10.057초. 실패 원문과 실행 기록을 보존했다. 실제 수집 시간이 31초가 된 경우 원래 로직이 `EVIDENCE_STALE_OR_FUTURE`로 거절했으나 테스트 helper의 허용 오류코드 정규식이 너무 좁아 assertion이 실패했다. 테스트 helper에 기존의 유효한 EVIDENCE 진단을 포함하고 해당 사례가 정확히 EVIDENCE_STALE_OR_FUTURE를 요구하도록 테스트 두 줄만 수정했다. runtime 소스 변경은 없다. 해당 수정 및 PR47 main을 포함한 최종 관련 검사에서 이 사례와 남은 경계/반개구간 검사가 모두 통과했다.

이 실행의 Python/YAML fingerprint(테스트 포함):

```text
5a1227f72587849b09fdc90a8237225c5523b095a10a990cba01468ebad632e3
```

기록: `capture-material-dev1-summary.json`, `capture-material-dev1-rows.json` 및 checkpoint/start 기록. 19개 credential 환경 이름을 KEYLESS로 설정했고, import·발견 작업 전부터 완료까지 실제 home 메타데이터와 소스가 불변임을 확인했다. QA 파일을 원래 상태로 복원했다. 합성 GET 응답·합성 coverage/owner 주장을 사용했으며 실제 파서, 사전에 만든 recorder, 임시 baseline store, 경계 재구성, FIFO와 guard 계산을 실행했다. 이는 실제 거래소 연결·실계좌 장애·Windows 운영 검증이 아니다.

## 최종 관련 통합검사

`capture-material-integration-final`: **274 PASS / 0 FAIL / 0 NOT_RUN**, 한 프로세스 **216.983초**. 새 23개와 기존 계좌 수집·연속 경로·baseline·guard/commit·Coordinator·Runner·권한/쓰기/계좌 경계 검사를 포함한다. 전체 저장소 suite를 다시 실행한 것은 아니다. 초기 개발 결과와 합산하지 않는다.

검증 head: `933a7bc8c38c9eff0a5bd08f29e95ac8794dc172`. Python/YAML fingerprint: `ebc44cbcf7089a23b348ec6db57d7e1cd2aa16eb84cb2156e873dfcf70f6a409`. 19 KEYLESS, 동결 소스 전후 일치, import/검사 목록 구성 전부터 완료까지 실제 홈 metadata 일치, QA 복원. PR47 병합 때 test registry 충돌은 기존 다섯 incident 모듈과 새 material 모듈을 모두 유지하여 해결했다. 정상 호가·보유·원본을 삭제하는 fallback이나 위험정책 완화는 없다. Linux에서 선택한 검사이며 실제 Windows/계좌/API/주문을 검증했다고 표시하지 않는다.

## 남은 연결

전체 원본 패킷의 불변 저장·백업·재시작 재현, 실제 거래소의 연속 경로 완전성과 출처를 인증하는 source, 현재 owner 권한·유효 한도 및 처리 완료 시각의 재검사, 보유·미체결 주문 대조, guard commit 뒤 publication, production consumer 연결은 아직 없다. 기존 Controller·Runner·Coordinator의 운영 거절과 손실 하한·위험정책은 이번 변경으로 완화하지 않았다. 이 자료 생성만으로 자동매매를 시작하거나 새 거래 권한을 승인하지 않는다.

구체 계약: `TRADEGEN_P2_I3A_API_CARD_2026-11-13.md`. 후속 연결 범위: `TRADEGEN_P2_NEXT_BRIDGE_PLAN_2026-11-13.md`.

법률, 세무, 투자 조언이 아니며 면허를 가진 자문가가 아니다
