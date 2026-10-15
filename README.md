# StonkyPairs

Three tools for building small long/short baskets from the S&P 500 plus ~50 ETFs:

| Mode | Script | You give it | It finds | Question it answers |
|---|---|---|---|---|
| 1. Mean-reverting hedge | `hedge.py` | a stock you want to buy | 3 positions that make the combined position snap back to an average | "What can I pair this with to trade the swings?" |
| 2. Protection | `protect.py` | a stock you own | 3 positions that cut its risk the most | "What cushions this if it drops?" |
| 3. Theme baskets | `theme.py` | a theme (list of tickers) | 4 stocks within it, balanced long/short, that swing around an average | "Inside this theme, what moves in a stable relative band?" |

Every mode judges itself on data it never saw, and modes 1 and 3 also run the same procedure
on random-walk prices so you can see what luck alone produces.

## Quick start

```bash
pip install -r requirements.txt
git clone --branch data --depth 1 https://github.com/Smiliecx/StonkyPairs.git data   # latest prices

python hedge.py DELL                                  # mode 1 (~1.5 min)
python protect.py DELL                                # mode 2 (seconds)
python theme.py ai_infrastructure                     # mode 3 (~2 min)

python hedge.py DELL --pick MU,CRM,SPY                # evaluate an exact basket in any mode
python protect.py DELL --pick NTAP,HPE,ANET
python theme.py ai_infrastructure --pick SMH,ASML,MU,STX
python theme.py --tickers NVDA,AMD,AVGO,MU,TSM,ASML,ANET,SMH    # ad-hoc theme
```

Each run prints a report and writes a chart (`results/*.png`) and full results (`results/*.json`).

## Mode 1: mean-reverting hedge (`hedge.py`)

The anchor is fixed as the long. Every 3-stock completion from a 120-name shortlist (~280k
baskets, longs or shorts) is scored, and history is split in time order:

| Stage | Window | What happens |
|---|---|---|
| Training | first ~4 years | Box-Tiao predictability scores every basket; the best 2,000 must pass half-life (3–60 days) and cointegration checks. |
| Validation | next year | Weights frozen; must still pass a stationarity test (ADF) without drifting. Survivors ranked by strength over training + validation. |
| Unseen | last year | Weights refit on training + validation, then frozen. "Held up" = still stationary (ADF p ≤ 0.10), drift ≤ 1.5 sd, swing not more than doubled. Simple backtest: enter at ±2 sd, exit at the mean, 5 bps per leg. |
| Chance | — | Same pipeline on random-walk prices with the real volatilities and correlations. |
| Today | all data | Weights refit on everything; current z-score. |

Output: three groups of interchangeable picks (one from each), every combination evaluated,
plus other strong baskets from different families.

## Mode 2: protection (`protect.py`)

No mean-reversion requirement: the goal is that the hedges move to offset the anchor.
Hedge sizes come from regressing the anchor's daily returns on the hedges' returns.

| Stage | Window | What happens |
|---|---|---|
| Training | 2 years | Every 3-leg hedge from a 150-name shortlist (~550k) is sized and scored by volatility removed. |
| Validation | 6 months | Sizes frozen. Ranked by the weaker of training and validation, so a hedge must work in both. |
| Unseen | last 6 months | Sizes refit on training + validation, frozen. Volatility removed, drawdown, and how much of the anchor's worst days the hedge absorbed. Compared with just shorting SPY and with the best single hedge. |
| Today | last 2.5 years | Current sizes. |

A hedge removes upside as well as downside: in a big rally the hedged position makes much
less than the stock alone.

## Mode 3: theme baskets (`theme.py`)

Themes live in `themes/<name>.txt` (one ticker per line). `ai_infrastructure.txt` has 37
names across chips, equipment, memory, servers, networking, power and data centers.

| Stage | What happens |
|---|---|
| Gate | Every 4-stock basket is fitted on the last 12 months ($1 gross) and must pass a cointegration test with a 3–30 day half-life, be roughly balanced (net long/short ≤ 50% of gross) and have no leg under 5%. |
| Rank | Survivors ranked by their **24-month track record**: each month, refit on the prior 12 months, trade the next month with weights frozen. "Held up" = stayed within 3 sd and came back to its average. Each basket is also placed as a percentile among all possible baskets in the theme. |
| Check | The whole procedure walk-forward over another 24 months: each month pick the top basket using only past data, trade it the next month. |
| Chance | The identical procedure on random-walk prices. |

**What testing showed:** with 6-month fits, even a genuinely mean-reverting basket was
indistinguishable from luck, so fits use 12 months (refit monthly). Track records separate
real from fake well for a basket **you name** (`--pick`): a planted basket scored in the top
1%, unrelated names mid-pack. When the tool **searches** thousands of baskets, the best
coincidences reach similar records by luck, so treat search results as ideas and trust the
procedure check and chance comparison. Best use: pick names for an economic reason, then
check them with `--pick`.

## Data

`download_prices.py` pulls ~6 years of daily, dividend-adjusted closes from Yahoo Finance
(free, via `yfinance`) for the S&P 500 (list from Wikipedia), the ETFs listed in the script,
and anything in `extra_tickers.txt`. A GitHub Actions workflow
(`.github/workflows/update-prices.yml`) runs it every Saturday and force-pushes the result to
the `data` branch as a single commit. Run it any time from **Actions → Update prices → Run
workflow**. To add a stock outside the S&P 500, add it to `extra_tickers.txt`.

## Tests

`python tests/run_synthetic.py` builds a simulated market with known answers and checks that:
mode 1 finds a planted relationship that holds up, flags one that breaks in the final year,
and shows no false confidence when nothing is there; mode 2 hedges a planted target with the
right names; mode 3 ranks a planted basket's track record in the top 10% and unrelated names
below it.

## Read results with care

- **Luck is the main enemy.** Searching hundreds of thousands of baskets always finds some
  that look great. Trust the unseen-period results and the chance comparisons.
- **Short-window backtests are noisy.** A month or a year contains few trades; weight the
  "held up" verdicts over P&L.
- **Survivorship bias.** The universe is today's S&P 500 and today's theme lists.
- **Weights are in log-price terms** (roughly constant dollars per leg) and need periodic
  rebalancing.
- Costs ignore short-borrow fees and slippage beyond the per-leg estimate.
- Not investment advice.
