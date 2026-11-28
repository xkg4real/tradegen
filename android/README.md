# TRADEGEN 승인 알림 · Android

Android Chrome에서 운영 승인 사이트의 `/android/`를 열고 메뉴의 **앱 설치** 또는 **홈 화면에 추가**를 선택한다. 이 버전은 홈 화면에서 실행하는 웹 앱(PWA)이며 APK 설치가 필요 없다. 알림을 누르면 같은 HTTPS 사이트의 `/approvals/`가 열린다. 해당 승인 서버에서 대상·버전·범위·유효기간을 확인하고 Android의 패스키 인증을 완료한다.

## 운영자 준비

이 저장소의 `android/approval-inbox/`는 승인 서비스 준비 상태를 안내하는 정적 화면이다. 운영 승인 서버가 아직 없으면 [승인함 배포 지침](approval-inbox/README.md)에 따라 이 안내 화면을 `/approvals/`에 HTTP 503 및 `Cache-Control: no-store`로 제공한다. Android에서 실승인을 완료하려면 운영자가 이후 이 경로에 인증된 승인함을 배포하고 기기 패스키를 등록해야 한다.

1. 소유자가 정한 HTTPS 승인 도메인에 `android/web/`의 내용을 `/android/` 경로로 배포한다. 승인함은 독립 서버가 같은 origin의 **`/approvals/`** 에 제공해야 한다. TRADEGEN 주문 기능이 없는 별도 승인 도메인을 쓰고, 이 경로에 외부 사이트로 향하는 리디렉션을 설정하지 않는다. 서비스 워커 범위는 `/android/`로 유지한다. JS·MJS 파일은 JavaScript MIME으로, `manifest.webmanifest`는 `application/manifest+json`으로 제공한다.
2. [알림 전송기 설정](../docs/notification-relay.md)에 따라 VAPID 키 쌍을 만들고 **공개** 설정 JSON만 `/android/push-config.json`으로 배포한다. 형식은 `{"applicationServerKey":"<65바이트 비압축 P-256 공개키의 Base64url>"}`다. 비공개 키와 Telegram 토큰은 발송 측에 보관한다. 키를 새로 만들 때 기존 기기는 등록을 해제하고 새 등록 파일을 전달한다.
3. 개인 Android 기기에서 위 주소를 열고 **푸시 알림 등록**을 눌러 Android·Chrome 알림을 허용한다. **비공개 등록 파일 저장**으로 `tradegen-android-subscription.json`을 내려받는다. `endpoint`, `expirationTime`, `keys.p256dh`, `keys.auth`가 담긴 개인별 파일이다. 운영자에게 비공개로 인계해 전송기에 등록하고 기기 다운로드 사본을 정리한다. 공개 저장소나 정적 사이트에 올리지 않는다. 운영자에 의한 등록이 완료되어야 서버 발송을 할 수 있다. 현재 대상은 Android Chrome과 Google FCM Web Push다.
4. **기기 알림 테스트**는 이 기기에서만 만든 알림을 표시한다. 이 버튼을 누르면 먼저 Android 알림 권한을 요청할 수 있다. 테스트 알림을 누르면 앱 첫 화면이 열린다. 실제 전송 확인은 전송기의 운영 테스트와 Android 기기에서 별도로 한다. 서버 발송 성공은 기기 수신이나 열람을 확정하지 않는다.

## HTTPS 서버에 올릴 파일

배포 묶음의 `site/`만 전용 HTTPS 사이트의 문서 루트에 둔다. 저장소에서 직접 준비할 때는 `android/web/`의 공개 파일을 문서 루트의 `android/`로 복사하고 `android/approval-inbox/index.html`을 문서 루트의 `approval-offline.html`로 복사한다. 배포 전 공개 설정은 발송기가 생성한 `push-config.json` 한 파일이다. 새 도메인은 DNS와 TLS 인증서를 먼저 준비한다.

Nginx에서는 전용 HTTPS `server` 블록에 이 루트를 지정하고 [경로 설정 예시](deploy/nginx-locations.conf)를 포함한다. `/android/`에는 설치 화면, `/approvals/`에는 승인 서비스 준비 전까지 HTTP 503과 `Cache-Control: no-store`를 제공한다. 일반 알림이 승인함을 열 때도 같은 경로를 사용한다. 운영자가 승인 서비스를 배포할 때 `/approvals/` 설정을 교체한다.

## 승인함 열기와 기기 해제

- 서버 알림을 누르거나 첫 화면의 **승인함 열기**를 선택하면 `/approvals/`가 열린다. 알림 내용에 담긴 URL·요청 ID는 사용하지 않는다. 화면을 연 행위로 승인 요청이나 주문을 만들지 않는다.
- 잠금 화면에는 일반 안내만 표시한다. 최신 알림 내용·요청 상태는 서버에서 본인 인증 후 확인한다. 생체정보·기기 암호 처리는 패스키를 지원하는 Android와 브라우저에 맡긴다. 적절한 인증 방식은 사용하는 Android 기기의 설정에 따른다.
- 기기 분실 시 운영자가 해당 등록 파일을 전송기 설정에서 제거하고, 승인 서버에서도 해당 기기에 필요한 복구·폐기 절차를 수행한다. 기기가 있으면 **이 기기 등록 해제**로 브라우저 구독도 취소한다. 알림 수신과 승인용 패스키의 등록·폐기는 각각 관리한다.
- 알림이 뜨지 않으면 Android 시스템·Chrome 사이트 알림 설정, 절전 설정, 현재 기기의 등록 여부를 확인한다. Android 등록 정보가 바뀌면 새 등록 파일을 다시 전달한다. 알림이 늦은 경우에도 서버에서 현재 요청의 만료·중복 사용·권한을 검사한다.

## 검증 범위

`node android/tests/android_companion.test.mjs`는 표준 Node만으로 공개키 대조, 등록 파일 형식, 전송 대상 제한, 신뢰하지 않는 payload의 무시 및 고정 승인함 연결, 기기 테스트 알림의 복귀 경로, 합성 브라우저 등록·키 변경·구독 해제 절차를 검증한다. 출시 전에는 운영 HTTPS 도메인, 실제 Android의 Chrome·홈 화면 모드, Google Web Push 수신, 화면 잠금·백그라운드 수신, 패스키 승인·거절·만료 처리까지 확인한다. 배포된 승인 서버·실제 기기 수신·패스키 완료는 소스 검사로 확인할 수 없다.
