# Data dictionary and evidence classes

v0.7 · [한국어](data-dictionary.ko.md) · [Exact CSV schemas](schema-inventory.json) · [Reproduction](reproduction.en.md)

The machine-readable schema inventory records the actual headers, bytes and SHA-256 of every result CSV, including excluded regenerable caches. It is a structural inventory. The semantic definitions below cover the canonical research/explorer datasets; specialised tables retain their additional definitions in the versioned reports and generating scripts. Empty numeric CSV cells become null in the explorer, never an implied zero.

## Evidence classes

| Class | Meaning | Examples | What it does not establish |
| --- | --- | --- | --- |
| Supplied observation | A field in an immutable account export | Execution ID, fill quantity, execution commission, wallet posting | External authenticity, undisclosed account completeness |
| Captured market observation | A saved provider price with its stated timestamp | Monthly exchange mark/index, daily reference price | Executable liquidity or a price outside capture coverage |
| Reconstructed | A deterministic transformation with disclosed assumptions | Signed inventory, remaining cost, parent order | Trader intent, unobserved pre-export positions |
| Conditional valuation | Reconstructed quantities evaluated under price/flow conventions | Spot-reference equity, stress, linked-return scenarios | Actual historical NAV, margin setting, liquidation distance |
| Exploratory inference | A model or selected event comparison | Adjusted year coefficient, post-loss median response | Causal skill, untouched validation, modern profitability |

## Dataset map

Paths are relative to the project root. The source registers and input locks provide provider provenance; a CSV filename alone is not independent evidence.

| Dataset | Row grain / key | Unit and clock | Generation / interpretation |
| --- | --- | --- | --- |
| `data/aoa-execution-*.csv` | Source execution record, `execid` | Quantity in contracts; quote-specific price; UTC interpretation of `transacttime` | Original observation; four files, never edited |
| `data/aoa-wallet-*.csv` | Nonblank source transaction, `transactid` | XBt means satoshis; date plus truncated time | Original observation; statuses must be retained |
| `results/manifest.json` | Original source file | Bytes, rows, SHA-256 | Baseline identity, not a data license |
| `results/extended_research/executed_orders.csv` | `symbol, orderid` | Full parent-order lifetime | 23,416 genuine-ID orders; zero IDs excluded here only |
| `results/extended_research/contract_event_states.csv.gz` | `time, symbol, batch_key` plus side/type if needed | Post-event signed contracts and satoshi cost/PNL | Timestamp/order reconstruction; not independent decisions |
| `results/portfolio_risk/contract_registry.csv` | `symbol` | Historical quote, settlement and multiplier | 46 contracts; historical overrides take precedence over reused modern names |
| `results/portfolio_risk/daily_inventory_all_contracts.csv` | `date, symbol` | Just before next UTC midnight | Contains zero inventories; 46 contracts per observed day |
| `results/portfolio_risk/active_positions_reference.csv` | `date, symbol` | Current-day close reference | Only active contracts; conditional unrealised PNL |
| `results/portfolio_risk/daily_reference_risk.csv` | `date` | UTC close; whole-account BTC/USD | Conditional capital/risk, not actual margin NAV |
| `results/event_study/account_daily.csv` | Ledger posting `date` | Signed integer satoshis | Noon-to-noon posting interpretation, not UTC-day marked profit |
| `results/historical_market_daily.csv` | UTC-labelled `date` | BTC/USD, USDT/USD and dimensionless returns | Daily references; synthetic BTC/USDT is not an observed venue quote |
| `results/extended_research/intraday_daily_extremes.csv` | `date` | Post-timestamp quantities within UTC day | BTC face extrema exact under reconstruction; cross-asset price reference fixed to previous close |
| `results/extended_research/historical_mark_minutes.csv.gz` | `sample_date, symbol, time` | One-minute sample, contract's quote currency | As-of captured price; maximum age 300 seconds |
| `results/extended_research/historical_mark_sample_equity.csv.gz` | `sample_date, time` | Whole-account minute equity, BTC/USD | 33 month starts; not a continuous history |
| `results/extended_research/conditional_daily_returns.csv` | `date, currency, flow_timing` | BTC or USD; dimensionless return | BOD/MID/EOD assumptions, explicit invalidity |
| `results/robustness_research/attribution_daily.csv` | UTC `date` | BTC components and EOD-converted USD | Additive identity; realised and conditional unrealised components separated |
| `results/robustness_research/behavior_models.csv` | Outcome, specification, block length, term | Transformed OLS coefficient | Conditional association, no capital common support between 2018/2021 |
| `results/robustness_research/loss_response_windows.csv` | Event, kind, horizon, metric | Changes in daily-window means | Retrospective loss selection; relative variant in `relative_loss/` |
| `results/explorer/research.sqlite` | Tables above plus selected raw fields | Source strings preserved; nulls explicit | Local disposable cache, excluded from distribution |

## Canonical fields

