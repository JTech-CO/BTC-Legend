# Accounting discrepancy audit

Version 0.2, 23 September 2026. [한국어](accounting-audit.ko.md) · [Baseline research](research.en.md) · [Machine-readable results](../results/accounting_audit/summary.json)

## Findings

The original **0.02745234 BTC XBTUSD aggregate discrepancy is explained** by two measurable effects: different reporting cutoffs and cost allocation across a simultaneous execution batch. The refined reconstruction matches the supplied XBTUSD wallet total exactly. It does not match every daily posting: twelve days retain differences of one or two satoshis, with zero net difference over the period.

Of the **154 wallet snapshot discrepancy days**, 152 are exactly consistent with the precision of the balance strings in the original CSV. Two dates are affected by one withdrawal whose stated date and balance sequence disagree. An explicit chronology scenario resolves their arithmetic, but the true processing date remains unverified. No source records were corrected or removed.

| Original issue | Audit finding | Remaining uncertainty |
| --- | --- | --- |
| 152 small wallet snapshot differences | Reconstructed balances round exactly to the source's displayed precision | Exact hidden digits cannot be recovered from the displayed balance itself |
| 27–28 April 2018 snapshot differences | A withdrawal dated 27 April carries a balance after the 28 April PNL | Request date, processing date, or export date cannot be distinguished |
| XBTUSD total difference, 2,745,234 satoshis | 1,958,048 from the reporting boundary; 787,186 from final inventory cost allocation | Twelve daily differences remain, each at most two satoshis |

The account-wide net realised amount of **3,537.32369404 BTC**, XBTUSD ledger PNL of **2,007.08464645 BTC**, deposits, withdrawals and final wallet balance are unchanged. The audit revises the explanation of the comparison errors, not the supplied ledger's totals.

## 1. Wallet precision: 152 days

The wallet has 1,380 dates with a completed-record balance snapshot. Of these, 1,226 match reconstructed balances exactly. The 152 precision cases all round-trip to their original scientific-notation balance.

For example, on 5 June 2021:

```text
Reconstructed balance: 100,334,421,760 satoshis
Source balance text:   1.00334E+11
Displayed value:       100,334,000,000 satoshis
Raw difference:        -421,760 satoshis = -0.00421760 BTC
```

The source text has a quantum of **1,000,000 satoshis (0.01 BTC)**. Rounding the reconstructed value to that quantum gives exactly the source value. The audit uses each raw string's Decimal exponent; it does not apply an arbitrary tolerance or derive a precision assumption from the discrepancy's size.

All 152 satisfy this test. They should be classified as **display-precision compatible**, not as evidence of missing cash. This establishes compatibility, not independent authentication of the underlying account.

Evidence: [all daily classifications](../results/accounting_audit/wallet_daily_classification.csv), [the original 154 discrepancy days](../results/accounting_audit/wallet_154_residual_days.csv). Source row numbers are one-based CSV rows including the header.

## 2. The April withdrawal chronology

The relevant source sequence is:

| CSV row | Stated date | Event | Amount, satoshis | Reported balance, satoshis |
| --- | --- | --- | ---: | ---: |
| 79 | 2018-04-26 | XBTUSD realised PNL | +170,204,947 | 424,743,181 |
| 80 | 2018-04-27 | XBTUSD realised PNL | +1,718,121 | 426,461,302 |
| 81 | 2018-04-28 | XBTUSD realised PNL | +54,595,876 | 481,057,178 |
| 82 | 2018-04-27 | Completed withdrawal | −100,120,000 | 380,937,178 |

The withdrawal identity is exact: **481,057,178 − 100,120,000 = 380,937,178**. Its displayed balance therefore incorporates the row labelled 28 April, despite its own date label of 27 April.

Grouping by the original date puts this withdrawal into 27 April and then picks its balance as that date's last source-row snapshot. That produces the 54,595,876-satoshi discrepancy. On 28 April, the PNL-row balance still includes the amount already assigned as withdrawn on the previous day, producing the 100,120,000-satoshi discrepancy.

