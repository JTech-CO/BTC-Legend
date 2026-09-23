# Methodology and audit boundaries

Version 0.1, research cutoff 2026-09-23. [한국어](methodology.ko.md). Numerical evidence comes from [summary.json](../results/summary.json), the associated CSV tables, and the [source register](sources.md).

The [v0.2 accounting audit](../reports/accounting-audit.en.md) refines this baseline's reporting boundary and simultaneous-fill allocation. Baseline episode outputs are retained for comparison; refined accounting outputs are stored separately.

The [v0.4 portfolio methodology](../reports/portfolio-risk.en.md) extends the scope to every supplied contract, settlement and funding record. Its daily reference marks and static risk scenarios remain separate from validated realised accounting and from this v0.1 baseline.

## 1. Preserve and validate the inputs

The five supplied CSVs are read without modification. SHA-256, bytes and row counts identify each original. Execution IDs must be non-null and globally unique. Trade quantities/prices must be positive and directions must be Buy/Sell. All observed settlement currencies are `XBt`. The script fails if these conditions change. No losses, liquidation rows or outliers are trimmed.

There are 1,444,583 execution events: 1,439,207 trades, 5,368 funding events and eight settlements. Funding and settlements are not ordinary fills. The 46 symbols require instrument-aware treatment. In particular, a USDT suffix cannot identify the collateral currency of a historical BitMEX quanto [S6–S8](sources.md).

Wallet input has 4,388 parsed rows, of which 2,135 are entirely empty. Of 2,253 nonblank rows, seven canceled withdrawals are retained in an exclusion table and 2,246 completed records are included. Nonblank transaction IDs are unique. Monetary strings are parsed with Decimal and converted to integer satoshis. This retains their stated precision, but cannot restore precision already lost in the export.

The execution file's earliest timestamp is 2018-03-05 07:28:18.063937. Absence of 1–4 March records means no observed activity in the supplied files, not a demonstrated missing export or proof of no other-account activity.

## 2. Units and payoff conventions

`XBt` is satoshis: **100,000,000 XBt = 1 BTC**. Historical XBTUSD has a nominal contract value of USD 1 [S1](sources.md). Thus 1,000,000 contracts represent USD 1,000,000 face value and approximately 100 BTC notional at USD 10,000/BTC. They are not one million BTC. Notional turnover is not capital deployed.

For signed inverse position q, entry price Pe and exit price Px, the ideal BTC payoff is `q × (1/Pe − 1/Px)`. A long profits from a rise, a short from a fall. The reconstruction uses the execution's recorded satoshi cost per contract instead of recomputing rounded exchange costs from price. Price averaging for inverse cost basis is harmonic. Order tables also show arithmetic VWAP for execution-price description; it must not replace the inverse basis.

For a historical quanto, payoff takes the form `q × multiplier × (Px − Pe)` in BTC. Each multiplier must be historically verified. This release attributes all instruments by their wallet `address` but reconstructs detailed inventory/cost only for XBTUSD. It does not apply the BTC inverse formula to altcoins.

`execcomm > 0` is treated as a charge and negative as a credit. Funding is accounted for separately from trade commissions. Wallet RealisedPNL already includes applicable execution charges, rebates and funding [S3](sources.md). Subtracting them again from wallet PNL would double-count costs. `execcost` is a signed transaction cost/value, not realised profit.

## 3. Fills, orders, bursts and episodes

| Unit | Definition | Limitation |
| --- | --- | --- |
| Fill | A Trade execution with unique execid | One order can create many fills |
| Identifiable order | Same symbol and nonzero orderid, checked for a consistent side | An order is not a full investment decision; amendments/partial cancellation are not fully observable |
| Unidentified fill | Zero UUID orderid | All 28 are labelled Liquidation; retained in accounting, excluded from parent-order claims |
| Burst | Consecutive same-symbol, same-side fills with gaps no greater than a threshold | A sensitivity grouping, not recovered intent |
| Episode | XBTUSD inventory moves from flat to nonzero and returns to flat or crosses zero | A reversal closes one episode and opens another; ignores cross-instrument hedges |

The valid order table has 23,416 rows, including 18,397 XBTUSD orders. The 28 zero-ID fills, including 19 XBTUSD fills, are not assigned fabricated parent IDs. Liquidation fill count is not liquidation-incident count.

XBTUSD burst thresholds of 1/5/30/60/300 seconds produce 74,699/28,815/17,930/16,042/12,199 groups. This variation rules out presenting a single time-cluster count as the trader's true decision count. A change in side always starts a new burst; successive groups need not be economically independent.

For inventory, all XBTUSD Trade rows, including liquidation fills, are sorted by timestamp, orderid, cumqty and execid. `Q(t) = Q(0) + cumulative signed lastqty`. Initial position is assumed zero. At each of 3,961 funding records, the reconstructed absolute position equals funding lastqty. This supports quantity completeness and the opening assumption at those checkpoints; it does not independently authenticate the file or entry basis.

Two timestamps contain both sides. Reversing the within-timestamp order-ID sort produces the same episode count and gross PNL to floating-point precision. This is a narrow tie-order sensitivity check, not proof of a complete exchange sequence.

A reversal allocates its commission in proportion to the quantities closing and opening. Each fully closed episode reports gross PNL minus allocated trade fees, **excluding funding**. Open episodes are not counted as wins or losses. The baseline produces 2,007.11209879 BTC versus wallet PNL of 2,007.08464645 BTC. The [follow-up audit](../reports/accounting-audit.en.md) explains the **+0.02745234 BTC** difference as out-of-window funding and simultaneous-batch cost allocation. A separate integer batch reconstruction matches total wallet PNL, with twelve daily residuals of one or two satoshis. No balancing plug is used, and the baseline episode statistics are not silently redefined.

