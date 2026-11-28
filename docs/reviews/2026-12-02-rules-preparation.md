# 12월 2일 규칙 재검토 준비표

2026년 11월 28일 KST에 PR #79의 `cd70bdd`에서 점검했다. 저장소의 **47행 중 25행은 12월 2일**, 22행은 12월 11일이 검토 기한이다. OKX 현물의 추가 노출은 12월 3일 KST부터 `auto_off`에 걸린다. 계좌에 실제로 효력이 있는 버전은 소유자가 서명한 표의 해시로 확인한다. 12월 2일 원문 재검토와 소유자 서명은 남아 있다. [현행 규칙 초안](../../core/compliance/kr_rules.yaml) · [직전 행별 검토 및 미결 증거](<../../research_notes/Korean resident trading venue legality/review_2026-11-10.md>)

## 재검토 대상

아래 표에서 행 이름은 모두 `KR-`로 시작한다. 각 행의 `sources`, `research`, `affected_by`와 11월 10일 기록을 함께 확인하고 원문 개정·시행일, 열람일, 변화 여부를 남긴다. 아래 링크는 검토자가 대조할 기존 출처다.

| 기한 | 행 또는 파일 | 확인할 내용 |
|---|---|---|
| 12/2 · 3행 | KIS-CRYPTO-FUT-ETF, KIS-CRYPTO-SPOT-ETP, KIS-CRYPTO-DERIV | 중개 가능 상품과 KIS 실제 상품 제공 여부를 따로 확인한다. 현물 ETF, 선물 ETF 및 개별 파생상품을 구분한다. [금융위 안내](https://www.fsc.go.kr/no010101/81466) · [KIS 상품 공지](https://securities.koreainvestment.com/main/customer/notice/Notice.jsp?cmd=TF04ga000002&num=45495) |
| 12/2 · 5행 | DOMESTIC-SPOT, GOPAX, DOMESTIC-LENDING, DOMESTIC-CRYPTO-DERIV, TRANSFER-OUT | FIU의 최신 신고 사업자와 서비스명, 고팍스 운영 공지, 대여·파생·해외 이전 관련 고시와 시행일을 대조한다. [FIU 현황](https://www.kofiu.go.kr/kor/notification/notice_view.do?ntcnYardOrdrNo=194&seCd=0007) · [대여 가이드](https://www.fsc.go.kr/no010101/85247) · [FIU 고시](https://www.kofiu.go.kr/kor/law/announce_view.do?lawordInfoOrdrNo=90&seCd=001) |
| 12/2 · 4행 | OKX-SPOT, OKX-WITHDRAW, OKX-DERIV, OKX-P2P | 12/3 국경 간 이전 제도의 최종 시행령·고시 원문과 OKX 자체 서비스 범위를 확인한다. 현물 재승인·기한 변경에는 별도 근거가 필요하다. 출금·파생·P2P는 각각 해당 행으로 판단한다. [금융위](https://www.fsc.go.kr/no010101/88039) · [OKX 약관](https://www.okx.com/help/risk-compliance-disclosure) |
| 12/2 · 6행 | OFFSHORE-CEX, STATE-BLOCKED, BITMART, HYPERLIQUID, DEX, DRIFT | 미신고 사업자 명단, 차단 조치, 서비스 개명과 관할 제한을 다시 확인한다. 웹 약관 본문을 읽을 수 없는 행은 미확인으로 기록한다. [11월 기록과 행별 출처](<../../research_notes/Korean resident trading venue legality/review_2026-11-10.md>) |
| 12/2 · 7행 | CONDUCT-ROUTE, CONDUCT-OTHERS, CONDUCT-COPY, CONDUCT-FX, CONDUCT-SIGNALS, CONDUCT-PROMOTE, CONDUCT-MANIP | 판결의 적용 요건, 외국환거래법 개정과 발효일, 자본시장·가상자산 불공정거래 규정을 검토한다. 앱 자체 정책에 따른 차단은 판결이 직접 요구하는 의무와 구분한다. [대법원 2024도10710](https://law.go.kr/LSW/precInfoP.do?precSeq=600579) · [대법원 2024도12420](https://www.law.go.kr/LSW/precInfoP.do?precSeq=609527) |
| 12/11 · 22행 | 위 25행을 제외한 전체 규칙 | 국내외 전통 증권·파생상품, 예측시장, 스포츠, 기타 해외 중개, 관련 행위 규정. 11/28부터 14일 이내 경보에 포함된다. 1월 1일 가상자산 세제와 2월 18일 이전 경계도 다음 검토에 넘긴다. [행별 목록](../../core/compliance/kr_rules.yaml) |
| 날짜 필드 없음 | `instruments.yaml` 17개, `venues.yaml` 6개 | 상품 13개에 출처 미확인 표시가 있다. 거래소는 Korbit, OKX의 최상위 출처, Upbit·OKX 입금 네트워크 주석을 확인한다. KIS 호가단위·거래통화 및 업비트 최소 수량·수수료를 서명본과 비교한다. 계좌 스냅샷 파싱 성공만으로 거래 가능 시장·조건을 바꾸지 않는다. [상품 목록](../../core/compliance/instruments.yaml) · [거래소 목록](../../core/odds/venues.yaml) |

## 날짜 경계 재생

`python -m core.compliance.rules --check --today 2026-12-02`를 비어 있는 임시 `TRADEGEN_HOME`으로 실행한 결과는 **종료 코드 3**, 서명 기록 0건이었다. 실제 소유자 홈은 이 실행의 대상에서 제외했다. 이어 저장소 초안 세 개와 코드에 테스트용 서명을 적용한 임시 픽스처에서 CLI의 날짜만 바꿔 재생했다. 아래 기한 항목 수는 행·필드의 조합으로 세므로 OKX 현물 1행이 두 번 나타날 수 있다.

| 기준일(KST) | 종료 코드 | 14일 이내 · 당일 | 기한 경과 · 종료 |
|---|---:|---|---|
| 11/28, 12/2 | 1 | `review_by` 47, `auto_off` 1 | 0 |
| 12/3, 12/11 | 2 | `review_by` 22 | `review_by` 25, `auto_off` 1 |
| 12/12 | 2 | 0 | `review_by` 47, `auto_off` 1 |
| 2027/2/18 | 2 | 0 | 위 48건 및 `effective_until` 2건(TRANSFER-OUT, OKX-SPOT) |

`review_by`는 당일까지 유효하다. `auto_off`와 `effective_until`은 지정일 00:00 KST부터 적용된다. 검사 코드 2는 기한이 지난 항목이 있다는 뜻이다. 신규 노출과 보유분 청산·반환은 의도에 해당하는 규칙과 서명 상태에 따라 게이트가 따로 결정한다. [검사 구현](../../core/compliance/rules.py) · [거래 게이트](../../core/compliance/gate.py)

고정한 PR #79에서 `python -m tests.compliance_acceptance compliance_tables` 75/75, `python -m tests.compliance_acceptance compliance_cli` 37/37이 통과했다. 이는 코드·초안의 동작 확인이다. 12월 공식 문서 확인과 실제 소유자 상태 점검은 별도로 기록한다.

검사한 SHA-256은 규칙 `1699d1d67e1864a693e1097a47b86db40541cf45823f720701a1a41948420c01`, 상품 `50fa819f62707eb58e09135355b4f84160611ef4a8ad1af7345bb119b6f1431a`, 거래소 `5d966ef1639d5da23acfd58e2caff70d80233f401984d683faceebdb30b14aa9`이다. 재검토 후 변경이 필요한 행은 새 원문·시행일과 변경 사유를 적어 별도 검토·서명한다. 서명 전에는 승인 저장소에 있는 표가 계속 적용된다.

법률, 세무, 투자 조언이 아니며 면허를 가진 자문가가 아니다.
