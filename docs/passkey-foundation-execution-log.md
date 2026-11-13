# 패스키 검증 기반 모듈 — 실행기록

2026-11-13. 완료 범위는 `universe-pr5/passkey-verification-foundation`이다. 독립 환경에서 실제 등록·assertion 암호검증과 순수 계약 검사 **25 PASS / 0 FAIL / 0 NOT_RUN, 0.153초**를 확인했다. 전체 archive 승인 기능, 승인 원장, 운영 RP 또는 실거래 기능을 완료한 보고가 아니다.

검증 label은 `passkey-foundation1`, source commit은 `b0cb8b34a9cc2d12c421b5f308f98680091b47ac`이다. 검사 전후 Python/YAML과 독립 broker requirements를 묶은 fingerprint는 `2956cb10286869bc3cad5642458b59f9364782d72fffc4140f978451bd9c6422`로 동일했다. 이후 PR57 문서 병합을 포함한 작업 HEAD는 `4974ec3d7427cc1e398b62df5ff1f73521143485`다. 변경은 [PR #59](https://github.com/xkg4real/tradegen/pull/59)에서 추적한다. 최종 delivery commit과 실제 main 병합·tree 대조 결과는 외부 인수인계 기록에 남긴다.

## 실제 변경

새 `tools/approval_broker/contract.py`는 불변 등록 요청과 ENROLL_PROOF 표시 본문·요청·challenge, 원문 응답, credential material 및 assertion 기대값을 정의한다. 입력의 exact 타입·필드, 중복 키, 크기·깊이·노드, 시간과 domain을 제한한다. 원문 clientDataJSON과 authenticator 응답은 별도 증거 bytes로 유지한다. 공개 credential ID의 SHA와 전체 material의 domain digest를 구분한다.

새 `webauthn_verify.py`는 구조 admission 뒤 실제 fido2 등록·서명 검증을 호출한다. 지원 범위는 ES256/EC2/P-256 및 none attestation이다. exact HTTPS origin/RP ID/challenge, UP/UV, userHandle, BE/BS, counter와 만료를 확인한다. browser가 돌려준 라이브러리 state를 기대값으로 받지 않는다.

none 등록은 attestation 서명이 없으므로 키 보유·제조사·특정 기기 인증으로 취급하지 않는다. 등록에서 얻은 후보 공개키의 유효성을 실제 cryptography에서 검사하며, 별도 실제 ENROLL_PROOF assertion이 키 보유를 검증한다. 검증 반환은 사실 데이터이고 `approval_applied`/`current_use_eligible`는 false다. pure context 또는 검증 결과 객체의 생성·복사는 승인 발급이 아니다.

동기화 패스키의 old=0/new=0 counter는 그대로 보존하고 anomaly=false로 둔다. 둘 중 양수가 있고 비증가하면 anomaly=true이며, BE=true에서는 이 사실만으로 거절하지 않는다. BE=false에서는 증가 조건을 적용한다. 반복 assertion 검증은 일회성 소비를 뜻하지 않는다. 향후 실제 원장의 원자적 replay 방지가 별도로 필요하다.

독립 `requirements.txt`, `requirements-dev.txt`, `constraints.txt`와 문서만 추가했으며 앱의 기존 의존성 파일·owner 서명/활성화 경로는 변경하지 않았다. 단독 테스트 실행기는 `tests/passkey_acceptance.py`다. 사용 방법과 공개 설치 artifact hashes는 [패키지 README](../tools/approval_broker/README.md)에 있다.

## 실제 검증 근거

| 검사 | 건수 | 결과 |
|---|---:|---|
| `launch_passkey_contract` | 9 | 9 PASS |
| `launch_passkey_webauthn` | 16 | 16 PASS |
| 단독 실행 합계 | 25 | 25 PASS / 0 FAIL / 0 NOT_RUN |

실제 일회용 P-256 키와 cryptography 서명, 실제 fido2 검증을 사용했다. 다른 키/변조된 서명, 잘못된 RP hash·origin·challenge·userHandle, UP/UV 및 BE/BS 위반, non-BE counter 회귀, 중복/뒤에 붙은 JSON·CBOR, 미지원 COSE·확장, 만료와 미래 요청을 거절했다. admission 이전에 라이브러리로 도달하지 않는지 확인하는 trap 외에 긍정 암호검증을 가짜 verifier로 대체하지 않았다.

검사 환경은 새 Linux Cloud CPython 3.13.16 가상환경이며 `fido2 2.2.1`, `cryptography 49.0.0`, `cffi 2.0.0`, `pycparser 3.0`을 별도로 설치했다. 앱의 공유 가상환경에는 추가 설치하지 않았다. 설치 보고서 `dependency-install-report.json`과 `passkey-foundation1-{summary,rows}.json`이 실제 근거다. 설치 RECORD hash도 summary에 포함한다. 설치 단계의 공개 패키지 조회와 검사 중 네트워크 금지를 구분한다.

19개 KEYLESS 이름을 적용했고 검사 중 네트워크 연결을 거절했다. 테스트 import/discovery 전부터 종료까지 실제 홈의 **메타데이터만** 비교했으며 변화가 없었다. 실제 홈 내용·owner 키·서명 암호·계좌·거래소 API는 사용하지 않았다. source fingerprint와 기존 QA 파일도 전후 동일했다. 이 결과는 실제 운영 환경이나 native iPhone/Windows 검증을 뜻하지 않는다.

## 검토와 환경 준비를 실행 실패와 구분

런타임 전 독립 읽기 검토에서 `CoseKey.parse`가 EC 점 유효성을 확인하지 않고 none 등록도 서명 검증을 생략한다는 결함을 발견했다. cryptography의 실제 `EllipticCurvePublicNumbers(...).public_key()` 검증을 추가하고, 구조는 맞지만 곡선 밖인 `(0,0)` 및 필드 범위 밖 좌표를 거절하는 회귀를 넣었다. 이는 실행 전 수정한 소스 결함이며 위 25개 실행의 FAIL이 아니다.

초기 시스템 Python 3.13의 ensurepip 부재로 가상환경 생성이 실패해 기존 로컬 CPython 3.13.16으로 별도 환경을 준비했다. 기본 프록시 연결도 OS 권한 제한으로 거절됐고, 허용된 프록시 설치 경로로 의존성 설치를 완료했다. 이는 테스트 실행 전에 해결한 환경 문제이며 암호검증 코드 실패나 통과한 테스트 수에 포함하지 않는다. 실제 설치 보고서를 확보한 뒤 동결된 소스로 위 단독 실행을 수행했다.

추가 앱 호환 검사 `passkey-app-compat1`은 종료 코드 0으로 확정됐다. HEAD `4974ec3d7427cc1e398b62df5ff1f73521143485`, source fingerprint `4489156607f87ddd4c9e3f6a382df812a31774e3080b7bc60345e5ba273244df`, **61 PASS / 0 FAIL / 0 NOT_RUN, 21.872초**다. source와 실제 홈 메타데이터, 기존 QA 파일의 불변을 확인했다. 단독 검증 fingerprint는 broker 의존성 `.txt`까지 포함하고 앱 호환 fingerprint는 기존 Python/YAML 범위이므로 두 hash의 차이를 소스 변경으로 해석하지 않는다.

25개 단독 검증과 61개 기존 호환 검사는 중복 없는 총 86개 검사지만 **서로 다른 환경에서 수행한 두 실행**이다. 한 번의 86개 프로세스 실행이나 저장소 전체 검사로 표시하지 않는다. 최종 전달·병합 정보는 PR #59와 외부 인수인계 기록을 따른다.

## 남은 경계

독립 owner grant 발급·설치, credential 활성화/폐기/복구 원장, challenge 일회성 소비, 전체 archive 요청·manifest 의미 확인, 실제 HTTPS RP/브라우저/IPC, Telegram 알림, 현재 사용 소비자와 감사 원장은 미구현이다. 상위 서비스가 전달할 typed 기대값은 이번 순수 모듈에서 실제 서비스 소유 상태로 인증되지 않는다. ARCHIVE_CONFIRM이라는 context 이름은 원문 archive 검증이나 적용 승인을 뜻하지 않는다.

fido2의 INFO 로그에는 credential ID가 포함될 수 있으므로 운영 서비스가 별도 로그 통제를 해야 한다. 패스키를 Ed25519 owner 서명으로 변환하지 않으며, 서버에 소유자 개인 서명키나 주문키를 맡기지 않는다. 특정 iPhone의 Face ID 사용, 네이티브 ACL·보호된 프로세스 경계·실제 RP domain 및 운영 배포는 아직 검증하지 않았다. 코드·규칙·연구 선발·거래 활성화 scope를 이 결과로 승인하지 않는다.

이 단위에서 기존 손실 하한이나 위험정책, 거래 진입·보유·매도 동작을 변경하지 않았다. 후속 작업은 독립 grant·ledger·RP·소비 경계를 실제로 연결해야 하며, 이 선행 모듈의 완료를 전체 사용자 승인 흐름의 완료로 재사용하지 않는다.

법률, 세무, 투자 조언이 아니며 면허를 가진 자문가가 아니다
