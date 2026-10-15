#!/usr/bin/env python3
"""
Mode 3 - theme baskets.

Give a theme (a list of tickers in themes/<name>.txt). Find 4 stocks (5 with
--sizes 4,5) within it, some bought and some shorted, whose combined value swings
around a steady average: the theme's overall direction mostly cancels and you
trade the stocks drifting apart and snapping back.

    python theme.py ai_infrastructure
    python theme.py ai_infrastructure --pick NVDA,AMD,MU,ANET     # one exact basket
    python theme.py --tickers NVDA,AMD,AVGO,MU,TSM,ASML,ANET,SMH  # ad-hoc theme

Method
  GATE       every basket is fitted on the last 12 months (Box-Tiao weights, $1
             gross) and must pass a cointegration test with a 3-30 day half-life,
             be roughly balanced (net long/short <= 50% of gross), every leg >= 5%.
  RANK       survivors are ranked by their TRACK RECORD over the prior 24 months:
             each month, refit on the 12 months before it, then trade the next
             month with weights frozen. "Held up" = stayed within 3 sd and came
             back to its average. This is what separates real from lucky: a single
             12-month fit can't (tested on simulated data with a planted basket).
  CHECK      the whole procedure walk-forward over another 24 months: each month
             pick the top basket using only past data, trade it the next month.
  CHANCE     the identical procedure on random-walk prices with the theme's real
             volatilities and correlations.
Needs ~5 years of history (12-month fit + 24 + 24 months).
"""

import argparse
import json
import math
import sys
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

import hedge as core

DEFAULTS = dict(
    fit_days=252,       # ~12 months per fit (6 months is too short to tell real from luck)
    step_days=21,       # ~1 month forward test, then slide
    rec_months=24,      # track-record months used to rank baskets
    n_tests=24,         # walk-forward months used to check the procedure
    sizes="4",          # basket sizes; "4,5" is ~8x slower
    min_hl=3.0,         # faster "reversion" is mostly day-to-day noise
    max_hl=30.0,
    min_sd=0.01,        # min swing (1 sd) as a fraction of gross $
    min_leg=0.05,       # every leg at least 5% of gross
    max_net=0.5,        # |longs - shorts| at most 50% of gross, so the theme's direction mostly cancels
    entry_z=1.5,
    cost_bps=5.0,
    max_cand=3000,      # gate survivors whose track records are scored (random sample if more)
    top=5,
    sims=3,
    seed=7,
)


def read_theme(arg, tickers_opt):
    if tickers_opt:
        return "Custom", [t.strip().upper() for t in tickers_opt.split(",") if t.strip()]
    root = Path(__file__).resolve().parent / "themes"
    p = Path(arg) if Path(arg).exists() else root / f"{arg}.txt"
    if not p.exists():
        sys.exit(f"Theme '{arg}' not found. Themes: " + ", ".join(x.stem for x in root.glob("*.txt")))
    tick = []
    for line in p.read_text().splitlines():
        t = line.split("#")[0].strip().upper()
        if t and t not in tick:
            tick.append(t)
    return p.stem.replace("_", " ").title(), tick


# -------------------------------------------------------------- engine ----

def _quad(S, idx, W):
    return np.einsum("bi,bij,bj->b", W, S[idx[:, :, None], idx[:, None, :]], W)


