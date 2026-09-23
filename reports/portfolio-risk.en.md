# Full portfolio risk reconstruction

Research v0.4, 23 September 2026. [한국어](portfolio-risk.ko.md) · [Event study](event-study.en.md) · [Numerical summary](../results/portfolio_risk/summary.json)

## What has been reconstructed

All **46 contracts**, including eight settlement events, now have instrument-specific inventory and cost reconstruction. **Every contract's aggregate realised PNL matches its wallet total exactly** within the reporting window. The reconstructed account total is **3,537.32369404 BTC**. All **5,368 funding-position checks match**. Sixteen contract/date comparisons retain differences of one or two satoshis, with an absolute sum of 18 satoshis and net zero.

This establishes substantially stronger portfolio accounting than the previous XBTUSD-only reconstruction. It does not supply historical exchange marks, margin allocations or liquidation thresholds. The valuation and stress layer below is a separately labelled **daily spot-reference scenario**, with zero perpetual/futures basis. It is not an audited NAV series or actual account leverage.

The main risk findings are:

- BTC collateral can outweigh a BTC short. On **499 of 821** eligible daily snapshots with a net short BTC inverse position, the portfolio still has **positive USD sensitivity to BTC** with other assets' USD prices held fixed. This is an economic offset measurement, not proof that hedging was the trader's intent.
- On **24 June 2021**, ETHUSD long and ETHUSDM21 short exposures almost cancel. The next day's settlement removes the futures leg while leaving the perpetual long open. Risk changes even without a new opening order.
- Historical USDT-labelled products cannot be mapped blindly to today's specifications. Five symbols now resolve to USDt-settled products, while the supplied trades belong to **XBt-settled quanto contracts**.
- Up to **eight contract symbols** are simultaneously nonzero. This count can include residual quantities and related underlyings, so it is not a measure of diversification.

## 1. Contract definitions and source checks

The saved [contract registry](../results/portfolio_risk/contract_registry.csv) contains 8 inverse BTC contracts, 26 BTC-quoted linear contracts, 11 quanto contracts and one UP option-like contract. All supplied executions settle in XBt, the satoshi unit. The registry combines a saved public instrument response, historical issuer announcements and a check against every trade's recorded cost.

For inverse contracts, ideal absolute satoshi value per contract is `100,000,000 / quoted USD price`. Historical lot rounding explains differences of at most 0.5 satoshi per contract. For the linear and quanto products, `abs(execcost) / quantity` agrees with the selected multiplier times quoted price to floating-point precision. Recorded execution costs, rather than ideal regenerated values, remain the accounting inputs.

The public instrument endpoint returns settled and unlisted instruments, but its response is **not a versioned historical specification archive**. The current response's state, expiry, lot size, margin fields and live conversion factors are not imposed on old executions. [BitMEX instrument API](https://docs.bitmex.com/api-explorer/get-instruments).

| Historical symbol | Quote | Historical multiplier, satoshis per quote unit | Historical settlement | Current response settlement |
| --- | --- | ---: | --- | --- |
| ADAUSDT | ADA/USDT | 1,000,000 | XBt | USDt |
| BNBUSDT | BNB/USDT | 100 | XBt | USDt |
| DOGEUSDT | DOGE/USDT | 100,000 | XBt | USDt |
| DOTUSDT | DOT/USDT | 10,000 | XBt | USDt |
| LINKUSDT | LINK/USDT | 10,000 | XBt | USDt |

