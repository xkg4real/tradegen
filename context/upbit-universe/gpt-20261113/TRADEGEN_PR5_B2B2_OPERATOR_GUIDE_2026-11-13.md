# TRADEGEN PR5 B2b-2 — 정확 원본 복구 운영 절차 초안

2026-11-13. **초안: 최종 통합검사·배포 확인 전에는 운영 완료 안내로 사용하지 않습니다.** 실제 CLI와 최초 저장소 준비 코드를 정적으로 대조했습니다. 아래 명령을 실제 PC에서 실행한 기록이나 Windows 실기기 검증 결과는 아닙니다.

이 절차는 미리 등록한 연구 보관물의 정확한 원본과 기존 서명 문서를 별도 목적지에 복원하고, 시도·결과·알림 대기를 기록합니다. **자료 보류 해제, 연구 선발, 전략 승인, 거래 활성화는 수행하지 않습니다.** 실패 연구의 원본도 보존되며, 복구됐다고 평가 통과 연구로 바뀌지 않습니다.

## 1. 준비 조건과 입력값

- 최종 배포된 코드와 해당 코드에 대한 유효한 소유자 승인, 현재 소유자 상태를 읽을 수 있는 실행 환경이 필요합니다. 아래 명령은 승인서를 만들거나 개인 서명키를 요구하지 않습니다.
- 원본 연구 저장소가 정상일 때 사건 감시 대상과 복구 경로를 먼저 등록해야 합니다. 손상 후 처음 만든 경로로 원래 저장소의 정체성을 추측하지 않습니다.
- 원본·원본 백업, 목적지·목적지 백업, 사건 저장소의 세 경로, 복구 시도 저장소의 세 경로는 서로 분리합니다. 기존 경로를 교체하거나 중첩하지 않고, 링크·재분석 지점과 동기화 작업 폴더를 사용하지 않습니다.
- 원본과 목적지의 저장 정책은 일치해야 합니다. 사건 저장소와 목적지 저장소·head는 기존의 명시적 운영자 절차로 준비돼 있어야 합니다. 이 문서는 새 **복구 시도 저장소**의 최초 준비만 다룹니다.
- 시도 저장소의 세 디렉터리는 미리 만든 **서로 다른 빈 디렉터리**여야 합니다. 각 limits JSON은 해당 저장소 형식에 맞게 준비합니다. 서로 다른 종류의 limits 파일을 바꿔 쓰거나 임의 기본값을 넣지 않습니다.
- `ORIGINAL_ATTESTATION_JSON`은 등록 때와 실행 때 사용하는 **동일한 원래 archive attestation 문서**입니다. 손상 대상 밖에 별도로 보관합니다. 새 서명이나 수정 문서로 바꿔 넣지 않습니다.
- 모든 `<...>`는 실제 사용자 환경에서만 치환합니다. 경로·서명 원문·소유자 기록·키·실제 데이터는 공개 저장소나 문의 메시지에 붙여 넣지 않습니다. ID는 해당 명령이 반환한 소문자 64자리 SHA-256을 사용합니다. head 이름은 준비한 이름과 정확히 같아야 하며, 시도 head 이름 형식은 `[a-z][a-z0-9-]{0,63}`입니다.

PowerShell에서 아래 설정을 한 번 준비합니다. 전체 절차를 한꺼번에 붙여 넣지 말고, 각 명령의 JSON 결과를 확인한 뒤 다음 단계로 진행합니다. 종료 코드 2 또는 `status: REFUSED`이면 해당 고정 오류 코드를 확인하고 멈춥니다.