def gate(L, cols, cfg):
    """Fit every basket of the configured sizes on window L (fit_days rows);
    keep those passing half-life, swing and a cointegration test (5% MacKinnon
    critical value for the basket size, DF regression computed in batch)."""
    from statsmodels.tsa.adfvalues import mackinnoncrit
    tab = core.Tables(np.nan_to_num(L))
    n = len(L) - 1
    out = []
    for k in [int(x) for x in str(cfg["sizes"]).split(",")]:
        if len(cols) < k:
            continue
        idx = np.array(list(combinations(cols, k)))
        nu, W, sd = core.batch_fit(tab, idx, norm="gross")
        vz, vy, cyz = _quad(tab.Szz, idx, W), _quad(tab.Syy, idx, W), _quad(tab.Syz, idx, W)
        with np.errstate(divide="ignore", invalid="ignore"):
            phi = cyz / vz
            t = (phi - 1) / np.sqrt((vy - phi * cyz) / (n * vz))
            hl = np.where((phi > 0) & (phi < 1), -math.log(2) / np.log(phi), np.inf)
        crit = mackinnoncrit(N=k, regression="c", nobs=n)[1]
        ok = np.isfinite(t) & (t <= crit) & (sd >= cfg["min_sd"]) & (hl >= cfg["min_hl"]) & (hl <= cfg["max_hl"])
        ok &= (np.abs(W).min(1) >= cfg["min_leg"]) & (np.abs(W.sum(1)) <= cfg["max_net"])   # balanced, no token legs
        keep = np.where(ok)[0]
        if len(keep) > cfg["max_cand"]:                # random sample: ranking by t favours noisy, fast baskets
            keep = np.sort(np.random.default_rng(cfg["seed"] + n).choice(keep, cfg["max_cand"], replace=False))
        out.append((k, idx[keep], W[keep], (t - crit)[keep], hl[keep]))
    return out


def month_ends(n, months, cfg):
    return [n - (months - t) * cfg["step_days"] for t in range(months)
            if n - (months - t) * cfg["step_days"] - cfg["fit_days"] >= 0]


def _trade(Lf, W, mu, sd, cfg):
    """One forward month for many baskets (frozen weights/mean/sd).
    Lf: (m, B, k) log prices starting on the last fit day."""
    z = (np.einsum("tbk,bk->tb", Lf, W) - mu) / sd
    crossed = (np.sign(z[1:]) != np.sign(z[:-1])).any(0)
    held = (np.abs(z).max(0) <= 3) & (crossed | (np.abs(z[-1]) <= 1))
    leg = np.einsum("tbk,bk->tb", np.expm1(np.diff(Lf, axis=0)), W)
    pos, p = np.zeros_like(z), np.zeros(z.shape[1])
    for t in range(len(z)):
        enter = (p == 0) * ((z[t] <= -cfg["entry_z"]).astype(float) - (z[t] >= cfg["entry_z"]).astype(float))
        p = np.where(((p == 1) & (z[t] >= 0)) | ((p == -1) & (z[t] <= 0)), 0, p + enter)
        pos[t] = p
    chg = np.abs(np.diff(np.vstack([np.zeros(z.shape[1]), pos]), axis=0))
    ret = (pos[:-1] * leg).sum(0) - chg[1:].sum(0) * cfg["cost_bps"] / 1e4
    return held, ret


def records(L, idx, cfg, months):
    """Vectorized track record of many same-size baskets over the `months`
    months ending at len(L): refit on the prior fit window, trade next month."""
    B = len(idx)
    held, n, tot = np.zeros(B), np.zeros(B), np.zeros(B)
    if B == 0:
        return held, n, tot
    for e in month_ends(len(L), months, cfg):
        f0, f1 = e - cfg["fit_days"], min(e + cfg["step_days"], len(L))
        ok = ~np.isnan(L[f0:f1][:, idx]).any(axis=(0, 2))
        if not ok.any():
            continue
        sub = idx[ok]
        _, W, _ = core.batch_fit(core.Tables(np.nan_to_num(L[f0:e])), sub, norm="gross")
        s_fit = np.einsum("tbk,bk->tb", L[f0:e][:, sub], W)
        h, r = _trade(L[e - 1:f1][:, sub], W, s_fit.mean(0), s_fit.std(0), cfg)
        held[ok] += h; n[ok] += 1; tot[ok] += r
    return held, n, tot


def candidates(L, end, cfg):
    """Gate on the fit window ending at `end`, then rank by track record using
    only data before `end`. Returns dicts sorted best first."""
    f0 = end - cfg["fit_days"]
    cols = [j for j in range(L.shape[1]) if not np.isnan(L[f0:end, j]).any()]
    out = []
    for k, idx, W, margin, hl in gate(L[f0:end], cols, cfg):
        h, n, tot = records(L[:end], idx, cfg, cfg["rec_months"])
        for r in range(len(idx)):
            if n[r] >= cfg["rec_months"] // 2:
                out.append(dict(idx=idx[r], w=W[r], hl=float(hl[r]), margin=float(margin[r]),
                                held=int(h[r]), n=int(n[r]), rate=h[r] / n[r], ret=float(tot[r])))
    out.sort(key=lambda d: (-d["rate"], -d["ret"]))
    return out