The historical ADA/DOT specifications and the distinction between old and newly named contracts are documented in the [September 2021 naming/settlement notice](https://www.bitmex.com/blog/ada-bnb-doge-dot-and-fil-quanto-perpetuals-new-listing-and-early-settlement-of-contracts-due-to-naming-conventions). The [BNB launch](https://www.bitmex.com/blog/the-bnbusdt-quanto-perpetual-contract-comes-to-bitmex), [DOGE launch](https://www.bitmex.com/blog/every-doge-has-its-day-introducing-the-new-dogeusdt-quanto-perpetual-contract) and [LINK launch](https://www.bitmex.com/blog/introducing-a-new-linkusdt-quanto-perpetual-contract-and-increased-leverage-on-our-linkusdt-quanto-future-contract) independently identify BTC settlement and their multipliers. These historical overrides are explicit columns in the registry.

## 2. Inventory, settlement and cash accounting

Trade and Settlement events change signed quantity; Funding does not. Same-timestamp/order/side executions are grouped as in the preceding audit, while zero-ID records retain individual execution keys. Partial-close and reversal cost allocations use integer satoshis and preserve remaining basis. Inverse and linear/quanto contracts have opposite cost-to-PNL signs. Every settlement is checked to close exactly the supplied remaining quantity and leave zero cost.

This treatment matters. The export includes a **1,800,000-contract XBTM19 short** closed by settlement on 28 June 2019, and a **136,076-contract ETHUSDM21 short** settled on 25 June 2021. Counting only Trade records would leave fictitious inventory after expiry. The UP contract also settles at zero, a valid recorded settlement value. Its accounting can be reconciled even though an earlier option fair value cannot be reconstructed.

Under the zero-initial-inventory assumption, 45 contracts end flat. Only **XBTUSD remains short 29,080,100 contracts**, with absolute held cost **569.22139118 BTC**. The [funding checks](../results/portfolio_risk/funding_inventory_checks.csv) support quantity reconstruction wherever funding observations exist; they do not independently validate non-funding instruments or undisclosed accounts.

[Contract accounting](../results/portfolio_risk/accounting_by_contract.csv) reconciles each symbol to the wallet. XBTUSD has the previously disclosed twelve tiny day-level discrepancies. ETHU18 and LINKUSDT each add two one-satoshi discrepancies. All remain visible in [the residual table](../results/portfolio_risk/remaining_daily_residuals.csv), with no balancing adjustment.

Two clocks are retained:

1. **Accounting validation:** the wallet's previous-noon to labelled-noon UTC convention.
2. **Risk snapshots:** positions and model cash strictly before the next UTC midnight, matched to the preceding calendar date's daily closing reference price.

Synthetic end-of-day wallet cash is cumulative realised execution PNL minus recorded costs/funding charges, plus completed deposits and withdrawals through their labelled dates. We do not attach a noon wallet balance to a midnight position. Cash-flow timestamps remain truncated, and the 27–28 April 2018 withdrawal chronology remains unresolved. Its dates are explicitly flagged; source dates are preserved.

At 31 December's UTC close, modeled wallet cash is **737.28931453 BTC**, 0.01958048 BTC above the final supplied noon wallet balance of 737.26973405 BTC. The difference is exactly the two already identified later funding events, not an additional profit adjustment.

## 3. Valuation assumptions and coverage

The daily reconstruction starts on **5 March 2018**, the first observed account event, and ends on 31 December 2021. The requested 1–4 March period has no observed account events; it is not presented as verified zero-risk history.

Twelve additional historical USD reference series were downloaded from Coin Metrics for ETH, XRP, BCH, LTC, ADA, EOS, TRX, DOGE, BNB, DOT, LINK and YFI. Existing BTC and USDT snapshots are reused. URLs, retrieval times and hashes are saved in [the retrieval log](../data/portfolio_market/retrieval.json). New files do not replace the earlier market snapshots.

The contract quote proxy is:

| Contract quote | Proxy used |
| --- | --- |
| BTC/USD inverse | BTC USD reference |
| Altcoin/USD quanto | Altcoin USD reference |
| Altcoin/USDT quanto | Altcoin USD reference divided by USDT USD reference |
| Altcoin/BTC linear | Altcoin USD reference divided by BTC USD reference |

These are underlying reference values, not observed derivative marks. Both perpetual and maturity basis are zero in the base scenario. Each position's unrealised BTC PNL is calculated against its recorded remaining basis; wallet BTC plus the sum of unrealised BTC gives reference equity, which is then converted at the BTC USD reference.

All active conventional contracts have usable daily references. **1,397 of 1,398** daily snapshots have complete scenario valuation. On **3 May 2018**, five XBT7D_U110 contracts are still open and their option fair value is unavailable. Full equity and risk ratios are left missing, not filled with zero or a stale trade price. The [contemporaneous UP product notice](https://www.bitmex.com/blog/ups-and-downs-product-update) also shows why this symbol must not be treated as an ordinary BTC futures contract.

Seven snapshots, 22–28 March 2018, have zero reconstructed cash and no positions. Ratios with equity in the denominator are unavailable there. The remaining **1,390 snapshots** have complete, positive reference equity. Coverage percentages refer to snapshot availability, not authentication or percentage of economic risk captured.

## 4. BTC collateral changes portfolio direction

For BTC wallet cash W, signed inverse quantity q and entry price Pe, with no other positions:

```text
Equity_USD(P) = W × P + q × (P / Pe − 1)
d Equity_USD / d P = W + q / Pe
```

A short offsets some BTC collateral exposure. It becomes a net bearish USD portfolio only when the short's price sensitivity exceeds the remaining collateral exposure. Quanto and BTC-cross positions add further terms, so the implementation revalues the full portfolio under factor shifts rather than summing raw contract quantities.

In the CSV outputs, `btc_factor_delta_usd`, `btc_derivative_delta_usd` and `alt_factor_delta_usd` are local USD sensitivities per unit relative price move, estimated by central differences at ±0.01%. Multiply them by `0.01` for the local USD effect of a +1% move. The alt factor shifts all non-BTC assets' USD prices together. Finite joint shocks use full revaluation, including cross-effects, rather than adding these first-order sensitivities.

At **31 December 2021 UTC close**:

| Component | Reference-scenario result |
| --- | ---: |
| BTC reference price | USD 46,355.11733 |
| Modeled wallet cash | 737.28931453 BTC |
| XBTUSD unrealised PNL | +58.11172056 BTC |
| Reference equity | 795.40103509 BTC / USD 36.8709 million |
| BTC cash contribution to a +1% BTC move | +USD 341,771 |
| Derivative contribution to a +1% BTC move | −USD 263,863 |
| Net contribution to a +1% BTC move | **+USD 77,908** |

Although the inverse position is short USD 29.0801 million face value, the combined portfolio remains positively sensitive to BTC in USD terms. A static BTC −20% shock reduces the reference equity by approximately **USD 1.5582 million, or 4.23%**, holding positions and other factors fixed. These are historical scenario calculations, not an estimate of a liquidation price or a recommendation for a hedge today.

![Portfolio sensitivities and static stress](figures/portfolio_risk_snapshots.png)

Across all eligible net-short BTC inverse snapshots, **499 of 821 (60.78%)** remain positive to the BTC factor. Counting shorts as independent bearish bets would misclassify these snapshots. A positive BTC factor with other USD prices fixed does not guarantee profit in a correlated crypto rally: short altcoin exposure can dominate the combined move.

## 5. ETH offsets and the expiry of protection

At **24 June 2021 UTC close**, positions include:

| Contract | Signed contracts | Signed USD reference value |
| --- | ---: | ---: |
| ETHUSD | +135,099 | +9,302,347 |
| ETHUSDM21 | −136,076 | −9,369,619 |
| XBTUSD | +12,023,900 | +12,023,900 |
| XBTU21 | +40,000,000 | +40,000,000 |

The ETH pair has gross reference exposure **USD 18.6720 million**, but only **−USD 67,272** of net ETH-factor exposure under equal spot-based marks. A static ETH/alt USD price decline of 30%, BTC unchanged, adds only about **USD 20,182** to equity. This is economically consistent with a substantial offset, but the records do not establish the intended strategy, contemporaneous basis or margin netting treatment.

The short ETH future settles at **25 June 11:59:59.999999 UTC**. Checkpoints just before and after settlement show ETHUSD remains **+135,099 contracts**, while ETHUSDM21 moves from **−136,076 to zero**. The exact quantity change comes from the source settlement; it is not an assumption based on today's expiry field. [Checkpoint inventory](../results/portfolio_risk/event_checkpoint_inventory.csv).

At the following daily close, net ETH-factor reference exposure is **+USD 7.7811 million**. The isolated alt −30% scenario changes from approximately **+0.04%** of reference equity on 24 June to **−6.58%** on 25 June. BTC inverse long exposure also rises from 52.0239 million to 70.0218 million contracts. A joint BTC −20% / alt −30% scenario changes from **−42.98% to −64.73%**. Those changes also reflect new trades, changed prices and changed equity, so the difference is not attributed exclusively to expiry.

![Settlement, offsets and reference equity](figures/portfolio_settlement.png)

Wallet cash rises from **1,174.75977610 to 1,314.15497918 BTC** across these two UTC closes, while reference equity falls from **1,304.61597254 to 1,119.83723019 BTC**. Realisation of accumulated gains and concurrent market losses can produce this pattern. The example shows why an unusually profitable wallet posting or a rising cash balance is insufficient evidence of increasing total wealth. It remains a spot-reference scenario, not a claim about exact exchange-marked NAV.

## 6. Stress results and concentration

The eight scenarios are BTC ±20%, all non-BTC assets' USD prices −30%, joint BTC/alt moves of −20%/−30% and +20%/+30%, USDT/USD −5%, and maturity-futures quote basis ±5% with perpetual proxies unchanged. Positions, wallet cash and cost bases are held fixed. Revaluation includes the interaction between a quanto's BTC PNL and the USD value of that BTC. It excludes subsequent fees, funding, liquidation, execution constraints and rebalancing. Shock magnitudes are illustrative, not fitted quantiles or probabilities.

| UTC close | BTC −20% | Joint decline | Joint rise | Interpretation |
| --- | ---: | ---: | ---: | --- |
| 2020-10-19 | +66.33% | +66.33% | −66.33% | Large BTC short exceeds collateral sensitivity |
| 2021-05-18 | −8.08% | −1.88% | −1.22% | BTC and ETH shorts interact with BTC collateral |
| 2021-05-19 | −19.99% | −42.42% | +53.64% | ETH long exposure adds downside after the intraday changes |
| 2021-06-24 | −43.01% | −42.98% | +42.96% | ETH mostly offset; BTC exposure remains large |
| 2021-10-12 | −5.64% | +25.88% | −41.63% | BTC factor positive, but large ETH/XRP shorts dominate a joint rise |
| 2021-12-31 | −4.23% | −4.23% | +4.23% | BTC short partly offsets BTC cash exposure |

Percentages divide the scenario's USD equity change by that snapshot's positive reference equity. They are not realised daily returns. [All scenarios](../results/portfolio_risk/daily_stress.csv) and [cash/contract contribution breakdown](../results/portfolio_risk/focus_stress_contributions.csv).

The May snapshots illustrate sampling limits. Both BTC and ETH are short at the 18 May UTC close, but the exact **19 May 12:00 checkpoint** has XBTUSD **+30,702,992** and ETHUSD **+181,667** contracts. By the 19 May UTC close, XBTUSD is nearly flat short and ETHUSD is long 120,118. A once-daily snapshot cannot establish the maximum intraday risk taken before the large loss.

The maximum gross derivative reference-value/equity ratio is **32.27 on 20 March 2018**, an early snapshot with small remaining equity and a dated deposit. This is a proxy ratio, not the leverage selector or the true maximum intraday leverage. Some static shocks exceed 100% of base equity and generate negative hypothetical equity. The model does not simulate maintenance-margin liquidation, so these outputs cannot be interpreted as actual losses, bankruptcy events or amounts collectible from the trader.

USDT quote risk is distinct from USDT collateral risk. In the USDT −5% scenario, asset USD values are fixed and their USDT quotes rise by `1 / 0.95`; short historical quanto positions can lose even though there is no USDT margin balance to haircut. The largest percentage reduction in this scenario is about **4.15% on 10 May 2021**. Real depegs can move other assets, basis and liquidity simultaneously; that is outside this isolated test.

## 7. What remains unidentified

The complete source-account quantity and realised-cost model is well reconciled. The risk layer still needs historical contract mark/index data, maturity basis, intraday cash timing, open-order margin, margin mode and risk-tier history before it can support actual leverage, maintenance headroom or liquidation-distance claims. A percentage drawdown of raw USD equity would also mix withdrawals and changing BTC conversion; this release does not present it as an investment return.

No covariance model, VaR, expected shortfall, Sharpe ratio or CAGR is estimated. Eight contract names can share the same crypto factors. Static stress shows exposure under specified moves, not event probabilities or diversification benefits during crises. Historical success remains compatible with material tail exposure, changing position scale and economically offsetting positions; it does not identify a reproducible modern signal.

## 8. Reproduction

```text
python scripts/portfolio_risk.py
python scripts/portfolio_figures.py
python -m unittest discover -s tests -v
python scripts/verify_portfolio_risk.py
```

These commands run offline using saved inputs. `python scripts/fetch_portfolio_market.py` is an optional public-data acquisition step; successful existing snapshots are reused. A later download can contain source revisions and must be treated as a new snapshot.

The [validation output](../results/portfolio_risk/validation.json) checks raw-source terminal quantities, every contract's ledger total, all funding quantities, settlement closure, missing-value handling, position-to-portfolio valuation and stress contribution conservation. Original account files and v0.1–v0.3 results remain intact. New evidence is under `results/portfolio_risk/`; it does not silently replace earlier episode definitions or the 2026 market snapshot.
