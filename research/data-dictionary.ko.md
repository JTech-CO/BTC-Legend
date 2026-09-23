# 데이터 사전과 근거 등급

v0.7 · 기본 언어 [English](data-dictionary.en.md) · [정확한 CSV 스키마](schema-inventory.json) · [재현 절차](reproduction.ko.md)

기계 판독용 스키마 목록은 재생성 캐시를 포함한 모든 결과 CSV의 실제 헤더·바이트·SHA-256을 기록합니다. 구조 목록이며, 아래 의미 사전은 핵심 연구·탐색기 자료를 설명합니다. 특수 표의 추가 정의는 해당 버전 보고서와 생성 코드에 있습니다. 비어 있는 숫자 셀은 탐색기에서 null이며 0으로 해석하지 않습니다.

## 근거 등급

| 등급 | 의미 | 예시 | 입증하지 않는 것 |
| --- | --- | --- | --- |
| 제공 원본 관측 | 보존된 계좌 파일의 필드 | 체결 ID·수량·수수료·지갑 기장 | 외부 진위·미공개 계좌의 전체성 |
| 수집 시장 관측 | 시각이 명시된 저장 가격 | 월초 마크·지수·일별 기준가격 | 체결 가능한 유동성·미수집 구간의 가격 |
| 복원 | 가정을 공개한 결정적 변환 | 부호 있는 보유량·잔여 원가·원주문 | 의도·자료 이전 미관측 포지션 |
| 조건부 평가 | 가격·입출금 가정으로 평가 | 기준평가 자본·충격·연결 수익률 | 실제 NAV·증거금 설정·청산 여유 |
| 탐색 추론 | 모형·사건 선정 비교 | 조정 연도 계수·손실 후 반응 | 인과적 실력·미사용 검증·현재 수익성 |

## 데이터셋 지도

경로는 프로젝트 기준 상대 경로입니다. 출처와 입력 해시가 공급자 근거를 제공하며 CSV 파일 이름 자체가 독립적인 증거는 아닙니다.

| 자료 | 행 단위·키 | 단위·시각 | 생성·해석 |
| --- | --- | --- | --- |
| `data/aoa-execution-*.csv` | 원본 체결, `execid` | 계약 수량·계약 호가 가격·`transacttime`의 UTC 해석 | 원본 4개, 수정하지 않음 |
| `data/aoa-wallet-*.csv` | 비어 있지 않은 거래, `transactid` | XBt는 사토시·날짜와 잘린 시각 | 원본 관측, 상태 보존 필요 |
| `results/manifest.json` | 원본 파일 | 바이트·행 수·SHA-256 | 파일 동일성, 라이선스 아님 |
| `results/extended_research/executed_orders.csv` | `symbol, orderid` | 원주문 전체 실행 기간 | 정상 ID 주문 23,416개, 이 표에서만 0 ID 제외 |
| `results/extended_research/contract_event_states.csv.gz` | `time, symbol, batch_key`, 필요시 방향·유형 | 사건 후 계약 수량·사토시 원가/손익 | 시각·주문 복원이며 독립 판단 수가 아님 |
| `results/portfolio_risk/contract_registry.csv` | `symbol` | 당시 호가·정산 통화·승수 | 46개, 재사용된 현대 심볼보다 당시 명세 우선 |
| `results/portfolio_risk/daily_inventory_all_contracts.csv` | `date, symbol` | 다음 UTC 자정 직전 | 0 수량 포함, 관측일마다 46계약 |
| `results/portfolio_risk/active_positions_reference.csv` | `date, symbol` | 당일 종료 기준가격 | 활성 계약만, 조건부 미실현손익 |
| `results/portfolio_risk/daily_reference_risk.csv` | `date` | UTC 종료·전체 계좌 BTC/USD | 조건부 자본·위험, 실제 증거금 NAV 아님 |
| `results/event_study/account_daily.csv` | 원장 기장 `date` | 부호 있는 정수 사토시 | 정오 간 기장 해석, UTC 일별 평가손익 아님 |
| `results/historical_market_daily.csv` | UTC 표기 `date` | BTC/USD·USDT/USD·무차원 수익률 | 합성 BTC/USDT는 관측된 거래소 호가 아님 |
| `results/extended_research/intraday_daily_extremes.csv` | `date` | UTC 일중 동일 시각 반영 후 수량 | BTC 액면 극값은 복원 수량 기준, 자산 간 가격은 전일 종가 고정 |
| `results/extended_research/historical_mark_minutes.csv.gz` | `sample_date, symbol, time` | 1분·계약 호가 통화 | 이용 가능 시각 기준, 최대 300초 경과 |
| `results/extended_research/historical_mark_sample_equity.csv.gz` | `sample_date, time` | 전체 계좌 1분 BTC/USD 자본 | 월초 33일, 연속 전체 이력 아님 |
| `results/extended_research/conditional_daily_returns.csv` | `date, currency, flow_timing` | BTC 또는 USD·수익률은 무차원 | BOD/MID/EOD 가정·무효 사유 |
| `results/robustness_research/attribution_daily.csv` | UTC `date` | BTC 구성·종가 환산 USD | 가산 항등식, 실현·조건부 미실현 구분 |
| `results/robustness_research/behavior_models.csv` | 결과·명세·블록 길이·항 | 변환된 OLS 계수 | 조건부 관련성, 2018/2021 자본 공통 범위 없음 |
| `results/robustness_research/loss_response_windows.csv` | 사건·종류·길이·지표 | 전후 일별 값 평균의 변화 | 사후 손실 선정, 상대 기준은 `relative_loss/` |
| `results/explorer/research.sqlite` | 위 표와 원본 선택 필드 | 원문 숫자 문자열·명시적 null | 로컬 재생성 캐시, 배포 제외 |