def walk_forward(L, cfg):
    """The whole procedure, out of sample: each month pick the top candidate with
    past data only, trade it the next month."""
    rec = []
    for e in month_ends(len(L), cfg["n_tests"], cfg):
        c = candidates(L, e, cfg)
        if not c:
            rec.append(dict(end=e, found=False, held=False, ret=0.0))
            continue
        b = c[0]
        f0, f1 = e - cfg["fit_days"], min(e + cfg["step_days"], len(L))
        s = L[f0:e][:, b["idx"]] @ b["w"]
        h, r = _trade(L[e - 1:f1][:, b["idx"]][:, None, :], b["w"][None], s.mean(), s.std(), cfg)
        rec.append(dict(end=e, found=True, held=bool(h[0]), ret=float(r[0]), idx=b["idx"]))
    return rec


def chance(L, cfg):
    rng = np.random.default_rng(cfg["seed"])
    cols = [j for j in range(L.shape[1]) if not np.isnan(L[:, j]).any()]
    R = np.diff(L[:, cols], axis=0)
    mu, cov = R.mean(0), np.cov(R, rowvar=False)
    vals, vecs = np.linalg.eigh(cov)
    root = vecs * np.sqrt(np.clip(vals, 0, None))
    runs = []
    for k in range(cfg["sims"]):
        Ls = np.vstack([L[:1, cols], L[:1, cols] + np.cumsum(mu + rng.standard_normal(R.shape) @ root.T, 0)])
        runs.append(walk_forward(Ls, cfg))
        print(f"  chance run {k + 1}/{cfg['sims']}", file=sys.stderr, end="\r")
    print(" " * 30, file=sys.stderr, end="\r")
    return runs


def summarize(rec):
    found = [r for r in rec if r["found"]]
    rets = np.array([r["ret"] for r in rec]) if rec else np.zeros(1)
    return dict(n=len(rec), found=len(found), held=sum(r["held"] for r in found),
                total=float(rets.sum()), pos=int((rets > 0).sum()), worst=float(rets.min()))


# -------------------------------------------------------------- report ----

