# 독립 패스키 검증 기반 모듈

이 패키지는 실제 WebAuthn 등록 응답과 ES256 assertion을 검증하는 **선행 모듈**이다. 독립 owner grant, 승인 원장, 일회성 challenge 소비, HTTPS 승인 화면, Telegram 연동과 앱의 승인 적용 경로는 아직 없다. 이 모듈을 설치하거나 검사를 통과해도 코드·규칙·연구 선발·거래 활성화 승인이 만들어지지 않는다.

완료 단위는 `universe-pr5/passkey-verification-foundation`이다. 전체 패스키 archive 승인 기능의 완료 ID가 아니다. 실행 근거는 [검증 실행기록](../../docs/passkey-foundation-execution-log.md)에 남긴다.

## 구현된 계약

- `contract.py`: 정확한 필드와 크기를 제한하는 불변 등록 요청, `ENROLL_PROOF` 요청·표시 본문·challenge, 원문 응답, credential material 및 assertion 기대값. 별도 domain에서 요청과 원문 증거를 해시한다.
- `webauthn_verify.py`: `fido2==2.2.1`의 실제 등록·서명 검증과 `cryptography==49.0.0`의 실제 P-256 공개키 검증. 중복 JSON/CBOR 키, 뒤에 붙은 데이터, 미지원 알고리즘·확장, origin/RP ID/challenge/UP/UV/userHandle 및 BE/BS/counter 조건을 검사한다.
- 등록은 ES256/EC2/P-256, `attestation=none`만 받는다. `none`에는 attestation 서명이 없으므로 등록 응답은 **후보 키 재료**다. 별도 `ENROLL_PROOF` assertion의 실제 서명 검증이 키 보유를 확인한다. 제조사·특정 iPhone·생체인증 방식의 증명은 아니다.
- `VerifiedRegistration`과 `VerifiedAssertion`은 생성·복사 가능한 사실 데이터다. `approval_applied`와 `current_use_eligible`는 항상 false이며 기존 앱이 승인 token으로 받지 않는다. `AssertionContext`와 `now` 역시 전달된 기대값이지 실제 서비스·시계·원장이 확인됐다는 증거가 아니다.

BE=true인 동기화 패스키는 비증가 counter만으로 거절하지 않는다. old=0/new=0은 anomaly=false이며, 둘 중 양수가 있고 비증가하면 anomaly=true다. BE=false에서는 양수 counter가 있으면 증가해야 한다. 같은 유효 응답을 순수 검증기에 다시 전달하면 다시 검증될 수 있다. **이 검증기는 재사용 방지 원장을 대신하지 않는다.**

## 독립 개발 환경에서 실행

아래는 별도 Linux Cloud 개발 환경용 예다. 앱의 공유 가상환경이나 사용자 PC 환경에 추가 설치하지 않는다. 저장소 루트에서 실행하며, 설치와 오프라인 검사를 구분한다.

```bash
python3.13 -m venv /tmp/tradegen-passkey-check
/tmp/tradegen-passkey-check/bin/python -m pip install \
  -r tools/approval_broker/requirements.txt \
  -r tools/approval_broker/requirements-dev.txt \
  -c tools/approval_broker/constraints.txt
/tmp/tradegen-passkey-check/bin/python -m tests.passkey_acceptance \
  --results /tmp/tradegen-passkey-results.json
```

이 독립 실행기는 앱의 전체 acceptance registry를 import하지 않는다. 검사 import 전에 19개 KEYLESS 이름을 `<unset>`으로 설정하고, 검사 중 네트워크 연결을 거절하며, 실제 홈의 파일 내용 없이 메타데이터만 전후 비교한다. 앱의 기존 QA 파일을 검사 결과로 덮어쓰지 않는다. 실제 운영 키나 계좌 데이터는 필요하지 않다.

2026-11-13 Linux CPython 3.13.16 독립 환경에서 계약 9개와 실제 암호검증 16개, **총 25 PASS / 0 FAIL / 0 NOT_RUN**을 확인했다. 일회용 합성 ES256 키로 실제 서명하고 실제 fido2 검증기를 호출했다. 실제 iPhone·Safari·Face ID·Windows ACL·운영 HTTPS 서비스 검증 결과는 아니다.

## 의존성과 로그

직접·전이 의존성은 이 디렉터리의 독립 requirements/constraints에서 고정한다. 공개 패키지 설치 보고서에서 확인한 **이번 Linux 설치 artifact**의 SHA-256은 다음과 같다. 다른 플랫폼의 wheel hash나 전체 운영 배포 승인으로 일반화하지 않는다.

| 패키지 | 버전 | 설치 artifact SHA-256 |
|---|---|---|
| fido2 | 2.2.1 | `ed397da981b9ab133da6ead7309e41f924b566b749956129efe286fae097749f` |
| cryptography | 49.0.0 | `cbc77da8c523d5abd028635ba850a6966fcee2c82e2bf65a41d1d8afe0f98be9` |
| cffi | 2.0.0 | `c8d3b5532fc71b7a77c09192b4a5a200ea992702734a2e9279a37f2478236f26` |
| pycparser | 3.0 | `b727414169a36b7d524c1c3e31839a521725078d7b2ff038656844266160a992` |

근거는 개발 세션의 `dependency-install-report.json`이다. 문서에는 공개 패키지 정보만 옮겼으며 로컬 owner 자료나 키는 포함하지 않는다. 검증 중 설치된 각 배포의 RECORD hash도 별도 실행 근거에 기록했다. requirements는 버전을 고정하지만 pip의 `--require-hashes` 배포 lock을 구현한 것은 아니다.

`fido2.server`는 INFO 로그에서 credential ID를 기록한다. 후속 broker/RP 서비스는 이 라이브러리 로그를 명시적으로 차단하거나 비공개 로그 정책으로 통제해야 한다. 이 순수 패키지는 전역 logging 설정을 바꾸지 않는다.

## 다음 연결에서 필요한 것

실제 서비스가 보관한 요청·credential·grant에서 기대값을 재구성하고, 동일 challenge의 적용을 원자적으로 한 번만 확정하는 원장과 폐기·복구 절차가 필요하다. 독립 root와 서비스 간 실제 신뢰 경계, 표시한 대상과 적용 대상의 binding, 전체 archive manifest 의미 검사 및 현재 사용 소비자는 별도 구현이다. 별도 가상환경이나 동일 프로세스의 실제 Python 클래스만으로 악성 앱과의 격리가 성립하지 않는다.

패스키 서명을 기존 Ed25519 owner 서명으로 변환하거나 owner 개인키를 서버에 맡기지 않는다. 이 단위는 기존 owner/코드/규칙/활성화 서명 경로를 변경하지 않는다.

법률, 세무, 투자 조언이 아니며 면허를 가진 자문가가 아니다