## 핵심 필드

| 필드 | 정의·단위 |
| --- | --- |
| `source_file`, `source_row` | 원본 파일과 CSV 레코드 순번 + 2로 기존 pandas 읽기와 같습니다. 헤더는 1행입니다. 셀 안 줄바꿈이 있는 CSV에서는 물리적인 줄 번호와 다를 수 있습니다. 원본 레코드는 수정하지 않습니다. |
| `execid`, `orderid`, `batch_key` | 체결 UUID·원주문 UUID·복원 묶음 키입니다. 0 UUID를 하나의 원주문으로 보지 않으며 고유 체결 ID로 사건을 구별합니다. |
| `date`, `time`, `transacttime` | 맥락별 시각입니다. 시장 날짜는 UTC 일 종료, 사건은 UTC 해석, 지갑은 기장 날짜와 잘린 원문 시각입니다. 같은 시각 기준으로 무조건 조인하면 안 됩니다. |
| `lastqty`, `quantity`, `contracts` | BTC가 아닌 계약 수입니다. 각각 원본 기록·시각별 묶음·원주문 전체 수량입니다. |
| `lastpx`, `mark_price`, `index_price`, `reference_contract_price` | 당시 계약의 호가 단위 가격입니다. 명세 `quote`의 USD·USDT·XBT를 확인해야 하며, 계약 간 합산하거나 기준가격을 마크로 부르면 안 됩니다. |
| `position`, `position_before` | 사건 후·전의 부호 있는 계약 수입니다. 양수 롱·음수 숏이며 일말 평가 행은 종료 보유량입니다. |
| `held_cost_sat` | 정수 사토시 단위의 음수가 아닌 잔여 원가입니다. 납입 증거금이 아닙니다. |
| `execcost` | 부호 있는 원본 체결 원가, 사토시입니다. 원본 조회에서는 숫자 문자열을 유지하고 복원에서는 당시 계약의 부호 규칙을 적용합니다. |
| `execcomm`, `fee_sat` | 사토시 지급액이며 음수는 리베이트·수취입니다. 실제 기록이 추정 수수료율보다 우선합니다. 펀딩 수수료를 거래 수수료로 다시 세지 않습니다. |
| `gross_sat`, `net_sat` | 거래·정산 비용 전 실현손익과 해당 체결 수수료 차감 후 손익입니다. 사건 상태표의 별도 펀딩은 계좌 단위에서 결합합니다. |
| `amount`, `walletbalance`, `transactstatus` | 원본 사토시 금액·잔액 문자열과 상태입니다. 잔액은 표시 반올림이 있을 수 있습니다. 완료 상태만 현금 항등식에 넣고 미완료·취소도 화면에는 표시합니다. |
| `model_wallet_sat`, `model_wallet_btc` | 복원 지갑 현금이며 후자는 전자를 100,000,000으로 나눈 값입니다. 복원 시각 기준의 거래·정산 비용과 펀딩을 포함합니다. |
| `cash_flow_sat` | 완료된 외부 입금 양수·출금 음수, 원본 날짜 기준입니다. 손익이 아닙니다. |
| `unrealised_btc`, `known_unrealised_btc` | 조건부 계약 손익과 관측 가능한 평가의 합계입니다. 활성 가격이 빠졌다면 알려진 부분 합계를 전체 자본으로 보지 않습니다. |
| `reference_equity_btc`, `reference_equity_usd` | 지갑과 필요한 모든 미실현 평가를 합산하고 일별 BTC 기준가격으로 USD 환산한 값입니다. 완전한 평가가 불가능하면 null입니다. |
| `missing_reference`, `missing_mark_contracts` | 계약 가격 결측 여부·개수입니다. 기존 필드명의 mark는 기준평가 부재를 뜻하기도 하며 다른 행이 거래소 마크 평가라는 증거가 아닙니다. |
| `gross_reference_value_usd`, `gross_value_to_reference_equity` | 계약 기준가치 절댓값 합계와 양의 기준평가 자본 대비 비율입니다. 실제 증거금 레버리지가 아닙니다. |
| `peak_btc_gross_face_usd` | 동일 시각 사건 반영 후 BTC 인버스 계약 USD 액면 절댓값 합계의 최대입니다. 서로 다른 만기의 반대 포지션을 상계하지 않습니다. |
| `peak_all_contract_reference_usd`, `reference_price_date` | 전일 가격을 고정한 여러 계약의 총가치와 그 가격 날짜입니다. 실제 장중 시장가치 최대가 아닙니다. |
| `available_time`, `exchange_time`, `age_seconds`, `valid` | 이용 가능 시각은 거래소·수집 중 늦은 시각, 경과 시간은 평가에서 거래소 시각을 뺀 값입니다. 두 시각이 평가 이전이고 0-300초 경과·양의 마크/지수여야 유효합니다. |
| `complete_marks`, `equity_mark_bod_btc` | 활성 계약과 BTC 환산 가격이 모두 최신일 때 일초 입출금 가정으로 평가한 자본입니다. 불완전하면 null입니다. 표본일에는 외부 흐름이 없습니다. |
| `mark_minus_index_equity_usd` | 지갑·BTC 환산을 고정하고 각 파생 마크를 해당 지수로 바꾼 동일 시각 자본 차이입니다. 전체 기간 베이시스 수익이 아닙니다. |
| `flow_timing`, `weighted_capital`, `return`, `status` | BOD/MID/EOD 가중치는 1/0.5/0입니다. 일별 modified Dietz 분자는 종료 자본−시작 자본−외부 흐름입니다. 평가·자본·입출금 날짜가 무효하면 null을 유지합니다. |
| `coefficient`, `hac_se`, `block_wild_low/high` | OLS 점 추정·달력 Bartlett HAC 오차·보정 없는 잔차 블록 경험 구간입니다. 예측이나 인과 효과가 아닙니다. |
| `change`, `valid_events`, `matched_pairs` | 이후 구간 평균−이전 평균, 유효 사건 분모, 관측 가능한 사건·대조 쌍 수입니다. 결측을 감소하지 않은 사건으로 세지 않습니다. |

## 버전·출처 원칙

v0.1 조건부 에피소드 자료를 v0.2/v0.3 개선 회계로 조용히 바꾸지 않고 보존합니다. v0.4 기준평가는 v0.5/v0.6 조건부 위험·성과의 기준입니다. v0.7은 금융 계산을 바꾸지 않고 결과를 색인합니다. 각 버전 보고서·생성 코드·검증을 함께 사용하세요. [출처 목록](sources.md), 원본 입력 해시, CSV 구조 목록, 묶음 파일 목록은 서로 다른 대상을 설명합니다.
