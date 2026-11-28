# Android 승인함 연결

`index.html`은 운영 승인함이 준비되지 않았거나 중단되었을 때 보여 줄 정적 안내문이다. 승인 사이트의 프런트 서버가 `GET /approvals/`에 HTTP 503과 이 문서를 반환하도록 배포한다. 응답에는 `Cache-Control: no-store`, `Referrer-Policy: no-referrer`, `Content-Security-Policy: default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'`을 설정한다. 이 폴더에서 공개할 파일은 `index.html`뿐이다. 운영 승인함이 준비되면 해당 경로를 인증된 서비스에 연결한다. Windows 앱의 정상 작동 여부는 이 안내 화면에서 확인할 수 없다.

## 저장소에서 확인한 범위

- main `1fd8792`의 `tools/approval_broker`는 WebAuthn 등록 응답·assertion을 검증하는 Python 모듈이다. Windows의 기존 로컬 승인 도구는 별도 경로다.
- [PR #66의 엔진](https://github.com/xkg4real/TRADEGEN/blob/ae255f813a51ddc14b614a91831f2cb63eac5bb6/tools/approval_broker/engine.py)은 원장에 보관한 요청, challenge, 증거와 결과를 대조한다. [CLI](https://github.com/xkg4real/TRADEGEN/blob/ae255f813a51ddc14b614a91831f2cb63eac5bb6/tools/approval_broker/cli.py)는 파일 기반의 원장 준비·grant 설치·disable·상태 조회를 제공한다. 해당 커밋에는 Android나 브라우저가 호출할 HTTPS 승인함, 소유자 로그인 세션, 네트워크용 요청 조회·제출 인터페이스가 없다.
- 엔진의 승인 범위는 연구 자료 묶음의 동일성 확인(`archive_manifest_identity`)이고 별도 자격증명 수명 주기 처리가 있다. 연구 선발, 코드·규칙 승인, 보유·매도·거래 활성화에 쓰려면 각 범위의 검토된 승인 계약과 소비 경로가 필요하다.

## 실제 승인함을 배포할 때 연결할 사항

1. 독립 운영자가 검토한 HTTPS origin 및 RP ID에서 소유자 세션을 인증한다. `/approvals/` 접근 시 세션 소유자에 해당하는 실제 요청만 조회하게 한다. 운영 도메인에는 검토한 코드와 자산만 배포한다. 같은 origin의 JavaScript는 다른 경로의 응답도 읽을 수 있으므로 경로만으로 앱들을 격리할 수 없다. 거래 앱·사용자가 올린 콘텐츠는 origin을 분리한다. 승인 세션은 host 전용 `Secure`, `HttpOnly`, `SameSite=Strict` 쿠키로 제한하고 기존 알림 구독 자료·도메인 공용 쿠키로 승인자를 식별하지 않는다. 서버는 상태를 변경하는 요청의 origin과 CSRF 방어를 검증한다. Android 서비스 워커는 `/android/`에만 등록하고 승인함 응답의 캐시를 금지한다.
2. 승인 서버는 원장에서 사용자에게 허용된 요청을 읽어 [RequestRecord.display_bytes](https://github.com/xkg4real/TRADEGEN/blob/ae255f813a51ddc14b614a91831f2cb63eac5bb6/tools/approval_broker/authority_contract.py)의 대상·범위·자료 해시·요청 시각·challenge 만료·승인 만료를 표시한다. 화면에 표시한 대상과 인증에 쓰는 원본의 `request_sha256` 및 `display_sha256`을 일치시킨다. 푸시와 URL에는 요청 내용이나 인증 수단을 넣지 않는다.
3. 사용자가 내용을 확인하고 승인 동작을 선택하면 브라우저가 서버에 보관된 그 요청의 challenge와 RP 설정으로 `navigator.credentials.get`을 실행한다. 사용자 확인을 필수로 하고, 사용자 취소나 시간 초과는 미승인으로 종료한다. 서버는 실제 응답의 원본 바이트를 [Assertion 계약](https://github.com/xkg4real/TRADEGEN/blob/ae255f813a51ddc14b614a91831f2cb63eac5bb6/tools/approval_broker/contract.py)에 맞춰 검증기에 전달하고, 원장의 단일 사용·만료·대상 변경 검사를 거친다.
4. 인증된 서버의 원장 처리 결과를 확인한 뒤 사용자에게 해당 요청의 결과와 범위를 알린다. 제출 도중 통신이 끊어지면 결과 미확인으로 안내하고 재연결 후 조회한다. `EXACT_RETRY`는 과거 처리와 같은 응답의 재전송을 뜻한다. `ARCHIVE_CONFIRM`의 `APPLIED`는 해당 자료 묶음에만 적용된다. 현재 유효성 및 거래 권한은 독립적으로 확인한다.

운영팀은 승인 페이지의 실제 요청 열람, 다른 사용자 요청의 접근 거절, 인증 취소·만료·중복 처리, 연결 단절 후 결과 조회와 서비스 워커 범위를 Windows 브라우저 및 Android 실기기에서 확인한 후 정상 경로를 연다.
