# Windows에서 Telegram·Android 알림 보내기

Windows 릴레이는 TRADEGEN이 이미 기록한 경보를 읽고, 선택한 채널에 일반 알림을 보낸다. Telegram의 **알림 확인** 버튼과 Android의 원격 알림은 운영자가 지정한 HTTPS 사이트의 `/approvals/`를 연다. 승인·서명은 그 사이트에서 대상과 범위를 확인하고 별도로 진행한다. 승인 서비스의 배포 상태와 Android 설치 방법은 [Android 안내](../android/README.md)를 참고한다.

## 1. Windows에 비공개 저장 위치 준비

TRADEGEN을 실행하는 Windows 사용자로 PowerShell을 연다. 다음 명령은 저장소가 해당 사용자의 `OneDrive\Desktop\TRADEGEN`에 있는 경우다. 프로젝트용 Python 3.13 가상 환경과 의존성은 [설치 절차](../README.md#setup)를 따른다.

```powershell
$project = Join-Path $env:USERPROFILE 'OneDrive\Desktop\TRADEGEN'
$privateDir = Join-Path $env:LOCALAPPDATA 'TRADEGEN\notifications'
$stateDir = if ($env:TRADEGEN_HOME) { $env:TRADEGEN_HOME } else { Join-Path $env:USERPROFILE '.tradegen' }
$python = Join-Path $project '.venv\Scripts\python.exe'
$config = Join-Path $privateDir 'config.json'
$db = Join-Path $privateDir 'relay.sqlite3'
New-Item -ItemType Directory -Force -Path $privateDir | Out-Null
Set-Location -LiteralPath $project
```

`%LOCALAPPDATA%\TRADEGEN\notifications`의 **속성 → 보안**에서 작업을 실행할 사용자와 필요한 시스템 관리자만 읽고 쓸 수 있는지 확인한다. 토큰·구독 파일·비공개 키·설정·전송 이력은 이 로컬 폴더에 둔다. 이 값들을 공용 저장소, OneDrive의 기록 폴더, 메신저 또는 작업 스케줄러 인수에 넣지 않는다.

## 2. 알림을 받을 사람과 단말 등록

- **Telegram**. 운영자가 BotFather에서 전용 봇을 발급받고, 수신자가 개인 대화에서 봇을 시작한다. 운영자는 자기 봇에서 확인한 개인 대화의 양수 숫자 ID를 아래 설정에 문자열로 입력한다. 봇 토큰 한 줄은 비공개 폴더의 `telegram-token.txt`에 ASCII 또는 UTF-8(BOM 없음)로 저장한다. 봇에는 거래소 키나 소유자 서명키가 필요 없다.
- **Android**. 아래 명령을 최초 1회 실행한다. 기존 키 파일이 있으면 그대로 보존한다. `push-config.json`만 독립 운영 HTTPS 사이트의 `/android/push-config.json`에 배포한다. 기기에서 푸시 등록 후 내보낸 `tradegen-android-subscription.json`을 비공개 경로로 옮겨 위 폴더에 저장한다. 현재 릴레이는 Android Chrome이 발급한 Google FCM Web Push 구독 1개와 Telegram 개인 대화 1개를 각각 설정할 수 있다. 기기 등록과 테스트는 [Android 안내](../android/README.md)를 따른다.

```powershell
& $python -m tools.notifications.relay setup-vapid --private-key (Join-Path $privateDir 'vapid-private.pem') --public-config (Join-Path $privateDir 'push-config.json')
```

처음 등록할 때만 아래 예시로 `config.json`을 만든다. 두 채널을 모두 사용할 때의 형식이다. 한 채널만 준비했다면 해당 설정만 남긴다. `origin`은 소유자가 확인한 운영 HTTPS 도메인을 소문자로 입력한다. 경로·포트·끝 슬래시는 넣지 않는다. `sources`에서는 사용할 기존 기록만 선택하고 한 개 이상 유지한다. 다른 위치의 `TRADEGEN_HOME`을 사용하는 경우 릴레이와 원래 앱 모두 같은 설정으로 실행한다.

```powershell
$settings = [ordered]@{
    origin = Read-Host '운영 HTTPS origin'
    telegram = @{ token_file = 'telegram-token.txt'; chat_id = (Read-Host 'Telegram 개인 대화 숫자 ID') }
    android = @{ subscription = 'tradegen-android-subscription.json'; vapid_private_key = 'vapid-private.pem' }
    sources = @{
        control_root = Join-Path $stateDir 'execution-control'
        compliance_log = Join-Path $stateDir 'compliance\alerts.jsonl'
        execution_alerts = Join-Path $stateDir 'execution\alerts.jsonl'
    }
}
[IO.File]::WriteAllText($config, ($settings | ConvertTo-Json -Depth 4), [Text.UTF8Encoding]::new($false))
```

## 3. 첫 발송과 수신 확인

1. Windows에서 기존 경보와 미처리 사건을 먼저 검토한다. 과거 경보까지 모두 받으려면 `baseline`을 생략한다. 검토한 기존 경보를 이번 전송에서 제외하려면 상시 릴레이를 시작하기 **전에** 아래 첫 명령을 실행한다. `baseline_unavailable`에 나온 소스는 기록되지 않았다. `baseline`은 기존 대기 건을 취소하지 않는다.
2. `queue-test`는 설정한 채널마다 시험 알림 하나를 대기열에 추가한다. `status`로 `pending`을 확인한다. 이미 상시 릴레이가 실행 중이면 대기열은 다음 주기에 바로 발송될 수 있다.
3. 실제 기기 시험 시 마지막 `run --deliver --once`를 실행한다. 이 명령은 한 번 소스를 읽고, **시험 건과 당시 발송 가능한 일반 경보**를 함께 전송한다. 단말에 표시된 일반 알림을 열어 운영 HTTPS 도메인과 `/approvals/`를 확인한다. 운영 승인함이 아직 준비 중이면 안내 화면이 열릴 수 있다. 승인이나 주문은 이 점검에 필요 없다.

```powershell
# 선택 사항. 검토한 과거 경보를 제외할 때만 실행
& $python -m tools.notifications.relay baseline --config $config --db $db
& $python -m tools.notifications.relay queue-test --config $config --db $db
& $python -m tools.notifications.relay status --db $db
# 실제 단말에 발송할 때 실행
& $python -m tools.notifications.relay run --deliver --once --config $config --db $db
```

## 4. Windows 상시 실행과 장애 복구

작업 스케줄러의 **작업 만들기**에서 위와 같은 Windows 사용자·일반 권한을 지정한다. **트리거**는 로그온할 때로 설정한다. 로그인 전에 운영해야 한다면 **시작할 때**와 **사용자의 로그온 여부에 관계없이 실행**을 선택하고 해당 사용자로 로컬에서 등록한다. **동작 → 프로그램 시작**에 넣을 세 값은 같은 PowerShell 창에서 다음과 같이 확인한다.

```powershell
$python
'-m tools.notifications.relay run --deliver --config "{0}" --db "{1}"' -f $config, $db
$project
```

출력된 순서대로 **프로그램/스크립트**, **인수 추가**, **시작 위치**에 입력한다. 시작 위치는 저장소의 실제 전체 경로다. 기존 인스턴스가 있으면 새 인스턴스를 시작하지 않도록 하고, 장기 실행의 시간 제한을 해제한다. 작업을 시작한 뒤 `status`로 확인한다. 기본 확인 주기는 30초이며 `--interval`로 5~60초를 지정할 수 있다. 대기열과 이력은 재시작 후 동일한 `$db`에서 이어진다. 채널·구독·토큰을 변경했다면 릴레이를 재시작해 새 설정을 읽힌다.

| `status` 항목 | 운영자가 확인할 내용 |
|---|---|
| `baseline`, `pending`, `sending` | 각각 과거 이력으로 등록한 건, 발송 대기, 현재 발송 시도 중인 건의 채널별 수다. |
| `accepted` | Telegram 또는 Web Push 서비스가 요청을 접수했다. 화면 표시·열람은 사용자가 기기에서 확인한다. |
| `needs_review`, `held` | 인증 오류, 만료된 구독, 예기치 않은 응답, 반복 실패 등의 건수와 사유다. 기기 재등록이나 토큰 교체 등 해당 원인을 처리한다. |
| `source_errors` | 읽기 실패 중인 입력 이름이다. 원래 앱에서 기록 생성 여부·경로·권한을 확인한다. 경보가 처음 발생해야 파일이 생기는 소스도 있다. 손상 징후가 있으면 원래 앱의 복구 절차를 따른다. |

일시적 전송 오류에는 자동 재시도 간격과 공급자의 대기 시간을 적용한다. 기본 자동 시도 한도는 사건·채널별 5회다. 요청 전송 직후 연결이 끊기거나 릴레이가 종료되면 공급자의 접수 결과가 불명확해 같은 알림이 두 번 표시될 수 있다. 원인 해결 후 아래 예시처럼 해당 채널의 보류 건을 다시 대기열에 넣는다. 이 명령은 그 채널의 **모든 보류 건**에 적용된다. 기기 분실 시 릴레이를 정지하고 해당 구독을 제거하거나 교체한 뒤 재시작한다. Android 푸시 구독과 승인용 패스키는 각각 폐기한다.

```powershell
& $python -m tools.notifications.relay status --db $db
& $python -m tools.notifications.relay retry-held --channel android --db $db
```

## 어떤 경보가 들어오는가

| 입력 | 릴레이가 읽는 기존 기록 |
|---|---|
| `control_root` | `execution-control` 원장의 체크포인트와 해시 연결을 검증한 뒤 보호 하한 위반에 따른 `halt`, 서울 날짜별 첫 일일 손실 중단을 전달한다. |
| `compliance_log` | 규정 점검기가 `compliance/alerts.jsonl`에 남긴 Windows 토스트 시도다. 토스트 표시 실패 건도 포함한다. |
| `execution_alerts` | 기존 E1 조회기가 `execution/alerts.jsonl`에 기록한 적색·황색 사건이다. 예를 들어 등록 출금 주소 변경 또는 알 수 없는 미체결 주문이 해당한다. E1 일일 보고서의 발송 표시를 바꾸지 않는다. |

이 경로는 기존 생산자가 저장한 사건만 읽는다. 앱이나 조회기가 중단돼 새 기록 자체가 없으면 릴레이가 거래 상태를 알아낼 수 없다. 두 JSONL은 한 번에 파일당 16 MiB, 행당 256 KiB, 10만 행까지 검사한다. 불완전한 행·잘못된 형식·용량 초과가 있으면 그 입력 전체를 보류한다. 형식 검사만으로 완전한 행 단위의 삭제를 탐지할 수 없으므로 원본 보존과 검증은 해당 기록의 정책을 따른다. 다른 소스와 이미 대기 중인 경보는 별도로 처리한다. Telegram에는 일반 문구와 고정 링크만 보내며 Android에는 빈 푸시 메시지를 보낸다. 사건의 금액·계좌·호가·서명 내용은 원래 기록 또는 인증된 화면에서 확인한다.
