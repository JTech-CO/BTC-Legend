# BTC-Legend

**기본 언어는 [English](README.md)입니다.**

제공자가 **워뇨띠**의 기록으로 제시한 `aoa` 계정의 체결·지갑 CSV를 분석하는 연구 프로젝트입니다. 연구 대상 기간은 **2018.03.01–2021.12.31**이며, 실제 첫 기록은 **2018.03.05**입니다. 계정 귀속, 원본의 진위, 다른 계좌를 포함한 전체성은 별도로 인증하지 않았습니다.

현재 작업은 금융·암호화폐 시장 관점의 분석입니다. 실시간 매매, 특정 시점의 매수·매도 권고, 거래소 계정 연결은 구현하지 않았습니다. 향후 시뮬레이션이나 매매 프로그램 개발 자체를 금지하는 프로젝트는 아닙니다. 파일은 로컬에서 수정하며 커밋과 공개는 소유자가 진행합니다.

| 자료 | 링크 |
| --- | --- |
| 우선순위 9-10: 통합 백서·연구 탐색기 | [한국어 백서 v0.7](reports/whitepaper.ko.md) · [English](reports/whitepaper.en.md) |
| 재현·로컬 탐색기·검토 패키지 실행 | [한국어 실행 안내](research/reproduction.ko.md) · [English](research/reproduction.en.md) |
| 데이터 단위·시각·근거 수준 | [한국어 데이터 사전](research/data-dictionary.ko.md) · [English](research/data-dictionary.en.md) |
| 핵심 발견과 당시·현재 시장 비교 | [한국어 연구 보고서](reports/research.ko.md) · [English](reports/research.en.md) |
| 후속 회계 차이 추적 | [한국어 v0.2](reports/accounting-audit.ko.md) · [English v0.2](reports/accounting-audit.en.md) |
| 큰 이익·손실·청산 사건 | [한국어 v0.3](reports/event-study.ko.md) · [English v0.3](reports/event-study.en.md) |
| 전체 포트폴리오 위험 복원 | [한국어 v0.4](reports/portfolio-risk.ko.md) · [English v0.4](reports/portfolio-risk.en.md) |
| 과거 마크가격·장중 노출·입출금 조정 성과 | [한국어 v0.5](reports/marks-intraday-returns.ko.md) · [English v0.5](reports/marks-intraday-returns.en.md) |
| 우선순위 4: 매매 행동의 변화 | [한국어 v0.5](reports/behavior-changes.ko.md) · [English v0.5](reports/behavior-changes.en.md) |
| 우선순위 5-8: 행동 설명·성과 기여·민감도·손실 후 반응 | [한국어 v0.6](reports/behavior-attribution-robustness.ko.md) · [English v0.6](reports/behavior-attribution-robustness.en.md) |
| 단위·회계·데이터 품질·재현 방법 | [한국어 방법론](research/methodology.ko.md) · [English](research/methodology.en.md) |
| 외부 근거 | [출처 목록](research/sources.md) |
| 수치 원본 | [계정 집계](results/summary.json) · [시장 집계](results/market_summary.json) |

## 로컬 연구 탐색기와 통합 재현

v0.7 탐색기는 날짜·계약별 포지션, 부모 주문, 원본 체결, 지갑 기장, USD/USDT 기준가격, 표본 마크가격과 불확실성을 연결합니다. EN이 기본이며 KR로 전환할 수 있습니다. [실행 안내](research/reproduction.ko.md)에 따라 원본과 파생표를 준비한 뒤 실행합니다.

```text
python scripts/reproduce.py --mode verify
python scripts/build_explorer.py
python scripts/serve_explorer.py
```

브라우저에서 `http://127.0.0.1:8765`를 엽니다. 약 0.88 GB의 로컬 SQLite 색인은 Git에서 제외합니다. `verify`는 저장된 결과를 검증하며, `python scripts/reproduce.py --mode rebuild --explorer`는 잠긴 입력에서 전체 파이프라인을 재계산합니다. 이번 버전은 단위 테스트 44개, 기존 연구 검증 5종, 탐색기 검증 34개를 통과했습니다. 금융 분석 전체를 원본부터 새로 재계산한 실행과는 구분합니다. 원본과 색인을 제외한 로컬 검토 패키지 구성도 실행 안내에 기록했으며, 배포 권한을 부여하는 것은 아닙니다.

## 주요 연구 결과

핵심 결과는 **체결 1,439,207건**, **식별 가능한 주문 23,416개**, **주문 ID가 0인 청산 표시 체결 28건**입니다. 청산 체결은 주문 복원에서 분리하지만 손익·포지션 집계에서는 유지합니다. 계좌 전체 순실현손익은 **3,537.32369404 BTC**이고, 그중 XBTUSD는 **2,007.08464645 BTC(약 56.74%)**입니다.

