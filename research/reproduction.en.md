# Reproduction and local research package

v0.7 · [한국어](reproduction.ko.md) · [Integrated white paper](../reports/whitepaper.en.md) · [Data dictionary](data-dictionary.en.md)

## What can be reproduced?

The reports, research code, derived tables, figures and browser application form a local review package. Exact numerical reproduction additionally requires the original five account exports and the saved market files. They are deliberately absent from the review ZIP. The private explorer SQLite index is also excluded. A package that can be read without source data is not a claim that every number can be rebuilt without those data.

The supplied account's attribution, authenticity and complete external coverage are unverified. Hashes establish file identity only. No software license or raw/derived-data redistribution permission has been selected or granted. This release prepares files for the owner's review; it does not publish them or initialise, commit or push a repository. The review bundle contains detailed derived account observations, so it is not anonymised.

## Environment

Use Python 3.11+ with the supported package ranges in [requirements.txt](../requirements.txt). In a user-managed virtual environment:

```text
python -m pip install -r requirements.txt
```

The explorer server itself uses only the Python standard library; building its index needs pandas. The browser loads local HTML/CSS/JavaScript without a CDN, frontend package installation, account integration or internet request. All charts are generated locally.

[runtime.json](runtime.json) records the environment used for the release catalog, not a universal exact dependency lock. During development, the scientific figures used Python 3.14.0, NumPy 2.3.4, pandas 2.3.3 and matplotlib 3.10.7; data analysis and validation also ran in the bundled Python environment recorded by the runner. Cross-platform floating point results are checked with stated tolerances; integer cash/quantity invariants remain exact.

## Restore inputs, then verify

Restore each file to the relative path in [input-lock.json](input-lock.json). It includes original accounts, saved reference prices, provider captures, metadata and retrieval records. Preserve filenames and bytes. Human commentary is not a numerical input. Raw source names and hashes also remain in [the account manifest](../results/manifest.json).

```text
python scripts/reproduce.py --mode preflight
python scripts/reproduce.py --mode verify
```

Preflight reports missing inputs and hash mismatches and stops before research steps. It never downloads or overwrites them. Verification runs the full unit suite and the five v0.1-v0.6 verification scripts in order, stopping on the first failure. Logs and the recorded command/exit status are written under `results/release/`. `reproduction.json` distinguishes verification of saved outputs from a full rebuild; a successful verification is not relabelled as a fresh full-pipeline reproduction.

## Rebuild from the retained snapshot

```text
python scripts/reproduce.py --mode rebuild --explorer
```

This explicit mode regenerates research outputs and figures, builds the explorer index, then runs tests and validations. It needs NumPy, pandas and matplotlib in the same Python environment. It uses no network. It replaces derived outputs, not source files. Close a running explorer before replacing its SQLite index on Windows. Allow several minutes and several GB of working space: account CSVs, reconstructed events and a roughly 0.88 GB local index dominate storage.

The dependency order is:

1. `analyze.py` and `accounting_audit.py`: baseline, immutable source manifest and refined accounting.
2. `market_analysis.py`: historical/current saved-market comparison, required by subsequent event/behaviour studies.
3. `event_study.py` and `portfolio_risk.py`: posting events, contract specifications, inventories and reference risk.
4. `research_events.py`: order identities, contract event states and holding episodes.
5. `mark_sample_analysis.py`, `intraday_behavior.py`, `flow_adjusted_returns.py`: observed monthly mark comparisons, intraday quantities and conditional returns.
6. `research_priorities.py` and `research_sensitivity.py`: adjusted behaviour, attribution, loss response and sensitivity.
7. Five figure scripts, optional `build_explorer.py`, then tests and verification.

Download helpers are separate opt-in tools. `fetch_market.py` requests the fixed original study cutoff; `fetch_portfolio_market.py` obtains reference series/specifications; `fetch_historical_marks.py` obtains the selected provider samples after `research_events.py`. Availability and upstream historical revisions can prevent retrieval of the original bytes. A new download is not automatically an exact substitute. Do not run `lock-inputs` to hide a mismatch; review and version an intentional input change as a new research snapshot.

## Run the explorer

With v0.5-v0.6 prerequisites present:

```text
python scripts/build_explorer.py
python scripts/verify_explorer.py
python scripts/serve_explorer.py
```

Open [the local explorer](http://127.0.0.1:8765). Use `--port 8766` if needed and stop the server with Ctrl+C. The server binds only to 127.0.0.1, opens SQLite read-only, accepts no write API, rejects foreign origins and arbitrary file paths, and does not provide general filesystem browsing. It is a personal research viewer, not an internet deployment service.

Choose a date and contract, then inspect boundaries, parent orders, inventory events, wallet postings, funding, monthly marks and BOD/MID/EOD return scenarios. The first four requested dates have market data but no account observations; they are not shown as zero wealth. Source buttons display **all executions of the parent order**, or the single distinct execution for a zero-ID event. A timestamp batch may therefore link to more fills than its own batch count. Pagination is 100 records. Contract prices retain each contract's quote currency; contract quantity is not a BTC amount.

The contract filter affects positions, orders, funding and event rows. Account-level metrics, wallet records, equity plots and returns remain whole-account. The monthly price-detail table shows only the most recent 200 contract-price observations for that date/filter; the complete captured file is indexed locally. Daily account equity charts have missing-value breaks and include external cash flows, so they are not investment-return charts.

English is the initial UI language; a selected Korean/English preference persists in local browser storage. Date/filter selections are encoded in the local URL. The JSON export contains the selected day, input hashes, and only the currently displayed event/source pages with total counts. It is explicitly a case snapshot, not a complete execution export. It includes account details and remains the user's local file.

## Create and verify the review bundle

After intentional code/document changes, refresh the release catalog and build the ZIP:

```text
python scripts/research_release.py catalog
python scripts/research_release.py package
```

`catalog` creates the complete CSV header inventory and hashes the review-package members. `package` refuses changed cataloged files, uses fixed ZIP member timestamps, verifies the archived member hashes and CRCs, and writes `dist/btc-legend-v0.7-review.zip`. Package digest, byte count and verification status are in `results/release/package.json`. No network or Git command is executed. Regenerate the catalog after edits; the manifest intentionally cannot hash itself.

Included: README files, code/tests, explorer assets, EN/KR documents, derived result tables, figures, source registers and input/hash manifests. Excluded: all `data/` inputs, `.git/`, SQLite files, large regenerable parent-order/event caches, local run logs and previous archives. Some detailed derived tables still contain source references and transaction identifiers. Exclusion of originals does not grant redistribution rights for derivatives. The [schema inventory](schema-inventory.json) identifies each result's header, hash, size and inclusion flag; [release manifest](release-manifest.json) is the actual member list. Links to excluded data require restoring the original local workspace and are not expected to resolve in the review ZIP alone.

## Validation scope

The new explorer has [34 data/API integrity checks](../results/explorer/validation.json). The unit suite has 44 tests, including loopback/HTTP restrictions, read-only SQLite, query parameter binding, source pagination, preflight mismatches and bundle exclusions. Browser review covers EN/KR, contract filtering, source drilldown, pagination, known missing valuation, absent account days and captured mark days. The project retains earlier validation records rather than treating those counts as external certification. Current limitations remain in the integrated white paper.
