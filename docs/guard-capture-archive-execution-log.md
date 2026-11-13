# P2 I3b-archive 실행 기록

2026-11-13. 작업 기준 `f20dd1f8efe7c178c63c5579c2751f7647c5c8c0`, 브랜치 `gpt/full-capture-archive`, runtime commit `b1122b1a2cefd021f3ede9e161d3fea470d23e63`. 수정 후 관련 **161 PASS / 0 FAIL / 0 NOT_RUN**, 한 프로세스 **34.278초**로 검증했다. 실제 자동매매 준비 완료를 뜻하지 않는다. 최초 실행 159 PASS / 2 FAIL은 아래 결함·수정 이력으로 보존한다.

## 구현한 경로

새 `guard_capture_format.py`는 원래 I3a stage와 이전 BaselineState를 닫힌 타입 형식으로 표현한다. 원 응답 bytes는 별도 receipt payload에 그대로 보존하고, 순서·요청 경로/매개변수·scope·수집 시각·fee·captured accounts·재구성 endpoint·전체 path/preview를 연결한다. Decimal 부호·자릿수·지수와 bool/int/string, tuple, optional 필드를 구분한다. 임의 class import, pickle, eval로 복원하지 않는다. 원 baseline은 기존 strict baseline codec으로 다시 확인하며 임시 자정 RiskBaseline/AccountBundle은 저장하지 않는다.

`packet`은 baseline 및 모든 원 응답의 SHA/길이/논리 ID 목록을 연결하고, 별도 domain digest가 packet 전체를 식별한다. 원 응답의 whitespace·숫자 표기를 다시 쓰거나 같은 bytes의 반복 관찰을 삭제하지 않는다. 기존 receipt.sha256은 원 주장으로 보존하며 raw bytes와의 의미 일치는 실제 I3a 감사에서 판정한다. 바깥 payload inventory는 실제 보관 bytes의 SHA와 길이를 검증한다.

새 `guard_capture_archive.py`는 기존 **실제 BundleStore**만 받는다. `RAW_ARCHIVED`의 run/attempt ID는 `capture-`와 전체 packet SHA를 결합하고 revision을 고정한다. 알파벳으로 시작해야 하는 기존 ID 문법을 유지하며 digest를 자르지 않는다. 모든 payload는 `other_input`, required, COLLECTED의 정확한 전체 목록으로 기록된다. 이는 수집 패킷의 inventory이며 연구 평가·전략 승인·source completeness를 의미하지 않는다.

저장은 기존 `archive_raw`를 사용한다. 반환 receipt만 믿지 않고, 실제 primary·backup·catalog·retained head에 연결된 전체 자료를 `read_raw(require_backup=True)`로 다시 읽고 정확한 manifest·파일 목록·typed packet identity를 비교한다. 새로운 저장 엔진이나 writer 예외, 자동 provision/head seed/adopt는 추가하지 않았다. 중단·한도 초과·미확정 head는 기존 저장소의 거절을 유지하고 원본을 삭제하거나 잘라내지 않는다.

## 제한과 재현 의미

- raw 응답은 최대 2,000개, 개별 8 MiB, 합계 64 MiB다. metadata packet은 최대 64 MiB, baseline은 최대 64 KiB, 전체 payload는 최대 128 MiB+64 KiB이며 설정값은 이 상한 이하로만 줄일 수 있다. JSON byte/depth/node, typed 필드·행·문자열·Decimal과 전체 inventory를 제한한다. typed metadata가 원 raw와 별개로 차지하는 용량도 실제 manifest/object/store 정책과 primary·backup admission에 포함된다. 이론상 모든 최댓값이 모든 저장 설정에 들어간다고 보장하지 않는다.
- 읽을 때는 실제 catalog의 manifest reference 길이를 먼저 검사하고 bounded manifest만 읽어 전체 파일 수·개별/합계 크기·고정 이름·role을 확인한다. 그 후에 전체 payload graph를 읽고 decode한다. 저장소의 일반 object payload 상한을 packet manifest 한도로 잘못 사용하지 않는다.
- `replay_guard_capture_archive`는 저장소에서 새로 읽어 복원한 stage를 실제 `prepare_guard_capture_material`에 전달한다. 원 preview 시각만 historical evaluation time으로 사용하며 caller가 현재 시각을 조작하는 옵션은 없다. retained coverage callback을 다시 호출하거나 verified_at을 갱신하지 않는다. 실제 collector의 순차 원 응답 재소비·FIFO·경계/preview 재도출을 사용한다.
- 감사 후에도 실제 전체 primary/backup을 다시 읽고 root/head 및 bytes를 비교한다. 성공 결과에는 `historical_replay=True`가 있지만 `source_authenticated`, `current_freshness_verified`, `guard_committed`, `execution_ready`는 모두 false다. 자기 hash·옛 baseline snapshot·보관 head는 현재 계좌/guard predecessor나 운영 승인으로 승격되지 않는다.

## 기존 경로와 새 consumer의 구분

기존 `ContinuousUpbitCandidateSource.collect`와 path-only 감사 파일의 의미는 변경하지 않았다. 기존 path 파일이 전체 수집 패킷이나 독립 restart authority가 된 것이 아니다.