사건 전수 연구에서 청산 표시 체결 전체는 **59건**으로 확인됐습니다. 기존 28건 외에 정상 주문 ID를 공유하는 ETHUSD 부분 축소 체결 31건이 있습니다. 정확한 시각·주문 기준 29개 묶음이며 독립 마진콜 횟수로 확정하지 않습니다. 최대 이익 기장일 **+275.53795475 BTC**는 XBTUSD·XBTH20, 최대 손실일 **−281.83947272 BTC**는 XBTUSD·ETHUSD의 합산 결과입니다. 펀딩 포함 보유 구간, 시간별 경로와 청산 근거는 [별도 v0.3 결과](results/event_study/summary.json)에 저장했습니다.

완료된 총 입금 **14.48925714 BTC**와 실현손익에서 출금 **2,814.54321713 BTC**를 차감하면 마지막 잔액 **737.26973405 BTC**와 정확히 일치합니다. 하지만 마지막 XBTUSD 포지션이 열려 있으므로 이를 최종 평가자산이나 투자수익률로 해석하지 않습니다.

![시장과 지갑의 변화](reports/figures/market_wallet.png)

재현 명령은 [영문 README](README.md#reproduce-locally)에 있습니다. 저장된 시장 자료로 오프라인 재실행할 수 있습니다. 원본은 보존했으며, 현재 비교는 **2026.09.22 UTC 일봉 종료 시점**을 기준으로 합니다. 데이터 공개 권한이나 라이선스는 임의로 확정하지 않았습니다.

후속 회계 연구에서는 기존 XBTUSD 총차이 **0.02745234 BTC**를 정산 범위 밖 펀딩 **0.01958048 BTC**와 원가 배분 차이 **0.00787186 BTC**로 설명했습니다. 개선 모델의 총차이는 0이며, 일별 12일에는 1~2사토시 차이가 남습니다. 지갑 차이 154일 중 152일은 표시 정밀도로 설명되고, 2일은 한 출금의 날짜·처리 순서 확인이 필요합니다. 기존 조건부 구간 통계는 비교용으로 유지하며 최신 회계 결과는 별도 [집계](results/accounting_audit/summary.json)에 있습니다.

v0.4에서는 **46개 계약과 만기 정산 8건**을 복원했습니다. 모든 계약의 총실현손익과 원장이 각각 일치하고, 펀딩 수량 **5,368건**도 맞습니다. BTC 담보·USD/USDT 환산을 포함한 일별 기준가격 평가와 여덟 가지 고정 충격을 [포트폴리오 결과](results/portfolio_risk/summary.json)에 저장했습니다. 실제 마크가격 NAV나 레버리지가 아닌 조건부 시나리오이며, 현재 재사용된 USDT 심볼 다섯 개에는 당시 명세를 적용했습니다.

[v0.5 확장 연구](reports/marks-intraday-returns.ko.md)는 월초 33일의 과거 마크·지수 파일 54개를 확보하고 장중 수량과 입출금 시각 민감도를 분석했습니다. 수익률 시나리오는 현물 기준 평가를 유지하며 전체 기간의 실제 NAV 수익률을 확정하지 않습니다. [매매 행동 연구](reports/behavior-changes.ko.md)에서는 XBTUSD 주문 수 감소, 절대 주문 규모·완료 보유 시간 증가와 후기 알트 기여 확대를 확인했습니다. 분할 체결을 독립 판단으로 세지 않고 부모 주문을 비교합니다. 새 결과와 검증은 `results/extended_research/`에 있습니다.

제공자 원본이 없는 체크아웃에서는 `research_events.py` 이후 `fetch_historical_marks.py`로 공개 표본을 받은 다음 분석합니다. 로컬에 표본이 있으면 오프라인 재현이 가능합니다. 제공자 원본 압축파일과 대형 사건 캐시는 Git 제외 대상으로 두고 수집 기록·파생 연구표를 남겼습니다.

[v0.6 연구](reports/behavior-attribution-robustness.ko.md)는 우선순위 5-8을 다룹니다. 자본·시장을 조정하면 독립된 전략 변화라는 단순 해석이 약해지며, 2018년과 2021년의 자본 범위는 겹치지 않습니다. 가산 회계 분해로 계약 손익·수수료·펀딩·미실현손익·BTC/USD 환산을 구분했습니다. 마크가격의 간격·최신성 9개 조합과 손실 정의 변경으로 결론의 민감도를 확인했으며, 손실 후 위험 축소는 보편적인 패턴이 아니었습니다. 재현 결과는 `results/robustness_research/`에 있고, [검증 32개](results/robustness_research/validation.json)와 프로젝트 전체 단위 테스트 38개가 통과했습니다. 계좌 원본과 이전 시장 스냅샷은 그대로 보존했습니다.
