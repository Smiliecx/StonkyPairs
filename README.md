# sparse-hedge

Find mean-reverting hedge baskets around a stock you want to buy.

You name an **anchor** (e.g. `DELL`). The tool searches the S&P 500 plus ~50 ETFs for
3 other positions, longs or shorts, that make the combined position snap back to an average
instead of trending. It returns **three groups** of interchangeable picks (choose one from
each), position sizes, and an honest record of whether that kind of basket held up on data it
never saw.

## How it works

History is split in time order:

| Stage | Window | What happens |
|---|---|---|
| Training | first ~4 years | Every 3-stock completion of the anchor (from a 120-name shortlist, ~280k baskets) is scored by Box-Tiao predictability. The best 2,000 must also pass half-life (3–60 days) and cointegration checks. |
| Validation | next 1 year | Weights frozen. Baskets must still pass a stationarity test (ADF) without drifting. This weeds out most coincidences. Survivors are ranked by strength over training + validation. |
| Unseen | last 1 year | Final exam. Weights refit on training + validation, then frozen. Nothing in the selection looks at this year. A basket "held up" if the spread is still stationary (ADF p ≤ 0.10), hasn't drifted more than 1.5 sd, and its swing hasn't more than doubled. Includes a simple backtest (enter at ±2 sd, exit at the mean, 5 bps per leg). |
| Chance | — | The identical pipeline run on random-walk prices with the real volatilities and correlations, so you can see what luck alone produces. |
| Today | all data | Weights refit on everything; current z-score of the spread. |

Scores for any basket come from three small precomputed tables per window (same-day and
one-day-lagged co-movement of log prices), so ~280k baskets are scored in seconds.

The groups: slot *j* of the best basket plus its best substitutes for that role. You can
pick any combination; every combination is evaluated, and each name shows how often its
baskets held up on the unseen year. The report also lists other strong baskets from
different families.

## Usage

```bash
pip install -r requirements.txt
git clone --branch data --depth 1 https://github.com/<owner>/<repo>.git data   # latest prices

python hedge.py DELL                      # search, groups, report (~1.5 min)
python hedge.py DELL --pick MU,CRM,SPY    # evaluate one exact basket (seconds)
python hedge.py DELL --sims 0             # skip the chance benchmark (faster)
```

Output: a text report, `results/<ANCHOR>_best.png` (spread z-score across the three
windows), and `results/<ANCHOR>_report.json` (every basket evaluated).

Useful options: `--max-gross 3` (max hedge dollars per $1 of anchor), `--max-hl 60`,
`--shortlist 120` (0 = whole universe, slow), `--cost-bps 5`, `--entry-z 2`, `--years 6`.

## Data

`download_prices.py` pulls ~6 years of daily, dividend-adjusted closes from Yahoo Finance
(free, via `yfinance`) for the S&P 500 (list from Wikipedia), the ETFs listed in the script,
and anything in `extra_tickers.txt`. A GitHub Actions workflow
(`.github/workflows/update-prices.yml`) runs it every Saturday and force-pushes the result
to the `data` branch as a single commit, so history doesn't grow. Run it any time from the
repo's **Actions** tab → *Update prices* → *Run workflow*.

To add a stock outside the S&P 500, add its ticker to `extra_tickers.txt`.

## Tests

`python tests/run_synthetic.py` builds a simulated market with known answers and checks
that the tool (1) finds a planted relationship that holds up, (2) flags a planted
relationship that breaks in the final year, and (3) doesn't report false confidence when
nothing is there.

## Read results with care

- **Luck is the main enemy.** Searching ~280k baskets always finds some that look great in
  training. Trust the unseen-year results and the chance benchmark, not the training fit.
- **Unseen-year backtests are noisy.** One year usually contains only a few trades, and
  baskets that broke down can still show a profit. Weight the "held up" verdict and ADF
  p-value over backtest P&L.
- **Survivorship bias.** The universe is today's S&P 500, so companies that were removed
  or failed are missing from the history.
- **Weights are in log-price terms,** meaning roughly constant dollar amounts per leg;
  they drift as prices move and need periodic rebalancing.
- Costs ignore short-borrow fees and slippage beyond the per-leg estimate.
- Not investment advice.