def chart(dates, L, b, rec, sims, tick, cfg, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4), dpi=130, gridspec_kw=dict(width_ratios=[1.1, 1]))
    n0 = len(L) - cfg["fit_days"]
    s = L[n0:, b["idx"]] @ b["w"]
    a1.plot(dates[n0:], (s - s.mean()) / s.std(), lw=1.1, color="#3b6ea5")
    for y, ls in [(0, "-"), (cfg["entry_z"], "--"), (-cfg["entry_z"], "--")]:
        a1.axhline(y, color="#888", lw=0.8, ls=ls)
    legs = " ".join(("+" if w > 0 else "-") + tick[j] for j, w in zip(b["idx"], b["w"]))
    a1.set_title(f"Current pick, last 12 months (z-score)\n{legs}", fontsize=9)
    a1.grid(alpha=0.2)
    if rec:
        ends = [dates[min(r["end"] + cfg["step_days"] - 1, len(dates) - 1)] for r in rec]
        a2.plot(ends, np.cumsum([r["ret"] for r in rec]) * 100, lw=1.6, color="#d9822b", marker="o", ms=3,
                label="real prices")
        for i, sr in enumerate(sims):
            a2.plot(ends[: len(sr)], np.cumsum([r["ret"] for r in sr]) * 100, lw=0.9, color="#999",
                    label="random-walk prices" if i == 0 else None)
        a2.legend(fontsize=8, frameon=False)
    a2.axhline(0, color="#444", lw=0.6)
    a2.set_title("Procedure walk-forward: pick monthly, trade next month\ncumulative P&L, % of gross", fontsize=9)
    a2.grid(alpha=0.2)
    import matplotlib.dates as mdates
    for ax in (a1, a2):
        ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(ax.xaxis.get_major_locator()))
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("theme", nargs="?", default="ai_infrastructure")
    ap.add_argument("--tickers", help="comma-separated tickers instead of a theme file")
    ap.add_argument("--pick", help="evaluate one exact basket (comma-separated tickers)")
    ap.add_argument("--data", default="data/prices.csv")
    ap.add_argument("--names", default=None)
    ap.add_argument("--out", default="results")
    for k, v in DEFAULTS.items():
        ap.add_argument(f"--{k.replace('_', '-')}", type=type(v), default=v)
    args = ap.parse_args()
    cfg = {k: getattr(args, k) for k in DEFAULTS}

    title, want = read_theme(args.theme, args.tickers)
    prices = pd.read_csv(args.data, index_col=0, parse_dates=True).sort_index().ffill(limit=5)
    missing = [t for t in want if t not in prices.columns]
    tick = [t for t in want if t in prices.columns]
    span = cfg["fit_days"] + (cfg["rec_months"] + cfg["n_tests"]) * cfg["step_days"]
    prices = prices[tick].iloc[-span:]
    L, dates = np.log(prices.values), prices.index
    names = core.load_names(args.names or Path(args.data).with_name("tickers.csv"))
    nm = lambda j: names.get(tick[j], (tick[j], ""))[0][:26]
    stem = "custom" if args.tickers else Path(args.theme).stem
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)

    n = len(L)
    cols = [j for j in range(len(tick)) if not np.isnan(L[n - cfg["fit_days"]:, j]).any()]
    short = [tick[j] for j in range(len(tick)) if j not in cols]
    print(f"Theme: {title} - {len(tick)} names" + (f" (not in price data: {', '.join(missing)})" if missing else ""))
    print(f"Fit window {dates[n - cfg['fit_days']]:%b %d %Y} - {dates[-1]:%b %d %Y}: {len(cols)} names usable"
          + (f" (under 12 months of history: {', '.join(short)})" if short else "") + "\n")

    rng = np.random.default_rng(cfg["seed"])

    def reference(k):
        """Track records of all possible k-stock baskets (sampled if huge)."""
        allc = list(combinations(cols, k))
        if len(allc) > 60_000:
            allc = [allc[i] for i in rng.choice(len(allc), 60_000, replace=False)]
        h, nn, t = records(L, np.array(allc), cfg, cfg["rec_months"])
        good = nn >= cfg["rec_months"] // 2
        return h[good] / nn[good], t[good]

    if args.pick:
        legs = [t.strip().upper() for t in args.pick.split(",")]
        bad = [t for t in legs if t not in tick]
        if bad:
            sys.exit(f"Not in theme/data: {', '.join(bad)}")
        idx = np.array([tick.index(t) for t in legs])
        Lw = L[n - cfg["fit_days"]:]
        _, W, _ = core.batch_fit(core.Tables(Lw), idx[None], norm="gross")
        s = Lw[:, idx] @ W[0]
        h, nn, t = records(L, idx[None], cfg, cfg["rec_months"])
        picks = [dict(idx=idx, w=W[0], hl=core.ar1_half_life(s), held=int(h[0]), n=int(nn[0]),
                      rate=h[0] / max(1, nn[0]), ret=float(t[0]))]
        print("Evaluating your basket (no search involved, so its track record is a fair test).\n")
    else:
        c = candidates(L, n, cfg)
        if not c:
            print("No basket passed the 12-month cointegration gate (half-life 3-30 days). That's a real answer: "
                  "nothing in this theme is moving in a stable relative band right now.")
            return
        picks, seen = [], []
        for r in c:
            if any(len(set(r["idx"]) & s_) > 2 for s_ in seen):
                continue
            seen.append(set(r["idx"]))
            picks.append(r)
            if len(picks) >= cfg["top"]:
                break
        print(f"{len(c)} baskets passed the 12-month gate (sampled to {cfg['max_cand']:,} if more); ranked by their "
              f"24-month track record. Showing {len(picks)} distinct ones.\n")

    refs, rows = {}, []
    for i, b in enumerate(picks):
        k = len(b["idx"])
        if k not in refs:
            refs[k] = reference(k)
        pr, pt = refs[k]
        Lw = L[n - cfg["fit_days"]:]
        s = Lw[:, b["idx"]] @ b["w"]
        z = float((s[-1] - s.mean()) / s.std())
        head = "YOUR BASKET" if args.pick else ("TOP PICK" if i == 0 else f"Alternative {i}")
        print(f"{head}: half-life {core.fmt_hl(b['hl'])}, swing (1 sd) {s.std() * 100:.1f}% of gross")
        for j, w in sorted(zip(b["idx"], b["w"]), key=lambda x: -x[1]):
            print(f"   {'BUY  ' if w > 0 else 'SHORT'} ${abs(w) * 10000:>6,.0f}  {tick[j]:<6} {nm(j)}")
        sig = ("BUY the basket (stretched low)" if z <= -cfg["entry_z"] else
               "SELL the basket (stretched high)" if z >= cfg["entry_z"] else "wait (near its average)")
        print(f"   now: z = {z:+.2f} -> {sig}")
        print(f"   24-month record (refit monthly on prior 12 months, traded next month): held up "
              f"{b['held']}/{b['n']}, P&L summed {b['ret'] * 100:+.0f}% of gross")
        print(f"      among all {len(pr):,} possible {k}-stock baskets in the theme: held-up rate beats "
              f"{(pr < b['rate']).mean() * 100:.0f}%, P&L beats {(pt < b['ret']).mean() * 100:.0f}% "
              f"(typical basket holds up {np.median(pr) * 100:.0f}% of months)\n")
        rows.append(dict(tickers=[tick[j] for j in b["idx"]], w=np.round(b["w"], 4).tolist(), hl=b["hl"],
                         z_now=z, held=b["held"], months=b["n"], ret=b["ret"],
                         pct_held=float((pr < b["rate"]).mean() * 100), pct_ret=float((pt < b["ret"]).mean() * 100)))

    rec, sims = [], []
    if not args.pick:
        print("Procedure check: each month over the last 2 years, pick the top basket using only past data, "
              "trade it the next month:")
        rec = walk_forward(L, cfg)
        sr = summarize(rec)
        print(f"   real prices : held up {sr['held']}/{sr['found']} months, P&L summed {sr['total'] * 100:+.0f}% "
              f"of gross, {sr['pos']} positive months, worst month {sr['worst'] * 100:+.1f}%")
        if cfg["sims"] > 0:
            sims = chance(L, cfg)
            ss = [summarize(s_) for s_ in sims]
            ch = np.mean([s_["held"] / max(1, s_["found"]) for s_ in ss]) * 100
            ct = np.mean([s_["total"] for s_ in ss]) * 100
            print(f"   random walks: held up {ch:.0f}% of months, P&L summed {ct:+.0f}% (avg of {cfg['sims']} runs)")
            rh = sr["held"] / max(1, sr["found"]) * 100
            if rh >= ch + 15 and sr["total"] > 0:
                print("   -> The procedure beats luck on this theme: picks have held up more often than chance.")
            else:
                print("   -> Not clearly better than luck on this theme. Treat picks as speculative; size small.")
        print()
    else:
        print("Tip: a record well above the typical basket is the evidence you want. Picking names for an "
              "economic reason (shared customers, supply chain) and checking them here avoids the luck of "
              "searching.\n")

    chart(dates, L, picks[0], rec, sims, tick, cfg, out / f"theme_{stem}.png")
    rep = dict(theme=title, config=cfg, picks=rows, walk_forward=summarize(rec) if rec else None,
               months=[dict(end=str(dates[r["end"] - 1].date()), held=r["held"], ret=r["ret"],
                            tickers=[tick[j] for j in r["idx"]] if r["found"] else []) for r in rec])
    (out / f"theme_{stem}.json").write_text(json.dumps(rep, indent=1, default=float))
    print(f"Chart: {out / f'theme_{stem}.png'}   Full results: {out / f'theme_{stem}.json'}")


if __name__ == "__main__":
    main()