## 4. Wallet identity and residuals

The aggregate identity in BTC is:

```text
14.48925714 + 3,537.32369404 − 2,814.54321713 = 737.26973405
completed deposits + net realised PNL − completed withdrawals = final wallet
```

This matches the final reported balance exactly, with an implied zero initial balance. The wallet contains five date-order inversions. Several instrument PNL rows share one post-batch balance; row-by-row `balance.diff() == amount` is therefore not a valid general check. We sum completed movements by stated date, then compare their cumulative ledger with the last source-row snapshot on that date.

**154 observed days have a nonzero raw daily residual.** The largest absolute difference is 1.0012 BTC on 2018-04-28; 2018-04-27 differs by 0.54595876 BTC. The follow-up finds that 152 differences round exactly to the scientific-notation source precision. The April pair is a withdrawal date/snapshot ordering conflict, arithmetically reconciled under an explicitly labelled scenario. The actual processing date remains unknown. Both original date-based balances and reported snapshots remain in `wallet_daily.csv`.

Wallet `timestamp`/`transacttime` strings omit the hour and/or date (e.g. `57:26.3`). We do not fabricate exact times. Execution timestamps have no zone suffix. Their 04/12/20 funding cadence agrees with documented BitMEX UTC times [S4](sources.md), so market work uses UTC as a provisional convention. Wallet PNL is analysed by posting date. It cannot establish same-day causal reactions to a midnight-close market series; exchange daily settlement windows also differ from UTC calendar days [S3](sources.md).

## 5. Performance quantities and non-quantities

Reported account performance is net realised **BTC amount**. Instrument PNL follows wallet `address`. Daily win/loss counts refer to aggregate posting days, not trades. Top-ten-day concentration divides their positive realised amounts by total net realised PNL. Cumulative-realised peak-to-trough loss is measured in BTC; it is not NAV maximum drawdown.

No CAGR, TWR, XIRR, Sharpe, leveraged ROE or full account equity MDD is asserted. These require appropriately marked equity, external-flow timing, margin information and boundary positions. Withdrawing BTC is not a loss, receiving a deposit is not trading income, and a first deposit is not necessarily the trader's entire starting wealth.

The optional sum of `daily posted BTC PNL × that day's BTC/USD close` is only a translation convention. It is not realised dollar cash profit, does not account for later holdings or conversions, and does not measure total investment return. A fair passive-BTC benchmark must replicate external flows and valuation times. A price chart alone is not such a benchmark.

## 6. Market calculations and USD/USDT

Coin Metrics supplies the historical daily USD reference series. Its daily PriceUSD represents the end of the labelled UTC day [S9–S10](sources.md). Each period return starts from the previous day's close. Realised volatility is sample standard deviation of daily log returns multiplied by square root of 365. Spot drawdown includes the prior closing baseline. The requested historical calendar has 1,402 daily price observations.

Current data use 120 closed UTC days through 2026-09-22 from Bitstamp BTC/USD and USDT/USD, and Binance BTC/USDT. Dates must be unique/continuous and OHLC boundaries valid. These are venue candles, not synchronous arbitrage quotes, BitMEX marks or order-book liquidity. Coin Metrics' downloaded file contains a final empty-price row dated 2026-05-24 and is not used for September's current snapshot.

Conversion is `BTC/USDT × USD/USDT = BTC/USD equivalent`. The converted cross-venue basis is `(converted price / Bitstamp BTCUSD − 1) × 10,000` bps. Historical synthetic BTC/USDT is reference BTC/USD divided by reference USDT/USD; it is expressly **not an observed exchange BTCUSDT candle**. USDCUSDT is retained as supplemental data, not a substitute for USD/USDT.

Historical regimes use previous-day 30-day returns: above +10%, below −10%, or between. All are exploratory fixed research thresholds. Descriptive regime PNL is neither a return nor proof of which signal caused entries. Posting-date correlations at shifts −1/0/+1 expose timing sensitivity; none estimates causal alpha.

Current analogs use Euclidean distance after scaling 7-day return, 30-day return and 30-day volatility by their historical standard deviations. Select five historical dates separated by at least 30 days. This is a descriptive comparison fitted to the historical sample, not an out-of-sample forecasting model. No future profit or trading rule is inferred.

## 7. Research needed to establish transferability

The next stage requires historical mark/index prices, funding snapshots, order-book/trade feeds with consistent UTC times, historical contract multipliers and margin/risk limits, and data showing available equity and open positions. The follow-up has explained the aggregate XBTUSD gap and the numerical structure of the 2018 discrepancy. Original wallet processing timestamps and exchange batching/rounding documentation would resolve the remaining chronology and tiny daily allocation uncertainty.

Pre-register a small set of testable mechanisms: directional timing, inventory reduction after adverse moves, passive execution savings, funding exposure and position scaling. For each, specify the observable signal and falsification condition before examining its outcomes. Separate discretionary motives from measured behavior.

Use calendar walk-forward train/validation/test splits, purge overlapping holding periods and embargo adjacent samples. Since this release inspected all 2018–2021 observations, none of them is now an untouched confirmation set. A new later dataset must be reserved before tuning. Cluster or block-bootstrap by day/episode, preserve serial dependence, report all tried models and adjust for multiple testing. Evaluate after actual fee tiers, funding, spread, slippage, queue position, adverse selection, latency and size-dependent impact. Stress alternate collateral and USDT depegs. Simulated passive fills require a queue model; a touched limit price is not a guaranteed fill.

Any later simulator or bot can be considered as a separate research stage. This methodology imposes no permanent software-development ban and supplies no present buy/sell instruction.