In a separately labelled analysis scenario, place transaction `245c7553-adb9-7071-5e6d-04b65f14a127` after the 28 April PNL. Both dates then reconcile. Combined with the precision test, all 1,380 snapshot dates are arithmetically compatible with the ledger under that scenario.

This is **not a verified date correction**. The truncated times do not determine whether 27 April was a request date, whether completion happened on 28 April, or whether an export label is wrong. The raw date remains unchanged. Evidence: [source rows](../results/accounting_audit/wallet_april_source_rows.csv), [explicit date scenario](../results/accounting_audit/wallet_date_scenario.csv).

## 3. Matching the XBTUSD reporting period

BitMEX describes daily wallet realised PNL as covering the previous day's 12:00 UTC to the labelled day's 12:00 UTC. The source export's accounting is strongly consistent with the **left-inclusive, right-exclusive** interval `[D−1 12:00, D 12:00)`. [Official PNL guide](https://support.bitmex.com/hc/en-gb/articles/6205277211037-How-do-I-manually-calculate-my-Realised-PNL).

We compared six cut hours and three posting-date offsets, using the same reconstructed events. Noon with the next-day label has by far the smallest error; competing windows are retained in [the comparison table](../results/accounting_audit/settlement_window_comparison.csv). No per-day shift was fitted.

The execution export extends beyond the last wallet reporting window:

| Logical UTC execution time | Funding execcomm, satoshis | Net account effect | Assigned reporting date |
| --- | ---: | ---: | --- |
| 2021-12-31 12:00:00 | −2,848,748 | +2,848,748 | 2022-01-01 |
| 2021-12-31 20:00:00 | +890,700 | −890,700 | 2022-01-01 |
| Total | | **+1,958,048** | Outside supplied wallet period |

These two records explain **0.01958048 BTC** of the original comparison difference. They are retained as out-of-window events rather than deleted or labelled erroneous. The January 2022 wallet was not supplied, so its actual posting is not asserted. [Boundary records](../results/accounting_audit/xbtusd_after_wallet_cutoff.csv).

## 4. Simultaneous fills and the final reversal

The remaining **0.00787186 BTC** concerns allocation between realised profit and the cost of the still-open position. At **2021-12-24 03:28:15.683307**, order `7623ce3f-8206-4be4-8ad0-b3a312832fb8` generated **76 Sell fills**, totalling **2,855,500 contracts**, at 55 price levels from USD 51,100 to USD 51,025. The preceding position was long **919,900 contracts**.

The original model closes that long using the first fills in cumulative-quantity order. The refined model first combines fills sharing **exact timestamp + order ID + direction**, then allocates the batch's recorded cost proportionally between closing and opening quantities. This is neither whole-order aggregation across time nor an arbitrary seconds-based cluster. Zero-UUID liquidation fills remain separately identified.

```text
Batch recorded execution cost:              5,592,397,211 satoshis
Cost allocated to closing by fill sequence: 1,800,804,897 satoshis
Proportional batch closing cost:
  5,592,397,211 × 919,900 / 2,855,500
  = 1,801,592,083.487620...
Rounded batch closing cost:                 1,801,592,083 satoshis
Difference:                                      787,186 satoshis
```

This moves 787,186 satoshis between realised PNL and the remaining inventory's cost. The final quantity stays **−29,080,100 contracts**. The baseline's final absolute inventory cost is **56,922,926,304 satoshis**; the refined value is **56,922,139,118 satoshis**.

The grouping rule was then applied consistently to all **941,007 XBTUSD fills**, producing **506,211 accounting batches**. It was not inserted as a one-off end correction. These batches are accounting events, not a revised count of trading decisions.

The full-period fit is strong empirical evidence for this allocation treatment. It does not establish the exchange's private implementation or prove that every same-timestamp group is a literal matching-engine transaction. Evidence: [76 source fills](../results/accounting_audit/xbtusd_final_reversal_source_fills.csv), [reconstructed batch](../results/accounting_audit/xbtusd_final_reversal_batch.csv).

## 5. Integer rounding and the remaining twelve days

