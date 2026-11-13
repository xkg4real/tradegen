# 용량 보존 실험 원본

이 디렉터리는 실행한 scratch 파일을 바이트 그대로 보존한다. 운영 모듈이나 새로운 history 형식 구현이 아니다. `prototype-results.json`의 15 PASS는 단일 writer 메모리 head/journal 모델에 대한 결과다.

실행 환경: Python 3.13, 기존 TRADEGEN venv, source a54a390, checkout `/workspace/tradegen-universe-pr4d-1113`. `verify.py`가 19 KEYLESS·임시 홈을 설정한다. `prototype.py`는 원래 용량 probe에서 정상 행을 포착한 뒤 저장 모델을 검사한다. `pr4d-size-probe.py` 전체를 실행하는 것이 아니라 그 파일의 합성 `ManyDustSource` 클래스만 AST로 재사용한다.

동일 환경에서 실행한 명령: `/workspace/.venvs/tradegen/bin/python -u /workspace/tradegen-session/capacity-preserve-1113/prototype.py`.

파일의 원래 위치:

- prototype.py, prototype-results.json: `/workspace/tradegen-session/capacity-preserve-1113/`
- verify.py, review-capacity-actual.py: `/workspace/tradegen-session/universe-pr4d-1113/`
- pr4d-size-probe.py: `/workspace/tradegen-session/universe-1113/`

다른 환경에서 재현할 때는 명시적 checkout/격리 경로를 먼저 준비하고 경로 변경을 기록한다. 운영 홈·키·네트워크 API를 사용하지 않는다. prototype의16MiB는 실험 상한이며 운영 정책값이 아니다. 실제 head CAS, Windows 내구성, chooser 통합, 실계좌 사례는 검사하지 않았다.