새 명시적 `collect_archive_guard_capture` wrapper가 actual source.collect → 실제 전체 보관/readback → 반환된 실제 archive digest로 다시 읽기 → historical audit를 연결한다. 보관 전 메모리 stage를 그대로 감사 성공으로 반환하지 않는다. 구조적으로 보관 가능한 패킷이 실제 의미 감사에서 실패하면 raw archive를 유지하고 `CollectedCaptureArchive`에 보관 receipt, replay=None, 고정 audit_error_code를 반환한다. 감사 실패를 저장 실패로 숨기거나 성공한 자료만 남기기 위해 원본을 수정하지 않는다. 저장/형식 실패는 감사 성공으로 반환하지 않는다.

이 단위는 collector가 실제 반환한 완성 stage를 다룬다. 수집 도중 중단되어 외부로 반환되지 않은 receipt나 애초 관측하지 않은 자료를 복원해 주지 않는다.

## 검사 상태와 남은 범위

첫 실행의 두 실패는 fixture 문제가 아니다. `_preflight_read`의 고정 `GuardCaptureArchiveError`가 실제 `BundleStore._locked` 안에서 발생하면 기존 저장소의 ValueError 정규화에 잡혀 `BUNDLE_STORE_IO_REFUSED`로 바뀌었다. 따라서 primary-only 보관은 `CAPTURE_ARCHIVE_BACKED_RAW_REQUIRED`, metadata 한도 초과는 `CAPTURE_ARCHIVE_RESOURCE_LIMIT`로 구분되지 못했다. 자료를 통과시키거나 검사를 약화한 문제가 아니라 실제 진단 의미가 유실된 코드 결함이다.

adapter만 수정했다. admission은 실제 lock 안에 그대로 두고 자체 `GuardCaptureArchiveError`만 내부에서 보존한 뒤, 실제 lock/root cleanup이 정상 완료된 경우에만 밖에서 다시 발생시킨다. 실제 저장소 cleanup·무결성 오류가 생기면 그것이 보존된 admission 오류보다 우선한다. 기존 BundleStore·예외 상속·테스트 기대값은 바꾸지 않았다. 수정 소스는 AST/diff 및 독립 읽기 검토를 완료해 재동결했으며, 같은 161개 검사에서 두 진단과 기존 경계가 모두 통과했다.

첫 실행 source fingerprint:

```text
4c78c5ca4c0dfde5723538d9ba5fe425a712d2a9858eba498985731939d758c9
```

수정 adapter 파일 SHA256:

```text
645620454185baab3e60fdd28ab2a65622a64d2d8eefc3323b0cfcd6127f3734
```

실패 원문은 `capture-archive-integration-dev1-summary.json`과 `capture-archive-integration-dev1-rows.json`에 보존했다. 첫 실행은 19 KEYLESS 이름을 사용했고 import/discovery 전부터 완료까지 실제 home 메타데이터 및 소스 불변이 확인됐다. QA를 원본으로 복원했다. 최초 실행과 최종 실행은 서로 별개의 기록이며 검사 수를 합산하지 않는다.

작성된 새 검사는 닫힌 codec·원문/Decimal scale·전체 inventory·구조/용량 경계와, 실제 fake-GET collector → 사전에 만든 recorder → I3a stage → 실제 임시 BundleStore primary/backup/head → 새 reader → 실제 I3a 재현을 대상으로 한다. flat/held/partial fill, 22시/자정 captured-vs-endpoint 구분, 원 clock trace, 감사 실패 원본 보존, exact retry·미확정 publication·one-sided rollback·root 교체, 감사 후 backup 변조, 원 stage alias 변조 격리와 현재 신선도 거절을 포함한다. 최종 관련 161개에는 새 형식 28개·실제 연결 23개 및 기존 material·account interval·bundle store·권한/쓰기 guard를 포함했다. 전체 저장소 suite를 다시 실행한 결과는 아니다.

최종 label `capture-archive-integration-final`: **161 PASS / 0 FAIL / 0 NOT_RUN**, 단일 **34.278초**. Python/YAML fingerprint `ccfaf65861e63594ab36f8908ffc242b123f8f1899ee595c722753c659e32228`. 19 KEYLESS, import/발견 전부터 종료까지 실제 home metadata·소스 불변, QA 원복. `capture-archive-integration-final-{start,checkpoint,rows,summary}.json`에 정확한 목록과 결과를 보존했다. 위 runtime commit은 이 검증한 소스와 일치한다.

이 검사에서 **새 reader 객체 구성**은 실제 OS 프로세스 종료·재시작이나 Windows 전원 장애 검증이 아니다. 실제 API·사용자 홈·계좌·키·주문을 사용하지 않으며 연구/GET·coverage/owner fixture는 합성 자료임을 표시한다. 첫 실행과 수정 후 재실행의 격리·QA 복원 기록은 구분한다.

현재 source identity/history retention, 연속 marks/fills의 실제 venue completeness issuer, 당시 pre/post owner 인증, trusted completion 시각 검사, 현재 baseline/guard/control head 연결, guard commit 뒤 publication 및 production Runner/Controller/Coordinator 소비는 남아 있다. full packet 보관과 역사 감사만으로 자동매매를 시작하지 않는다. 기존 손실 하한·daily stop·halt·위험정책은 완화하지 않았다. 별도 directory를 물리적으로 독립된 장애 영역이라고 주장하지 않으며 모든 저장소/anchor의 coherent rollback을 막는 외부 보장을 추가하지 않았다.

계약: `TRADEGEN_P2_I3B_CAPTURE_ARCHIVE_API_2026-11-13.md`. 설계: `TRADEGEN_P2_I3B_CAPTURE_ARCHIVE_PLAN_2026-11-13.md`.

법률, 세무, 투자 조언이 아니며 면허를 가진 자문가가 아니다