```powershell
Set-Location '<TRADEGEN_REPOSITORY>'
$TradegenPython = '<TRADEGEN_VENV_PYTHON_EXE>'

$AttemptArgs = @(
  '--attempt-root', '<ATTEMPT_ROOT>',
  '--attempt-backup-root', '<ATTEMPT_BACKUP_ROOT>',
  '--attempt-head-root', '<ATTEMPT_HEAD_ROOT>',
  '--attempt-head-name', '<ATTEMPT_HEAD_NAME>',
  '--attempt-limits', '<ATTEMPT_LIMITS_JSON>'
)
$IncidentArgs = @(
  '--incident-root', '<INCIDENT_ROOT>',
  '--incident-backup-root', '<INCIDENT_BACKUP_ROOT>',
  '--incident-head-root', '<INCIDENT_HEAD_ROOT>',
  '--incident-head-name', '<INCIDENT_HEAD_NAME>',
  '--incident-limits', '<INCIDENT_LIMITS_JSON>'
)
$OriginalArgs = @(
  '--sealed-root', '<SOURCE_ROOT>',
  '--backup-root', '<SOURCE_BACKUP_ROOT>',
  '--head-name', '<SOURCE_HEAD_NAME>',
  '--limits', '<SOURCE_LIMITS_JSON>',
  '--digest', '<BUNDLE_SHA256>'
)
$RecoveryArgs = $AttemptArgs + $IncidentArgs + @(
  '--source-root', '<SOURCE_ROOT>',
  '--source-backup-root', '<SOURCE_BACKUP_ROOT>',
  '--source-limits', '<SOURCE_LIMITS_JSON>',
  '--destination-root', '<DESTINATION_ROOT>',
  '--destination-backup-root', '<DESTINATION_BACKUP_ROOT>',
  '--destination-head-name', '<DESTINATION_HEAD_NAME>',
  '--destination-limits', '<DESTINATION_LIMITS_JSON>',
  '--archive-attestation', '<ORIGINAL_ATTESTATION_JSON>'
)
```

## 2. 빈 복구 시도 저장소를 한 번만 준비

```powershell
& $TradegenPython -m tools.owner.research_recovery provision @AttemptArgs
```

예상 상태는 `EMPTY_RECOVERY_STORE_PROVISIONED`입니다. 빈 기록과 독립 head의 시작점만 만듭니다. 기존 기록이 있거나 준비 중 중단된 디렉터리에 다시 실행하여 초기화하지 않습니다. 실패하면 디렉터리와 남은 파일을 그대로 보존하고 운영자가 조사합니다.

## 3. 원본이 정상일 때 감시 대상과 복구 경로를 사전 등록

먼저 같은 사건 저장소에 정상 원본을 등록합니다. 이미 정확히 같은 대상으로 등록했다면 기존 등록을 확인합니다.

```powershell
& $TradegenPython -m execution_launch.research_incident_cli register @IncidentArgs @OriginalArgs
```

`TARGET_REGISTERED`를 확인한 뒤 복구 경로를 등록합니다.

```powershell
& $TradegenPython -m execution_launch.research_recovery_cli route-register @RecoveryArgs --source-head-name '<SOURCE_HEAD_NAME>' --digest '<BUNDLE_SHA256>'
```

`RECOVERY_ROUTE_REGISTERED`와 반환된 `route_id`를 비공개 운영 기록에 보관합니다. 이때 실제 원본 전체·백업·원래 서명·현재 소유자 상태·별도 목적지를 검사합니다. 등록 자체가 복구 실행이나 자료 사용 승인은 아닙니다. `--source-head-name`과 `--digest`는 경로 등록에만 넣습니다.

## 4. 실제 사건을 확인하고 사건 ID 확보

원본을 정상적으로 열 수 있는 상태에서 다음 명령으로 실제 자료를 검사합니다. 예시 실행을 위해 자료를 손상시키지 않습니다.

```powershell
& $TradegenPython -m execution_launch.research_incident_cli check @IncidentArgs @OriginalArgs
& $TradegenPython -m execution_launch.research_incident_cli inspect @IncidentArgs
```