The audit tracks integer satoshis, rounds proportional allocations and preserves the unallocated cost in the remaining position. It never recomputes execution value from quoted price. This matters because BitMEX changed XBTUSD's lot size from 1 to 100 contracts in June 2021, changing price-to-satoshi rounding. The official notice also described effects on open positions. Using recorded execution costs avoids imposing one historical rounding grid on all dates. [Contemporaneous technical notice](https://www.bitmex.com/blog/the-technical-details-of-our-lot-size-change-on-xbtusd-swap-and-xbt-futures).

| Model, with matching wallet window | Aggregate residual | Maximum absolute daily residual | Sum of absolute daily residuals |
| --- | ---: | ---: | ---: |
| Individual fills, floating-point proportional cost | About +787,186 sat | About 4,196,756 sat | About 15,556,205 sat |
| Timestamp/order/direction batches, floating-point cost | About −0.49 sat | About 66.94 sat | About 1,723.19 sat |
| Batches, integer nearest rounding | **0 sat** | **2 sat** | **14 sat** |
| Batches, floor rounding | 0 sat | 492 sat | 22,788 sat |

The floor model illustrates why an aggregate match is insufficient validation. Nearest half-even and half-up variants yield identical daily results in this test, so the tie-breaking convention is **not identified** by the data.

There are 1,377 actual XBTUSD posting dates. The nearest-rounding model matches **1,365 exactly**. Twelve remaining dates form six small offsetting sequences; they are listed with wallet transaction IDs and source row references in [the residual table](../results/accounting_audit/xbtusd_small_residual_days.csv). The residuals have magnitudes of one or two satoshis, a total absolute amount of fourteen satoshis, and net zero. [Associated execution source ranges](../results/accounting_audit/xbtusd_small_residual_source_ranges.csv).

Across 1,398 calendar days in the observed wallet span, 1,386 are exact. The additional 21 dates have no supplied XBTUSD PNL row and the model also yields zero. Absent rows are flagged; they are not presented as actual zero-valued wallet postings.

The twelve small daily differences remain unexplained at the exact engine-processing level. Rounding order or aggregation details are possibilities, not verified causes. They are not removed by a tolerance or assigned back to the ledger.

## 6. Exact discrepancy bridge

```text
Original discrepancy, rounded to a satoshi:   2,745,234 sat = 0.02745234 BTC
Less out-of-wallet-window funding:           1,958,048 sat = 0.01958048 BTC
Less final inventory allocation difference:    787,186 sat = 0.00787186 BTC
Refined aggregate residual:                          0 sat
```

The baseline used binary floating-point arithmetic, producing insignificant sub-satoshi numerical noise around the first line. The audit derives the integer bridge from execution cash, fees, funding and terminal inventory cost. It does not use an unexplained plug.

The refined net PNL over **all exported execution events** is **2,007.10422693 BTC**. Restricting it to the final supplied wallet cutoff gives **2,007.08464645 BTC**, exactly the wallet total. Cost conservation is checked independently against cumulative signed execution cost and terminal inventory cost.

## 7. Reproduction, code changes and limits

```text
python scripts/analyze.py
python scripts/accounting_audit.py
python -m unittest discover -s tests -v
python scripts/verify.py
```

The audit runs offline against the original account files. It checks their SHA-256 fingerprints against the baseline manifest. Audit outputs are isolated under `results/accounting_audit/`. The baseline fill-based episode files remain available for comparison; this release does not silently replace their win rates or holding-time definitions with batch-based results.

An additional serialization defect was corrected: the previous `%.10g` CSV export could lose low-order satoshi digits in balance columns represented as floating-point because they contain missing values. Default round-trip serialization now preserves them. This did **not** cause the 154 original in-memory discrepancies or the original aggregate PNL gap. A dedicated regression test covers a 73,726,973,405-satoshi nullable balance.

Tests cover reporting boundaries, cost conservation on partial closes/reversals, batch-versus-fill allocation, large-integer rounding, fee counting and CSV precision. The empirical model has been assessed on the full supplied history; it is an accounting reconstruction, not an untouched predictive validation exercise.

Open issues are now narrow: the actual processing date of one withdrawal, twelve tiny day-level XBTUSD allocation differences, and independent confirmation of batching/rounding conventions. This audit does not establish marked equity, total account returns, actual leverage or the authenticity/completeness of other accounts.
