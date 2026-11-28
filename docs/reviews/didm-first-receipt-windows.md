# Windows에서 첫 호가와 GDELT 파일 수신 확인

TRADEGEN 연구 명령이 포함된 버전과 QUANTGEN의 `tools.didm.collect_daily`가 설치된 PC에서 PowerShell로 실행한다. 아래 명령은 공개 시세와 GDELT 파일을 한 차례 조회한다. 거래 키와 전자서명은 필요하지 않다. 앱을 켰다는 사실만으로 수신을 확인할 수는 없다.

## 1. 실행 위치와 저장 위치

```powershell
Set-Location (Join-Path $env:USERPROFILE 'OneDrive\Desktop\TRADEGEN')
$tg = (Resolve-Path '.\.venv\Scripts\python.exe').Path
$qgDir = (Resolve-Path (Read-Host 'QUANTGEN 저장소의 실제 폴더')).Path
$qg = (Resolve-Path (Join-Path $qgDir '.venv\Scripts\python.exe')).Path
$research = Join-Path $env:LOCALAPPDATA 'TRADEGEN-research\first-receipts'
$coord = Join-Path $env:LOCALAPPDATA 'TRADEGEN-A0\public-budget'
$log = Join-Path $research 'didm-log'
$stores = Join-Path $research 'didm-stores'
```

가상환경 이름이 다르면 각 프로젝트가 이미 사용하는 Python 실행 파일로 바꾼다. 같은 PC에서 Upbit 공개 요청을 보내는 다른 TRADEGEN 기록기도 기존 공용 조정 폴더 `$coord`를 공유해야 한다.

## 2. Upbit KRW-BTC 호가 한 건

TRADEGEN 앱을 완전히 종료한 경우에만 `OFF`를 입력한다. 앱이 실행 중이면 `ON`을 입력하고 앱이 생성·갱신하는 실제 상태 JSON 경로를 지정한다. 상태에는 현재 UTC 초의 `as_of`, `floor_halt`, `daily_stop`, `block_causes` 또는 `prior_block_active`가 필요하다. 상태 파일을 확보할 수 없으면 실행 중인 앱을 종료한 뒤 `OFF`로 진행한다.

```powershell
$mode = Read-Host '실제 앱 상태 (OFF 또는 ON)'
switch ($mode) {
    'OFF' { $statusArgs = @('--app-not-running') }
    'ON'  { $statusPath = (Resolve-Path (Read-Host '앱이 제공하는 상태 JSON 경로')).Path
            $statusArgs = @('--status-file', $statusPath) }
    default { throw '앱 상태를 확인하세요.' }
}
$quotes = Join-Path $research ("quotes-" + $mode.ToLowerInvariant())
$c = & $tg -m tools.research.upbit_quote_recorder capture --market KRW-BTC --scope first-receipt --archive-dir $quotes --coordination-dir $coord --cycles 1 --allow-public-network @statusArgs | ConvertFrom-Json
if ($LASTEXITCODE -ne 0 -or $c.status -ne 'CAPTURED') { throw ("수신 실패 " + $c.reason) }
@'
import json, sys, time
from datetime import datetime, timezone
from tools.research._study_common import read_verified_chained_log
rows, _ = read_verified_chained_log(sys.argv[1], "quotes.jsonl", pinned_head=sys.argv[2])
row = rows[-1]["data"]
assert row["kind"] == "quote"
obs = row["observation"]
age = int(time.time()) - row["as_of"]
print(json.dumps({"received_utc": datetime.fromtimestamp(row["as_of"], timezone.utc).isoformat(),
    "best_bid_krw": obs["bid"], "best_ask_krw": row["ask"], "age_seconds": age,
    "same_second": row["same_second"], "status_stale": row["status_stale"]}))
'@ | & $tg - $quotes $c.archive_head_sha256
```

바로 출력된 UTC 시각과 경과 초로 이번 수신인지 확인한다. `same_second=false`이면 체결가와 호가가 서로 다른 초에 도착했다. `status_stale=true`이면 앱 상태가 오래됐다. 기록된 양쪽 가격은 조회 시점의 값이다. 이용 제한 응답이 오면 공용 폴더의 대기 시간을 따른다.

## 3. GDELT 파일과 연구용 누적 범위

QUANTGEN은 추가 공급자 옵션을 생략하면 GDELT만 수집한다. `--source gdelt`는 TRADEGEN에서 판정할 소스를 지정한다. 이전에 기록한 미수신 슬롯이 있으면 한 실행에서 최대 8개까지 같은 공급자에 재시도한다.

```powershell
$g = & $tg -m tools.research.didm_run_log run-collector --log-dir $log --stores-root $stores --source gdelt --collector-cwd $qgDir "--collector-arg=$qg" --collector-arg=-m --collector-arg=tools.didm.collect_daily | ConvertFrom-Json
$collectorExitCode = $LASTEXITCODE
if ($collectorExitCode -notin 0,3) { throw ("GDELT 확인 실패 " + $g.reason) }
$g | Select-Object target_slot,fetched_slots,backfilled_slots,missing_slots,slot_receipts
$cut = [DateTimeOffset]::UtcNow.ToString('o')
& $tg -m tools.research.didm_coverage --log-dir $log --pinned-head $g.log_sha256 --as-of $cut
```

`slot_receipts`에서 동일한 UTC 슬롯의 events와 GKG 증거를 확인한다. 종료 코드 3이면 이번 원장에 미완료 결과가 남았다. 마지막 명령은 직전 UTC 정시 기준으로 24시간 96개 전부와 7일 672개 중 최소 639개에 대한 부족분을 각각 표시한다. 1회 수신과 연구 데이터 충족, 실제 주문 승인은 각각 별도로 확인한다.