정상 관측은 `TARGET_CHECKED`, 실제 보류는 `TARGET_HELD`입니다. `check` 결과의 `incident_ids`에서 해당 등록 대상에 연결된 사건 ID를 확인합니다. `inspect`는 등록·사건 수 등을 조회하며 새 사건 ID를 만들어 주지 않습니다. 이미 보류된 대상의 재확인은 기존 보류를 유지하며 보류 해제나 수리 후 정상 판정으로 간주하지 않습니다.

**원본 디렉터리 전체가 사라졌다면** 일반 `check`가 저장소를 열지 못할 수 있습니다. 이 경우 이미 기록된 실제 사건 ID와 사전 등록된 경로가 있어야 아래 복구 실행을 할 수 있습니다. 임의 ID를 만들거나 빈 원본 디렉터리를 재생성하여 등록을 우회하지 않습니다. 사전 등록·실제 사건이 없으면 이 제어기의 실행 조건을 충족하지 못한 상태로 조사합니다.

## 5. 동일 경로·사건·원래 서명으로 한 번 실행

```powershell
& $TradegenPython -m execution_launch.research_recovery_cli run-once @RecoveryArgs --route-id '<ROUTE_SHA256>' --incident-id '<INCIDENT_SHA256>'
```

이 명령은 현재 UTC와 실제 소유자 검증기를 내부에서 구성합니다. 사용자 지정 시각, 승인 여부, 성공 여부, 키를 입력하는 옵션은 없습니다. 원본의 primary가 없어져도 **등록 당시의 원래 경로**를 유지합니다. 실제 복사는 등록된 백업에서 별도 목적지로만 수행하며 손상 원본은 변경하지 않습니다.

`RECOVERY_ATTEMPT_OBSERVED`는 결과 관측이 반환됐다는 뜻입니다. 반드시 `phase`, `execution_count`, `observed_at`를 함께 확인합니다. `phase: EXACT_ARCHIVE_RESTORED`는 원본 전체와 서명 보관물을 검사한 결과가 기록됐다는 뜻이며, 현재 선발·거래 자격이나 보류 해제를 뜻하지 않습니다. 완료된 동일 시도를 다시 호출하면 **과거 완료 기록**을 반환할 수 있으므로 새 검증 시각으로 읽지 않습니다.

복구 전 권한·자료 검증에서 거절된 시도도 기록되고 같은 예산을 사용합니다. 복사가 시작됐다는 뜻은 아닙니다. 결과 기록에 실패하면 성공으로 처리하지 않습니다.

## 6. 결과와 알림 대기 조회

```powershell
& $TradegenPython -m execution_launch.research_recovery_cli inspect @AttemptArgs
& $TradegenPython -m execution_launch.research_recovery_cli list-pending @AttemptArgs
& $TradegenPython -m execution_launch.research_incident_cli list-pending @IncidentArgs
```

각각 `RECOVERY_STORE_VERIFIED`, `RECOVERY_NOTIFICATIONS_PENDING`, `NOTIFICATIONS_PENDING` 결과를 확인합니다. 시도 저장소 검증은 목적지 자료가 지금도 정상이라는 재검증이 아닙니다. `record_semantics: historical_observation_not_current_eligibility`를 그대로 적용합니다.

outbox는 저장된 알림 대기 목록입니다. **이 단위는 Telegram·이메일 등 네트워크 전송을 하지 않으며**, 목록 조회나 성공 결과만으로 전송·수신 완료를 기록하지 않습니다. 자동 승인 요청·서명도 수행하지 않습니다. `quarantine_released`, `current_use_eligible`, `research_selection_ready`, `execution_ready`, `network_delivery_performed`는 모두 `false`입니다.

## 7. 재시도·중단·소스 소실 처리

