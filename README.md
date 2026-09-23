# BTC-Legend

**English is the default. [한국어](README.ko.md)**

Empirical research on the supplied `aoa` trading and wallet export attributed by its provider to **워뇨띠 (Wonyotti)**. The requested study period is **1 March 2018–31 December 2021**. The first observed account event is **5 March 2018**. Attribution, authenticity and completeness outside these files have not been independently established.

The project studies execution, inventory, realised performance, losses, collateral and market conditions. Its present deliverable is research, with no live trading, trade recommendations or exchange account integration. Future simulation or trading software is not categorically prohibited. No Git repository was initialized, and nothing was committed or pushed.

## Read the research

| Document | English | Korean |
| --- | --- | --- |
| Findings, historical/current comparison, transferability | [Research report](reports/research.en.md) | [연구 보고서](reports/research.ko.md) |
| Follow-up: accounting discrepancy attribution | [Accounting audit v0.2](reports/accounting-audit.en.md) | [회계 차이 추적 v0.2](reports/accounting-audit.ko.md) |
| Definitions, accounting, data quality, reproducibility | [Methodology](research/methodology.en.md) | [분석 방법론](research/methodology.ko.md) |
| External source register | [Sources](research/sources.md) | Shared bilingual register |
| Machine-readable findings | [Account summary](results/summary.json), [market summary](results/market_summary.json) | Same numerical outputs |

## Principal observations

- **1,439,207 trade fills**, **23,416 identifiable executed orders**, and **28 liquidation-labelled fills with zero UUID order IDs**. The latter remain in inventory and cost calculations but cannot be assigned real parent orders.
- **3,537.32369404 BTC** in account-wide net realised ledger PNL. XBTUSD contributes **2,007.08464645 BTC**, approximately **56.74%**. Other contracts matter substantially.
- Completed deposits of **14.48925714 BTC**, withdrawals of **2,814.54321713 BTC**, and final wallet balance of **737.26973405 BTC** reconcile exactly. This is a cash ledger identity, not a total-return calculation.
- XBTUSD has **941,007 fills and 18,397 identifiable orders**. Its reconstructed end position is **short 29,080,100 USD contracts** under an initial-zero-inventory assumption supported by 3,961 funding-position checks.
- The final current-market comparison uses fully closed UTC days through **22 September 2026**, with BTC/USD, BTC/USDT and USDT/USD separately observed.

![Market and wallet research](reports/figures/market_wallet.png)

## Reproduce locally

Python 3.11+ and the packages in `requirements.txt` are sufficient. The supplied source CSVs must remain in `data/` under their original filenames. Commands below run from the project root.

```text
python scripts/analyze.py
python scripts/accounting_audit.py
python scripts/market_analysis.py
python scripts/figures.py
python -m unittest discover -s tests -v
python scripts/verify.py
```

These commands use saved market inputs and do not require network access. `python scripts/fetch_market.py` optionally downloads public market data for the fixed research cutoff; it never uses authenticated or trading endpoints. Do not refresh snapshots before reproducing the published version. Upstream revisions can change later downloads. Source hashes are recorded in `results/manifest.json` and `data/market/retrieval.json`.

`results/orders.csv` contains identifiable orders. Episode files explicitly marked `conditional` are exploratory estimates, not fully reconciled exchange statements. The original files are never overwritten. Raw account data are excluded by `.gitignore`; source licensing and redistribution are not asserted by this repository. No software/data license has been selected on the owner's behalf.

## Limits that affect interpretation

The [accounting follow-up](reports/accounting-audit.en.md) explains the baseline **0.02745234 BTC** gap as **0.01958048 BTC of out-of-window funding** plus **0.00787186 BTC of inventory cost allocation**. The refined XBTUSD aggregate matches the wallet exactly. Twelve posting dates retain differences of 1–2 satoshis. Of 154 raw wallet snapshot differences, 152 match the source's displayed precision; two dates involve one withdrawal with ambiguous processing chronology. Wallet timestamps remain truncated and ending inventory remains open. NAV returns, exact leverage, Sharpe ratios, liquidation prices, predictive signals and modern profitability are not established.

`results/summary.json` and the conditional episode files retain the v0.1 fill-based baseline. Refined accounting evidence is in [results/accounting_audit/summary.json](results/accounting_audit/summary.json); it does not silently replace the original episode statistics.
