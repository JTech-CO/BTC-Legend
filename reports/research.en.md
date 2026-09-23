# BTC-Legend: execution, performance and transferability

**Research v0.1 - 23 September 2026** · [한국어](research.ko.md) · [Methods](../research/methodology.en.md) · [Sources](../research/sources.md)

Accounting update: [v0.2 discrepancy audit](accounting-audit.en.md) explains the aggregate model gap and classifies all 154 snapshot differences. The episode statistics below remain the original fill-sequential baseline.

Event update: [v0.3 large-gain/loss and liquidation study](event-study.en.md) reconstructs extreme posting windows and funding-inclusive episodes. A full text scan finds 59 liquidation-labelled fills, including 31 ETHUSD fills with a valid order ID in addition to the 28 zero-ID fills below.

Portfolio update: [v0.4 portfolio reconstruction](portfolio-risk.en.md) extends inventory/cost accounting to all 46 contracts and adds explicitly conditional spot-reference valuation and stress. The v0.1 statistics below remain the historical baseline.

Further research: [v0.5 marks, intraday exposure and cash-flow-adjusted returns](marks-intraday-returns.en.md) adds observed monthly mark samples and timing sensitivity; [v0.5 behaviour changes](behavior-changes.en.md) compares order frequency, scale, holding time and instrument mix. These do not replace the original baseline or establish continuous actual NAV returns.

## Research conclusion

The supplied account generated substantial **realised BTC profits across both rising and falling BTC markets**. Its results cannot be reduced to a BTC buy-and-hold position or one disclosed technical indicator. The records support an account that traded both directions, scaled order sizes, increasingly supplied liquidity, and earned substantial profits from non-BTC contracts. They also document liquidation-labelled executions and severe realised losses.

The account's economic achievement is measurable; the decision process that caused it is only partly observable. This release does **not** establish a reproducible trading rule or show that the historical performance survives present market conditions. It does identify mechanisms worth testing and several popular explanations that the data do not support.

All account figures refer to the supplied `aoa` export. The user attributes it to 워뇨띠; independent authentication of that attribution and coverage of other accounts remain outside the evidence. Financial measurements below distinguish observations, conditional reconstructions and hypotheses.

## 1. What the dataset actually contains

| Population | Observed result |
| --- | ---: |
| Execution events | 1,444,583 |
| Actual Trade fills | 1,439,207 |
| Funding events / settlements | 5,368 / 8 |
| Instrument symbols | 46 |
| Identifiable executed orders | 23,416 |
| Zero-ID, liquidation-labelled fills | 28 |
| XBTUSD fills / identifiable orders | 941,007 / 18,397 |
| Completed wallet records | 2,246 |

Source: [account summary](../results/summary.json), [unidentified fills](../results/unidentified_order_fills.csv). Earliest observed event: **5 March 2018**, despite the requested period starting 1 March. The original CSVs were not modified.

For XBTUSD, the median identifiable order produces **19 fills**, the 95th percentile about **201**, and the maximum **2,638**. Counting fills as independent decisions radically exaggerates trading frequency. Conversely, one order can be only part of an entry, hedge or exit, so even 18,397 orders is not a “number of completed trades.” A valid zero-to-zero inventory definition produces 2,589 closed XBTUSD episodes under stated assumptions.

The 28 zero-order-ID records are all labelled `Liquidation`. They remain in the position reconstruction and transaction costs. Their count does not establish 28 independent liquidations. Excluding them as bad data would selectively remove adverse outcomes.

![Execution structure](figures/execution_structure.png)

## 2. Profit, withdrawals and what a return would require

| Ledger component | BTC |
| --- | ---: |
| Completed deposits | 14.48925714 |
| Net realised PNL | 3,537.32369404 |
| Completed withdrawals | −2,814.54321713 |
| Final wallet balance | **737.26973405** |

These movements reconcile to the final balance with **zero satoshi aggregate residual**. They do not show that 14.49 BTC was simultaneously invested, that the first deposit was total starting capital, or that withdrawn funds were converted into fiat. Seven canceled withdrawals are excluded from cash movements.