| Fields | Definition and units |
| --- | --- |
| `source_file`, `source_row` | Original filename and CSV record index + 2, matching upstream pandas import. Header is row 1; not necessarily a physical line in a CSV containing embedded newlines. No source record is rewritten. |
| `execid`, `orderid`, `batch_key` | Execution UUID, original order UUID, reconstruction grouping key. A zero order UUID never identifies a single parent order; its execution ID supplies the distinct event key. |
| `date`, `time`, `transacttime` | Context-specific clock. Market dates label UTC day closes; event times use UTC interpretation; wallet dates are posting dates and source time strings are truncated. These are not interchangeable joins. |
| `lastqty`, `quantity`, `contracts` | Contract count, not BTC quantity. `lastqty` is a source record; `quantity` a timestamp batch; `contracts` the parent-order total. |
| `lastpx`, `mark_price`, `index_price`, `reference_contract_price` | Price in the historical contract's quote units. Use registry `quote`: USD, USDT, or XBT. Do not sum across instruments or rename a reference price as a mark. |
| `position`, `position_before` | Signed contract count after/before the event; positive long, negative short. Closing reference rows use end-of-day positions. |
| `held_cost_sat` | Nonnegative remaining inventory cost basis in integer satoshis; not cash margin posted. |
| `execcost` | Signed source execution cost, satoshis, retained as original numeric text in source extracts. Replays use historical instrument sign mechanics. |
| `execcomm`, `fee_sat` | Satoshi charge; negative means rebate/credit. Actual observations supersede assumed fee schedules. Funding `execcomm` is not counted again as a trade fee. |
| `gross_sat`, `net_sat` | Gross realised trade/settlement PNL and gross less associated execution fee. Event states exclude separate funding, which is joined separately at the account level. |
| `amount`, `walletbalance`, `transactstatus` | Wallet source strings in satoshis and transaction status. Displayed balance precision may be rounded. Only `Completed` flows enter cash identities; pending/cancelled rows can still be viewed. |
| `model_wallet_sat`, `model_wallet_btc` | Reconstructed wallet cash; second equals first / 100,000,000. Includes actual trade/settlement costs and funding within the reconstruction clock. |
| `cash_flow_sat` | Completed external deposits positive, withdrawals negative, source date convention. Not profit. |
| `unrealised_btc`, `known_unrealised_btc` | Conditional position PNL and sum of available position valuations. A partial known sum is not full equity when an active mark is missing. |
| `reference_equity_btc`, `reference_equity_usd` | Model wallet plus all required reference unrealised PNL; USD conversion at BTC daily reference. Null if complete valuation is unavailable. |
| `missing_reference`, `missing_mark_contracts` | Missing position price flag / count. Here “mark” in legacy count names can mean absent reference valuation, not proof that other rows use exchange marks. |
| `gross_reference_value_usd`, `gross_value_to_reference_equity` | Sum of absolute contract reference values and division by positive reference equity. Not actual margin leverage. |
| `peak_btc_gross_face_usd` | Maximum sum of absolute inverse BTC-contract USD face following a timestamp's events. Opposite maturities are not netted. |
| `peak_all_contract_reference_usd`, `reference_price_date` | Cross-contract gross value under fixed preceding-day prices, and that price date. Not the true intraday market-value peak. |
| `available_time`, `exchange_time`, `age_seconds`, `valid` | Captured-price availability is the later exchange/collector timestamp; age is valuation minus exchange time. Both timestamps precede valuation; valid requires age 0-300 seconds and positive mark/index. |
| `complete_marks`, `equity_mark_bod_btc` | All active contracts plus BTC conversion have fresh captured prices; mark-valued equity under beginning-of-day flow convention. Null if incomplete. Sample days have no external flows. |
| `mark_minus_index_equity_usd` | Same-time account valuation difference with each derivative mark replaced by its own index, fixed wallet and BTC conversion. Not full-history basis profit. |
| `flow_timing`, `weighted_capital`, `return`, `status` | BOD/MID/EOD capital weights 1/0.5/0. Daily modified-Dietz numerator is end minus beginning equity minus external flow. Invalid valuation/capital/flow chronology stays null. |
| `coefficient`, `hac_se`, `block_wild_low/high` | OLS point estimate, calendar Bartlett HAC error and unadjusted residual-block empirical quantiles. Not a forecast or causal effect. |
| `change`, `valid_events`, `matched_pairs` | After-window mean minus before-window mean, valid event denominator, and number of observable event-control pairs. Missing changes do not count as non-decreases. |

## Version and provenance rules

v0.1 conditional episode outputs are retained and not silently replaced by the refined v0.2/v0.3 accounting. v0.4 reference valuation remains the baseline for v0.5/v0.6 conditional risk and performance. v0.7 indexes those outputs without changing financial formulas. Use each result's versioned report, generating script and validation together. The source register is [sources.md](sources.md); original-input lock, CSV inventory and package-member manifest describe different objects and should not be substituted for one another.
