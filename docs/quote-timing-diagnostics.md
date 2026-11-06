# 소유자 PC의 공개 호가 시각 진단

상태: 합성 응답으로 검증하는 진단 도구. 개발 중 실제 거래소 요청은 하지
않았습니다. 이 도구는 계좌·키·서명·주문을 다루지 않고 PC 시계도 변경하지 않습니다.

## 실행 순서

1. 새 코드의 PR을 검토하고 병합한 뒤 해당 Windows 체크아웃을 맞춥니다.
2. TRADEGEN 폴더에서 도움말을 확인합니다. 도움말과 인자 없는 실행은 오프라인입니다.

   ```powershell
   .\.venv\Scripts\python.exe -m execution_launch.quote_diagnostics --help
   ```

3. 본인 PC에서 실제 공개 호가 요청을 하려면 다음 명령을 직접 실행합니다.
   `KRW-BTC`는 시간 진단 예시이며 투자 대상 선정 결과가 아닙니다.

   ```powershell
   .\.venv\Scripts\python.exe -m execution_launch.quote_diagnostics capture --symbol KRW-BTC --samples 20 --interval-seconds 1
   ```

4. 출력 JSON의 `reason`, `measured_samples`, `strictly_admitted_samples`와
   각 표본의 `strict_quote_reason`을 확인합니다. 요청 실패·잘못된 응답·PC 시계
   역행·Ctrl+C가 있으면 그 전에 측정한 표본을 남기고 중단합니다. 코드는 파일을
   쓰지 않습니다. 필요하면 출력만 저장하고 계좌 자료나 비밀값을 덧붙이지 않습니다.
5. 진단 후 실제 연구를 시작하기 전에 원래의 표·코드·한도·연구 검토 절차를
   완료합니다. 이 명령의 성공이나 출력은 어떤 서명·활성화도 대신하지 않습니다.

표본 수는 1~60, 요청 사이 대기는 1~5초입니다(기본 20개/1초). 대기는 직전
요청 종료 뒤 시작하므로 고정 간격의 틱 기록이나 연속성 증명이 아닙니다.
각 요청에는 기존 E1의 시간 제한, 0.2초 pacing 및 허용된 GET 재시도가 적용됩니다.
추가 재시도는 하지 않습니다. 다른 프로그램과 IP 호출 한도는 공유합니다.

## 읽는 방법과 한계

- `apparent_book_age_us`: PC 수신 시각에서 원래 호가 timestamp를 뺀 값입니다.
  단위는 마이크로초이며 1,000µs는 1ms입니다. 이 값은 timestamp가 생성된 뒤
  수신될 때까지의 지연과 두 시계 차이가 섞인 값입니다. 네트워크 단방향 지연이나
  PC 시계 오차만을 따로 추정한 값이 아닙니다. 음수도 원래 그대로 표시합니다.
- `received_minus_http_date_us`: PC 수신 시각과 HTTP Date의 차이입니다.
  HTTP Date는 메시지 생성 시각의 초 단위 표현이므로 수십 ms 정밀도의 동기화
  증거가 아닙니다. 이 값으로 PC 시계를 자동 보정하지 않습니다.
- `request_wall_duration_us` / `request_monotonic_duration_ns`: 요청 전후의
  벽시계·단조시계 경과입니다. transport pacing과 재시도가 포함될 수 있으므로
  순수 RTT라고 부르지 않습니다. 단위도 각각 µs와 ns로 다릅니다.
- `strict_quote_admitted`: 그 응답이 기존 `parse_orderbook` 규칙을 그 시점에
  통과했는지입니다. 미래 호가, 오래된 호가, 큰 HTTP Date 불일치는 측정값을
  남겨도 기존과 같이 거부합니다. 표시된 코드는 최초 거부이며 다른 오류가
  없다는 증명은 아닙니다. 시간 검사가 호가 깊이 검사보다 먼저이므로, 시간 때문에
  거부된 응답의 전체 호가 구조는 검증되지 않았고 `book_structure_verified=false`로
  남습니다. 원본 시각을 바꾸거나 재라벨링하지 않습니다.
- `diagnostic_complete=true`와 exit 0은 요청한 수의 진단 표본을 수집했다는
  뜻입니다. 거부된 호가만 수집해도 진단 자체는 완료될 수 있습니다.
  `execution_ready=false`, `clock_synchronized=false`,
  `clock_offset_estimate_us=null`은 항상 유지됩니다. 짧은 표본이 이후 며칠의
  시계·네트워크 안정성이나 자정 계좌 경계 캡처 성공을 보장하지 않습니다.

출력에는 시각·시간차·고정 진단 코드·원본 바이트의 해시만 포함하며 가격, 수량,
원본 응답, 계좌 식별자, 인증값은 출력하지 않습니다. 해시는 무결성 참조일 뿐
거래소 서명이나 계좌 증거가 아닙니다.

## 구현과 공식 계약

2026-11-06 [Upbit 호가 조회 공식 문서](https://docs.upbit.com/kr/reference/list-orderbooks)를
재확인했습니다. 기존의 공개 GET, 단일 KRW 종목, level 0, count 30만 사용합니다.
공식 한도는 IP당 초당 10회이며 호가 그룹과 공유됩니다. 새로운 endpoint,
자격 증명 접근 또는 주문 권한을 추가하지 않았습니다.

HTTP Date의 의미와 초 단위 형식은
[RFC 9110 §6.6.1](https://www.rfc-editor.org/rfc/rfc9110.html#name-date) 및
[§5.6.7](https://www.rfc-editor.org/rfc/rfc9110.html#name-date-time-formats)에 따릅니다.

`E1UpbitQuoteSource.read_receipt()`는 아직 호가로 승인되지 않은 `OrderbookRead`를
반환합니다. 기존 `read()`는 동일 요청 결과에 기존 `parse_orderbook`를 그대로
적용합니다. 진단 모듈은 이 구분을 이용해 미래 timestamp를 버리지 않고 조사하며
실행 경로에 반환하지 않습니다.

`execution_accounts/quotes.py`는 소유자 코드 서명과 연구 capture-source digest의
범위에 있습니다. 병합 뒤 실제 실행용 코드 승인을 갱신하고 **새 연구를 고정하기
전에** 이 버전을 선택해야 합니다. 이미 공개한 commitment나 과거 캡처를 새
코드에 맞춰 고치지 않습니다. 이 진단은 `STUCK_AT_START`, 보유 포지션 연속
증거, instrument rules 갱신 또는 적격 전략 부재를 해결하지 않습니다.

검사는 `tests/launch_quote_diagnostics.py`와 기존 `tests/accounts_quotes.py`의
합성 응답으로 수행합니다. 법률·세무·투자 조언이 아니며 작성자는 면허를 가진
자문가가 아닙니다.
