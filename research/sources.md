# Sources / 출처

Research cutoff: **2026-09-23**, Asia/Seoul session. Numerical current-market cutoff: **2026-09-22 UTC close**. Retrieval timestamps, request URLs and hashes are in [retrieval.json](../data/market/retrieval.json).

I used Exa to review 40 sources across 3 search workstreams. Here, “40 sources” means 40 returned search slots across eight queries, including duplicates; **38 unique URLs** were discovered. [Search log](search_log.json). Workstreams covered contract/accounting mechanics, current-market verification, and historical/structural comparability. Only selected relevant sources support the report. Search-engine publication metadata was not treated as proof of observation date.

| ID | Source and date | Use and quality / 용도·품질 |
| --- | --- | --- |
| D1 | User-supplied `aoa-execution-*.csv`, four files | Primary supplied execution records; hashes in [manifest](../results/manifest.json). Internally auditable, externally unauthenticated. 체결 원본, 외부 진위 미인증. |
| D2 | User-supplied `aoa-wallet-2018-03-01-2021-12-31.csv` | Primary supplied ledger; currency and statuses inspected. 지갑 원본, 전체 계좌 이력 보장은 아님. |
| D3 | `data/90일 서한 - 워뇨띠.txt` | Supplied commentary with no verified publication date or source URL. Qualitative context only. 발행 시점·귀속 미검증, 과거 신호로 사용하지 않음. |
| S1 | [BitMEX, Why Quanto?](https://www.bitmex.com/blog/why-quanto), 2018-08-14 | Contemporaneous issuer description of XBTUSD inverse and ETHUSD quanto mechanics; promotional performance claims excluded. |
| S2 | [BitMEX, ETHUSD launch](https://www.bitmex.com/blog/announcing-the-new-ethusd-perpetual-contract), 2018-08-03 | Historical 0.000001 XBT multiplier. Contract specification evidence, not trader intent. |
| S3 | [BitMEX, Realised PNL calculation](https://support.bitmex.com/hc/en-gb/articles/6205277211037-How-do-I-manually-calculate-my-Realised-PNL), updated 2024-05-28 | Current explanation of accounting and daily posting window. Modern lot examples are not imposed on 2018 contract quantities. |
| S4 | [BitMEX, fees and funding](https://support.bitmex.com/hc/en-gb/articles/5903013223837-What-are-the-Trading-Fees-and-where-can-I-see-what-I-ve-paid) | Describes 04:00/12:00/20:00 UTC funding, consistent with export. No explicit timezone suffix exists in source CSV. |
| S5 | [BitMEX, fee changes live](https://www.bitmex.com/blog/site-announcement/now-live-revamp-of-bitmex-fee-structures-for-increased-trader-rewards), 2021-08-18 | Contemporaneous fee schedule change; actual `execcomm` remains the accounting input. |
| S6 | [BitMEX, DOGEUSDT quanto launch](https://www.bitmex.com/blog/every-doge-has-its-day-introducing-the-new-dogeusdt-quanto-perpetual-contract), 2021-02-02 | Confirms that USDT in a historical symbol does not imply USDT margin or settlement. |
| S7 | [BitMEX, BNBUSDT launch](https://www.bitmex.com/blog/the-bnbusdt-quanto-perpetual-contract-comes-to-bitmex), 2021-05-14 | Confirms BTC collateral and settlement for another USDT-quoted quanto. |
| S8 | [BitMEX, naming and early settlement](https://www.bitmex.com/blog/ada-bnb-doge-dot-and-fil-quanto-perpetuals-new-listing-and-early-settlement-of-contracts-due-to-naming-conventions), 2021-09-23 | Historical contract naming changes; do not map old symbols to current instruments blindly. |
| S9 | [Coin Metrics community data](https://github.com/coinmetrics/data) | Public historical BTC and USDT `PriceUSD`; local copies retained. Snapshot includes rows through 2026-05-24 but valid BTC price only through 2026-05-23. Not a current September feed. |
| S10 | [Coin Metrics PriceUSD definition](https://docs.coinmetrics.io/network-data/network-data-overview/market/price), [timestamp FAQ](https://docs.coinmetrics.io/resources/faqs) | Provider states daily PriceUSD is the UTC end-of-day price labelled by the beginning of that daily interval. |
| S11 | [Bitstamp public API](https://www.bitstamp.net/api/), `/api/v2/ohlc/btcusd/` and `/api/v2/ohlc/usdtusd/` | Direct venue daily candles, 120 closed UTC days, response JSON retained. Exact query URLs in retrieval log. Venue-specific, not a consolidated mark price. |
| S12 | [Binance public market-data endpoints](https://developers.binance.com/docs/binance-spot-api-docs/faqs/market_data_only) | BTCUSDT daily klines from `data-api.binance.vision`; response JSON retained. USDCUSDT downloaded as a supplemental cross only, not treated as USD. |
| S13 | [SEC statement on spot Bitcoin ETP approval](https://www.sec.gov/newsroom/speeches-statements/peirce-statement-spot-bitcoin-011023), 2024-01-10 | Primary regulator source for a post-sample structural change. Does not quantify its causal market impact. |
| S14 | [Yahoo Finance, 22 September 2026 market report](https://finance.yahoo.com/personal-finance/investing/article/bitcoin-and-ethereum-prices-today-tuesday-september-22-2026-crypto-prices-continue-to-surge-to-prices-last-seen-in-january-114724449.html) | Dated secondary context only. News explanations and liquidation estimates were not used as measured causal variables. |
| S15 | [BitMEX, technical details of the XBT lot-size change](https://www.bitmex.com/blog/the-technical-details-of-our-lot-size-change-on-xbtusd-swap-and-xbt-futures), 2021-05-20 | Added for accounting audit v0.2. Historical lot/rounding change effective 2021-06-08. Supports using recorded execution costs, not proof of the inferred batch-allocation implementation. 과거 로트·반올림 변경 근거이며 내부 묶음 처리 인증은 아님. |

The accounting follow-up used targeted official-source web searches, separately from the original Exa search count. S3's settlement-window guidance and S15's historical technical notice were checked. The exact timestamp/order/side grouping and integer allocation rules are empirical hypotheses tested against the supplied ledger, not claims copied from exchange documentation.

Event study v0.3 additionally checked two contemporaneous primary sources on 2026-09-23, separately from the original Exa search count:

- S16: [BitMEX, How We Are Responding to the 13 March DDoS Attacks](https://www.bitmex.com/blog/how-we-are-responding-to-last-weeks-ddos-attacks), 2020-03-16. Exchange account of 02:16 and 12:56 UTC access disruption. Used for operational chronology, not proof of the account's profits, losses, refunds or causal benefit. 거래소의 당시 설명이며 계좌 손익의 인과 증거가 아닙니다.
- S17: [BitMEX, The BitMEX Insurance Fund](https://www.bitmex.com/blog/the-bitmex-insurance-fund), 2019-02-10. Distinguishes liquidation/bankruptcy accounting and engine execution/insurance-fund outcomes. Used to limit interpretation of liquidation fill prices, not to infer historical margin mode or leverage. 청산 가격 해석의 한계 근거이며 실제 마진 설정을 역산하지 않습니다.

The event study reuses the saved historical Coin Metrics BTC/USD and USDT/USD references. It does not refresh the 2026 current-market snapshot or substitute daily closes for intraday marks.

Undated live-price pages and stale search snippets were rejected as current-price evidence. An initial Coinbase public candle request returned HTTP 403; the study uses successfully retrieved Bitstamp/Binance data instead. No missing observations were filled with news prices.

공개 데이터 접근 가능 여부는 재배포 라이선스 확인과 다릅니다. 원본 계정 파일과 서한의 공개 권한은 이 연구에서 확정하지 않았으며, 실제 GitHub 공개 전에 소유자가 결정할 사항입니다.