Wallet balance excludes unrealised position PNL. The reconstructed ending XBTUSD inventory is **−29,080,100 USD contracts**, and therefore still open. Dividing final wallet wealth by the first deposit would confound later deposits, withdrawals, open risk and the missing capital history. A headline CAGR, leverage multiple or Sharpe ratio would imply precision the evidence does not provide.

Daily raw comparison has 154 nonzero differences, the largest 1.0012 BTC. The [follow-up audit](accounting-audit.en.md) attributes 152 to displayed precision and two to one withdrawal's date/snapshot ordering conflict. A chronology scenario reconciles the latter, but its actual processing date remains unverified. Source dates and amounts are not silently fixed.

## 3. Where the profits came from

| Instrument | Net realised BTC | Share of account net realised PNL |
| --- | ---: | ---: |
| XBTUSD | 2,007.08464645 | 56.74% |
| ETHUSD | 830.36450739 | 23.47% |
| XBTU21 | 246.33373320 | 6.96% |
| XRPUSD | 173.86144941 | 4.91% |
| ETHUSDM21 | 140.93425904 | 3.98% |
| XBTH20 | 119.20156973 | 3.37% |

These are ledger contributions, including their applicable charges/funding, rather than standalone strategy returns. Negative contributors also exist: BCHUSD **−69.93503012 BTC**, LINKUSDT **−17.84627291 BTC**, and XRPU18 **−17.74146044 BTC**. Full values: [instrument PNL](../results/wallet_pnl_by_symbol.csv).

![Instrument contribution](figures/instrument_contribution.png)

| Year | BTC spot return | All-contract realised BTC | XBTUSD realised BTC | ETHUSD realised BTC |
| --- | ---: | ---: | ---: | ---: |
| 2018, from March | −64.23% | 188.43 | 175.59 | 7.02 |
| 2019 | +94.39% | 516.37 | 511.73 | 18.90 |
| 2020 | +304.93% | 763.64 | 573.17 | 14.41 |
| 2021 | +59.72% | 2,068.88 | 746.60 | 790.03 |

Spot returns use the prior close of each interval and Coin Metrics daily reference prices. Account BTC PNL is an amount with changing capital, not a percentage comparable to spot return. The positive 2018 BTC PNL during a falling market and material reconstructed short profits indicate activity beyond passive BTC appreciation. They do not by themselves estimate risk-adjusted alpha.