| 상황 | 처리 |
|---|---|
| 재개 가능한 실패 또는 완결된 START 뒤 프로세스 중단 | 기록이 온전할 때만 같은 경로·사건·문서·목적지로 `run-once`를 다시 호출합니다. 기본값은 최초 1회 + 재개 최대 2회, **합계 최대 3회**입니다. 설정은 더 엄격할 수 있습니다. |
| 재개 간격 미충족 | 마지막 신뢰 가능한 실행 시작/결과 관측 중 더 늦은 시각부터 **최소 60초**입니다. 설정에 따라 더 길 수 있습니다. `RECOVERY_RETRY_NOT_DUE`를 우회하려고 시계·파일·설정을 바꾸지 않습니다. 한 명령 안에서 반복 실행하거나 기다리는 루프는 없습니다. |
| 실행 예산 소진 | `RECOVERY_EXECUTION_BUDGET_EXHAUSTED`를 보존하고 조사합니다. 새 저장소·새 ID로 예산을 우회하지 않습니다. |
| `AUTHORITY_REFUSED`, `DESTINATION_UNCONFIRMED`, `EVIDENCE_REFUSED` | 자동 재개를 끝내는 상태입니다. 새 프로세스로 재실행해도 제한을 지우지 않습니다. 남은 원본·부분 복사본·결과를 보존합니다. |
| `READ_UNAVAILABLE`, `RESOURCE_LIMIT`, `PARTIAL_UNVERIFIED` | 원인을 확인한 뒤 동일 시도의 시간·횟수·권한 조건이 충족될 때만 재개할 수 있습니다. 읽기 실패를 영구 원본 소실이나 복구 성공으로 추정하지 않습니다. |
| 기록 쓰기 중 중단, 불완전 journal/head/backup, 경로·잠금 불일치 | 작업을 멈추고 모든 기록을 보존하여 운영자가 조사합니다. **삭제·truncate·reset·head 채택·기존 저장소 재provision을 하지 않습니다.** 정상적으로 확정된 START 뒤 중단과 손상된 시도 저장소를 구분합니다. |
| 원본 primary만 없음, 등록된 백업은 정상 | 사전 등록과 실제 사건을 바탕으로 백업에서 복구할 수 있습니다. 원래 primary를 새 디렉터리로 바꾸어 등록 상태를 갱신하지 않습니다. |
| 원본 또는 원본 백업이 없어졌지만 목적지는 이미 완성 | 미완료 시도 재개 시 실제 목적지 전체와 **원래 서명 artifact 및 그 백업**을 독립 재검증할 수 있습니다. 캐시된 성공 객체나 파일 존재만으로 완료 처리하지 않습니다. 이미 terminal인 시도의 재호출은 과거 기록 조회입니다. |
| 목적지도 불완전하고 필요한 원본 백업을 읽을 수 없음 | 성공으로 기록하지 않습니다. 현재 확보된 자료와 거절·부분 상태를 보존합니다. |

정확한 복구는 **원래 서명 bytes를 그대로 보존**합니다. 원래 유효기간·코드·키·철회·소유자 기록 조건이 계속 충족될 때 복구 자체를 이유로 재서명을 요구하지 않습니다. 만료된 승인을 연장하거나 새 코드·자료에 승계하지 않습니다. 새 자료의 재계산·재수집과 새로운 승인은 별도 절차입니다. 기존 손실 하한·halt 정책은 이 절차로 변경되지 않습니다.

## 정적 확인 근거와 남은 확인

- 실제 `execution_launch/research_recovery_cli.py`, `tools/owner/research_recovery.py`, `execution_launch/research_incident_cli.py`의 명령·필수 옵션·거절·출력 형식을 대조했습니다. 위 명령에는 실행 경로에 없는 옵션을 넣지 않았습니다.
- 시간·횟수·terminal 조건은 `research_recovery.py`와 `research_recovery_attempts.py`를 대조했습니다. 최종 통합검사·배포 버전·실제 Windows 실행 확인은 상위 세션 결과로 확정해야 합니다.
- 이 문서 작성 중 프로그램·테스트·실제 서명·복구·전송·주문을 실행하지 않았습니다. 모든 명령은 치환 전 자리표시자 예시입니다.

법률, 세무, 투자 조언이 아니며 면허를 가진 자문가가 아니다