The 2021 ETHUSD contribution exceeds XBTUSD's. Explaining the entire account as a Bitcoin-only strategy would omit an economically important change. All observed settlement currencies are `XBt`, including historical USDT-named quanto contracts. A symbol such as DOGEUSDT does not mean that this account held USDT margin [BitMEX's contemporary description](https://www.bitmex.com/blog/every-doge-has-its-day-introducing-the-new-dogeusdt-quanto-perpetual-contract).

## 4. Trading behavior supported by the records

### Larger orders and a changing execution mix

| Year | Identifiable XBTUSD orders, by first fill year | Median order size, USD contracts | Median fills per order | Maker share of filled USD contracts |
| --- | ---: | ---: | ---: | ---: |
| 2018, from March | 8,805 | 200,000 | 8 | 64.56% |
| 2019 | 3,740 | 700,000 | 31 | 67.91% |
| 2020 | 3,511 | 1,500,000 | 51 | 70.41% |
| 2021 | 2,341 | 5,000,000 | 96 | 77.08% |

Source: [orders by year](../results/xbtusd_order_yearly.csv), [execution statistics](../results/xbtusd_yearly.csv). Partial-year exposure differs, so raw annual order counts should not be treated as equal-duration activity rates. Order size is USD face value, not BTC amount, equity or actual leverage.

Larger individual orders explain much of the increase in fills per order. Maker participation also rises, but a Limit order can take liquidity; actual `lastliquidityind` is the measure used here. Quantity-weighting matters: 2018's maker share is 64.56% by contracts but only 47.53% by fill count.

For XBTUSD, net trade charges are approximately **30.34, 24.00, 40.32 and −9.51 BTC** in 2018–2021. Negative 2021 charges represent net rebates. These amounts alone cannot explain 2,007 BTC of XBTUSD ledger PNL. Exchange-wide terms also changed in August 2021: maker rebates fell from 2.5 bps to 1 bp and standard taker fees from 7.5 bps to 5 bps [exchange announcement](https://www.bitmex.com/blog/site-announcement/now-live-revamp-of-bitmex-fee-structures-for-increased-trader-rewards). A current fee schedule cannot be retroactively applied to these trades.

Across all instruments, recorded funding commissions total **−149.57544093 BTC**, equivalent to a net funding credit. Trade commissions cost **78.00012971 BTC** and settlement commissions **0.07551032 BTC**. These are components already reflected in the wallet, not extra income to add to 3,537 BTC. Funding aided performance, but does not account for most of it.

### Short holding times coexist with longer risk

The conditional XBTUSD reconstruction finds **2,589 completed inventory episodes**, with median duration **25.86 minutes**, 90th percentile **23.96 hours**, and 99th percentile approximately **8.00 days**. A label such as “pure scalping” would hide the long holding-time tail and open ending inventory.

| Conditional episode metric | Long | Short |
| --- | ---: | ---: |
| Closed episodes | 1,279 | 1,310 |
| Winning fraction, after trade fees, excluding funding | 77.01% | 74.58% |
| Average winning episode, BTC | 2.01 | 3.70 |
| Average losing episode, BTC | −4.08 | −7.21 |
| Profit factor, excluding funding | 1.65 | 1.50 |

[Episode statistics](../results/xbtusd_episode_statistics_conditional.csv). These are position episodes, not discrete discretionary ideas; BTC sizes vary greatly across time. On this definition the mean losing episode is larger than the mean winning episode. Thus a universal “small losses, large wins” explanation is unsupported. The observed high hit rate compensates for a payoff ratio below one. This does not make the pattern safe or transferable.

The baseline average-cost model's **0.02745234 BTC** wallet comparison gap is explained in [the accounting audit](accounting-audit.en.md) by the reporting cutoff and simultaneous-fill cost allocation. The refined batch accounting has zero aggregate residual and daily differences of at most two satoshis. The episode table above retains the original fill-sequential convention, excludes funding, and omits one open final episode. Other instruments may hedge these episodes. It remains exploratory rather than an audited true trade win rate.

### Collateral changes the meaning of a short

A BTC-collateral account is exposed to the USD price of its collateral. An XBTUSD short can partially offset that exposure. The final short therefore does not prove a simple bearish BTC forecast. Nor do simultaneous opposite positions in related instruments necessarily constitute independent directional bets.

For a fixed wallet balance W and an inverse position q at basis Pe, approximate USD equity at mark P is `W × P + q × (P/Pe − 1)`, before other positions and subsequent cash movements. Its price sensitivity is `W + q/Pe`, showing why reading the short in isolation misses the collateral. Actual effective leverage requires marked total equity and the full portfolio, not a presumed exchange leverage setting.

## 5. Losses and concentration are central findings

Across 1,398 calendar days from the first record to the end, aggregate realised postings are positive on **912**, negative on **467**, and zero on **19** days. The best posting day is **13 March 2020, +275.53795475 BTC**; the worst is **20 May 2021, −281.83947272 BTC**. Posting time is not the time every underlying trade occurred.

The ten best days contribute **1,462.88230959 BTC**, or **41.36% of total net realised PNL**. The largest decline in cumulative realised PNL from its previous peak is **590.97711858 BTC**. That is not the percentage drawdown of marked equity and cannot determine proximity to liquidation.

This concentration makes averages fragile. A few stress episodes, position scale and ability to remain funded may have had disproportionate effects. Whether those episodes reflect repeatable skill, favourable tail outcomes or both needs event-level market and risk reconstruction. Seeing one very successful account introduces selection/survivorship bias even though its losing trades are included.

## 6. Historical regimes and the current BTC market

Historical daily BTC volatility, annualised, ranges from about **70.0% to 78.6%** across the four calendar-year slices. Spot drawdowns within those slices reach approximately **−72.4%, −48.6%, −52.1% and −53.1%**, respectively. See [period calculations](../results/historical_market_periods.csv). These are daily-close drawdowns, not intraday extremes.

An exploratory lagged-30-day trend classification attributes **1,547.65 BTC** of account postings to down-trend-labelled days, **1,791.03 BTC** to up-trend-labelled days and **198.64 BTC** to range-labelled days. The populations differ in capital, composition, day count and settlement timing. This supports examining multiple regimes; it does not establish a trend-following or mean-reversion rule. [Regime table](../results/historical_regimes_descriptive.csv).

### Current quantitative snapshot

Cutoff: **22 September 2026 UTC close**, retrieved on 23 September. [Saved daily calculations](../results/current_market_daily.csv) and [exact source requests](../data/market/retrieval.json).

| Observation | Value |
| --- | ---: |
| Bitstamp BTC/USD close | $86,201.35 |
| Binance BTC/USDT close | 86,208.56 USDT |
| Bitstamp USDT/USD close | $0.99990 |
| Converted Binance BTC quote | $86,199.939144 |
| Converted cross-venue difference | −0.164 bps |
| BTC/USD trailing 7 / 30 / 90-day return | +14.06% / +10.92% / +41.34% |
| Trailing 30-day annualised volatility | 42.82% |

The pattern is a recent upward move with volatility near the **10.49th percentile** of historical rolling-30-day readings. This is a market description, not a trading recommendation. The reference-price method and current venue-close method differ, so exact percentile ranking is approximate. Volatility does not measure spread, market depth, queue competition or liquidation risk.

![Current market comparison](figures/current_market.png)

The small converted price difference is observed across daily closes and venues. It is not an executable arbitrage spread. USDT was not always at parity: the historical reference series has a minimum daily reading of about **$0.95033 on 14 November 2018** within this sample. This is a provider reference observation, not a claimed intraday market-wide low. Multiplying a BTCUSDT quote by one USD without conversion can therefore distort both regimes and dollar performance.

A three-feature descriptive analog exercise selects 23 February 2019, 8 May 2019, 14 April 2021, 28 July 2020 and 8 January 2020. These dates are similar in recent returns/volatility only. The analysis deliberately does not use their later returns to recommend a current position. [Distances and inputs](../results/current_historical_analogs_descriptive.csv).

### What carries over, and what remains unproved

| Candidate mechanism | Evidence here | Requirement before claiming modern applicability |
| --- | --- | --- |
| Parent-order reconstruction | Strong fill fragmentation and valid order IDs | Preserve identity, distinguish forced fills and strategic episodes |
| Passive execution | Growing contract-weighted maker share | Contemporary fees, spreads, fill probability, queue position and adverse selection |
| Short-term directional timing | Profitable conditional long/short episode groups | Timestamped pre-trade signals and honest later holdout tests |
| Funding exposure | Net recorded funding credit | Current venue funding distributions, basis risk and hedge costs |
| Scaling with capital | Larger orders and later nominal BTC profits | Marked equity, risk limits and size-dependent impact |
| BTC collateral and quanto exposures | Explicit XBt settlement and multiple symbols | Separate inverse/quanto/linear payoffs and USD/USDT conversion |
| Surviving extreme events | Large positive and negative days plus liquidations | Full portfolio stress paths and available margin |

There is also a documented post-sample institutional change: US spot Bitcoin ETP listings were approved in January 2024 [SEC](https://www.sec.gov/newsroom/speeches-statements/peirce-statement-spot-bitcoin-011023). That establishes a different product landscape; the present study does not measure ETF-flow causality or assume that liquidity has improved for every instrument and order size.

Current data do not contain the trader's orders after 2021, current BitMEX depth or funding, or a fully specified historical signal. Historical performance therefore cannot be directly replayed against today's chart to establish profit. The next valid claim is a falsifiable research hypothesis, followed by a new untouched out-of-sample test under realistic execution assumptions.

## 7. The supplied letter and the publication boundary

The supplied “90일 서한” describes a shift from short-term signals toward also recording medium-term views. Its authorship/publication date is not independently verified. It cannot establish what was known at a 2018–2021 trade or supply backtest features retrospectively. Its mention of an $85k valuation is not used as a current trading target.

This release provides local research, source fingerprints, transparent exclusions, conditional position reconstruction, dated public market snapshots and bilingual interpretation. It leaves the identifiable accounting residuals visible and does not publish a supposed secret strategy. A future white paper can extend the research into simulation or software after the data and empirical tests justify it.
