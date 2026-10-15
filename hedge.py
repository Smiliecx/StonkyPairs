#!/usr/bin/env python3
"""
Sparse mean-reverting hedge finder.

Given an ANCHOR stock you want to buy, find 3 other positions (longs or shorts,
from the whole universe) that make the combined position mean-revert, then
offer three groups of interchangeable choices: pick one from each.

    python hedge.py DELL                         # search + 3 groups + report
    python hedge.py DELL --pick MU,CRM,SPY       # evaluate one exact basket

Pipeline (history split in time order)
  TRAINING   (~4 yrs)  fit weights; score every basket by Box-Tiao predictability
                       (low = snaps back instead of trending); keep the top 300
                       that also pass half-life + cointegration checks.
  VALIDATION (1 yr)    freeze those weights; rank baskets by how well they kept
                       mean-reverting here. This is what weeds out coincidences.
  UNSEEN     (1 yr)    final exam: refit on training+validation, freeze, test.
                       Nothing in the selection ever looks at this period.
  CHANCE               the same pipeline on simulated random-walk prices with the
                       real volatilities/correlations: what does luck look like?
  TODAY                weights refit on all data, current z-score.
"""

import argparse
import json
import math
import sys
import warnings
from itertools import combinations, product
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
LN2 = math.log(2)

DEFAULTS = dict(
    years=6.0,          # history used in total
    val_days=252,       # validation window (trading days)
    test_days=252,      # unseen window (trading days)
    legs=3,             # hedge positions besides the anchor
    shortlist=120,      # candidates searched exhaustively (0 = whole universe)
    n_detail=2000,      # top training baskets carried into validation
    max_gross=3.0,      # max total hedge dollars per $1 of anchor
    min_sd=0.03,        # min spread swing (std, per $1 anchor) - cost floor
    min_hl=3.0,         # half-life range in trading days
    max_hl=60.0,
    max_p=0.05,         # cointegration test p-value (training)
    val_p=0.15,         # ADF p-value gate in validation (frozen weights)
    test_p=0.10,        # ADF p-value for "held up" on the unseen year
    entry_z=2.0,        # backtest: enter at |z| >= entry, exit at z = 0
    cost_bps=5.0,       # per leg, per trade
    group_size=5,
    sims=20,            # random-walk benchmark runs (0 = skip)
    seed=7,
)


# ------------------------------------------------------------------ data ----

def load_data(path, cfg):
    prices = pd.read_csv(path, index_col=0, parse_dates=True).sort_index()
    start = prices.index.max() - pd.DateOffset(days=int(cfg["years"] * 365.25))
    prices = prices.loc[prices.index >= start].ffill(limit=5)
    good = prices.notna().all() & (prices > 0).all()
    dropped = sorted(prices.columns[~good])
    prices = prices.loc[:, good]
    need = cfg["val_days"] + cfg["test_days"] + 500
    if len(prices) < need:
        sys.exit(f"Not enough history: {len(prices)} days, need about {need}.")
    return prices, dropped


def load_names(path):
    p = Path(path)
    if not p.exists():
        return {}
    df = pd.read_csv(p)
    return {r.ticker: (str(r.name), str(r.sector)) for r in df.itertuples()}


class Tables:
    """Lag-0 / lag-1 second moments of log prices. Any basket's Box-Tiao score
    comes from sub-blocks of these, so they are computed once per window."""

    def __init__(self, L):
        Y = L[1:] - L[1:].mean(0)
        Z = L[:-1] - L[:-1].mean(0)
        n = len(Y)
        self.Syy = Y.T @ Y / n
        self.Szz = Z.T @ Z / n
        self.Syz = Y.T @ Z / n


class Context:
    def __init__(self, L_all, dates, tickers, cfg, names=None):
        n = len(L_all)
        self.te0 = n - cfg["test_days"]               # first unseen day
        self.va0 = self.te0 - cfg["val_days"]         # first validation day
        self.L_all, self.dates = L_all, dates
        self.tickers = list(tickers)
        self.ix = {t: i for i, t in enumerate(self.tickers)}
        self.L_tr = L_all[: self.va0]
        self.L_va = L_all[self.va0 - 1: self.te0]     # each window starts on the previous day
        self.L_trva = L_all[: self.te0]
        self.L_te = L_all[self.te0 - 1:]
        self.tab_tr = Tables(self.L_tr)
        self.tab_trva = Tables(self.L_trva)
        self.names = names or {}
        r = np.diff(self.L_tr[::5], axis=0)           # weekly returns, for the shortlist
        self.wk = (r - r.mean(0)) / (r.std(0) + 1e-12)

    def span(self, which):
        a, b = {"tr": (0, self.va0), "va": (self.va0, self.te0), "te": (self.te0, len(self.L_all))}[which]
        return f"{self.dates[a]:%b %Y}-{self.dates[b - 1]:%b %Y}"


# --------------------------------------------------------------- scoring ----

def batch_fit(tab, idx, ridge=1e-6, chunk=200_000):
    """Box-Tiao fit for many small baskets at once.
    idx: (B, k) asset indices, column 0 = anchor.
    Returns nu (B,) predictability in [0, 1] (lower = more mean-reverting),
    W (B, k) weights scaled so the anchor = 1, sd (B,) spread std."""
    out_nu, out_W, out_sd = [], [], []
    k = idx.shape[1]
    eye = np.eye(k)
    for s in range(0, len(idx), chunk):
        b = idx[s:s + chunk]
        I, J = b[:, :, None], b[:, None, :]
        Syy, Szz, Syz = tab.Syy[I, J], tab.Szz[I, J], tab.Syz[I, J]
        Syy = Syy + ridge * np.einsum("bii->b", Syy)[:, None, None] / k * eye
        Szz = Szz + ridge * np.einsum("bii->b", Szz)[:, None, None] / k * eye
        M = Syz @ np.linalg.solve(Szz, np.swapaxes(Syz, 1, 2))   # predictable part
        Li = np.linalg.inv(np.linalg.cholesky(Syy))
        C = Li @ M @ np.swapaxes(Li, 1, 2)
        vals, vecs = np.linalg.eigh(0.5 * (C + np.swapaxes(C, 1, 2)))
        w = np.einsum("bji,bj->bi", Li, vecs[:, :, 0])
        with np.errstate(divide="ignore", invalid="ignore"):
            W = w / w[:, :1]
            sd = np.sqrt(np.einsum("bi,bij,bj->b", W, Syy, W))
        out_nu.append(vals[:, 0]); out_W.append(W); out_sd.append(sd)
    return np.concatenate(out_nu), np.concatenate(out_W), np.concatenate(out_sd)


def refit(tab, idx):
    _, W, _ = batch_fit(tab, np.asarray(idx)[None])
    return W[0]


def ar1_half_life(s):
    x, dx = s[:-1] - s[:-1].mean(), np.diff(s)
    b = (x @ (dx - dx.mean())) / (x @ x)
    return -LN2 / math.log1p(b) if -1 < b < 0 else float("inf")


def coint_p(s, n_vars):
    """ADF on the spread with MacKinnon cointegration p-values (accounts for the
    weights having been fitted on the same data)."""
    from statsmodels.tsa.adfvalues import mackinnonp
    from statsmodels.tsa.stattools import adfuller
    stat = adfuller(s, maxlag=1, regression="c", autolag=None)[0]
    return float(mackinnonp(stat, regression="c", N=n_vars))


def adf_p(s):
    from statsmodels.tsa.stattools import adfuller
    return float(adfuller(s, maxlag=1, regression="c", autolag=None)[1])


def fit_stats(L, idx, w):
    from statsmodels.tsa.adfvalues import mackinnonp
    from statsmodels.tsa.stattools import adfuller
    s = L[:, idx] @ w
    stat = float(adfuller(s, maxlag=1, regression="c", autolag=None)[0])
    return dict(hl=ar1_half_life(s), stat=stat, p=float(mackinnonp(stat, regression="c", N=len(idx))),
                mu=float(s.mean()), sd=float(s.std()))


def passes_fit(st, cfg):
    return cfg["min_hl"] <= st["hl"] <= cfg["max_hl"] and st["p"] <= cfg["max_p"]


def check(L, idx, w, mu, sd):
    """Frozen weights, mean and sd applied to a later window. The ADF test is
    the real arbiter: on a one-year window even a random walk shows a
    'half-life' of ~30 days, but it rarely passes ADF."""
    from statsmodels.tsa.stattools import adfuller
    s = L[:, idx] @ w
    stat, p = adfuller(s, maxlag=1, regression="c", autolag=None)[:2]
    return dict(hl=ar1_half_life(s), stat=float(stat), p=float(p),
                drift=float((s.mean() - mu) / sd), sd_ratio=float(s.std() / sd))


def val_ok(v, cfg):
    return v["p"] <= cfg["val_p"] and abs(v["drift"]) <= 2.0 and v["sd_ratio"] <= 2.5


def held_up(o, cfg):
    return o["p"] <= cfg["test_p"] and abs(o["drift"]) <= 1.5 and o["sd_ratio"] <= 2.0


def backtest(L, idx, w, mu, sd, cfg):
    """Trade a window with frozen weights/mean/sd: enter at |z| >= entry_z,
    exit when z crosses 0. Returns are on gross capital, after costs."""
    Lt = L[:, idx]
    z = (Lt @ w - mu) / sd
    leg = np.expm1(np.diff(Lt, axis=0)) @ w           # daily $ P&L per $1 anchor, long spread
    gross = float(np.abs(w).sum())
    pos, p = np.zeros(len(z)), 0
    for t in range(len(z)):
        if p == 0:
            p = 1 if z[t] <= -cfg["entry_z"] else (-1 if z[t] >= cfg["entry_z"] else 0)
        elif (p == 1 and z[t] >= 0) or (p == -1 and z[t] <= 0):
            p = 0
        pos[t] = p
    chg = np.abs(np.diff(np.concatenate([[0], pos])))
    net = (pos[:-1] * leg - chg[1:] * gross * cfg["cost_bps"] / 1e4) / gross
    eq = np.cumsum(net)
    dd = float((eq - np.maximum.accumulate(np.concatenate([[0], eq]))[1:]).min())
    sharpe = float(net.mean() / net.std() * math.sqrt(252)) if net.std() > 0 else 0.0
    entries = int(((pos != 0) & (np.concatenate([[0], pos[:-1]]) == 0)).sum())
    return dict(ret=float(eq[-1]), sharpe=sharpe, max_dd=dd, trades=entries, in_mkt=float((pos != 0).mean()))


# ---------------------------------------------------------------- search ----

def shortlist(ctx, a, cfg):
    cand = np.array([j for j in range(len(ctx.tickers)) if j != a])
    if cfg["shortlist"] <= 0 or len(cand) <= cfg["shortlist"]:
        return cand
    nu, W, _ = batch_fit(ctx.tab_tr, np.stack([np.full(len(cand), a), cand], 1))
    nu = np.where(np.isfinite(W[:, 1]) & (np.abs(W[:, 1]) <= cfg["max_gross"]), nu, np.inf)
    corr = np.abs(ctx.wk[:, cand].T @ ctx.wk[:, a]) / len(ctx.wk)
    picked = list(cand[np.argsort(nu)[: int(cfg["shortlist"] * 0.6)]])   # best pairs
    for j in cand[np.argsort(-corr)]:                                     # + strongest co-movers
        if len(picked) >= cfg["shortlist"]:
            break
        if j not in picked:
            picked.append(j)
    return np.array(picked)


def select(ctx, idx, cfg, n_detail):
    """Training fit -> top n_detail by predictability -> training checks ->
    validation gate (frozen weights) -> rank survivors by cointegration
    strength over training + validation (weights refit on that window), so a
    relationship that is consistent for 5 years beats one with a lucky year."""
    nu, W, sd = batch_fit(ctx.tab_tr, idx)
    gross = np.abs(W[:, 1:]).sum(1)
    ok = np.isfinite(nu) & np.isfinite(gross) & (gross <= cfg["max_gross"]) & (sd >= cfg["min_sd"])
    order = np.where(ok)[0][np.argsort(nu[ok])][:n_detail]
    out = []
    for r in order:
        st = fit_stats(ctx.L_tr, idx[r], W[r])
        if not passes_fit(st, cfg):
            continue
        v = check(ctx.L_va, idx[r], W[r], st["mu"], st["sd"])
        if val_ok(v, cfg):
            w2 = refit(ctx.tab_trva, idx[r])
            if np.abs(w2[1:]).sum() > cfg["max_gross"] * 1.25:
                continue
            st2 = fit_stats(ctx.L_trva, idx[r], w2)
            out.append(dict(idx=idx[r], w=W[r], nu=float(nu[r]), train=st, val=v, score=st2["stat"]))
    return sorted(out, key=lambda d: d["score"]), int(ok.sum())


def search(ctx, a, cfg):
    sl = shortlist(ctx, a, cfg)
    combos = np.array(list(combinations(sl, cfg["legs"])))
    idx = np.hstack([np.full((len(combos), 1), a), combos])
    ranked, n_ok = select(ctx, idx, cfg, cfg["n_detail"])
    return dict(shortlist=sl, n_combos=len(idx), n_ok=n_ok, ranked=ranked)


def build_groups(ctx, a, best, sl, cfg):
    """Slot j of the best basket + the best substitutes for that slot (others
    held fixed). Each substitute is assigned to the slot where it scores best."""
    legs = list(best["idx"][1:])
    cand = [j for j in sl if j not in legs]
    best_slot = {}
    for slot in range(len(legs)):
        idx = np.array([[a] + [c if i == slot else legs[i] for i in range(len(legs))] for c in cand])
        ranked, _ = select(ctx, idx, cfg, 30)
        for r in ranked:
            j = int(r["idx"][1 + slot])
            if j not in best_slot or r["score"] < best_slot[j][1]:
                best_slot[j] = (slot, r["score"])
    groups = []
    for slot, leg in enumerate(legs):
        members = sorted((sc, j) for j, (s_, sc) in best_slot.items() if s_ == slot)
        groups.append([leg] + [j for _, j in members[: cfg["group_size"] - 1]])
    return groups


def evaluate(ctx, idx, cfg):
    """Full three-stage evaluation of one basket."""
    idx = np.asarray(idx)
    w_tr = refit(ctx.tab_tr, idx)
    tr = fit_stats(ctx.L_tr, idx, w_tr)
    va = check(ctx.L_va, idx, w_tr, tr["mu"], tr["sd"])
    w_trva = refit(ctx.tab_trva, idx)                 # final-exam weights
    trva = fit_stats(ctx.L_trva, idx, w_trva)
    te = check(ctx.L_te, idx, w_trva, trva["mu"], trva["sd"])
    te["bt"] = backtest(ctx.L_te, idx, w_trva, trva["mu"], trva["sd"], cfg)
    te["held"] = held_up(te, cfg)
    return dict(idx=idx, w_tr=w_tr, train=tr, val=va, val_pass=val_ok(va, cfg),
                fit_pass=passes_fit(tr, cfg), w_trva=w_trva, trva=trva, test=te,
                gross=float(np.abs(w_tr[1:]).sum()))


def today(ctx, idx):
    w = refit(Tables(ctx.L_all), idx)
    s = ctx.L_all[:, idx] @ w
    return dict(w=w, hl=ar1_half_life(s), z=float((s[-1] - s.mean()) / s.std()))


# ------------------------------------------------------ chance benchmark ----

def chance_benchmark(ctx, a, cfg, real_score):
    """Run the identical pipeline on random walks that share the real
    volatilities and correlations (so any 'relationship' found is luck)."""
    rng = np.random.default_rng(cfg["seed"])
    R = np.diff(ctx.L_all, axis=0)
    mu, cov = R.mean(0), np.cov(R, rowvar=False)
    vals, vecs = np.linalg.eigh(cov)
    root = vecs * np.sqrt(np.clip(vals, 0, None))
    scores, held = [], []
    for k in range(cfg["sims"]):
        Rs = mu + rng.standard_normal(R.shape) @ root.T
        Ls = np.vstack([ctx.L_all[:1], ctx.L_all[:1] + np.cumsum(Rs, 0)])
        sim = Context(Ls, ctx.dates, ctx.tickers, cfg)
        res = search(sim, a, cfg)
        if res["ranked"]:
            scores.append(res["ranked"][0]["score"])
            held.append(evaluate(sim, res["ranked"][0]["idx"], cfg)["test"]["held"])
        else:
            scores.append(float("inf")); held.append(False)
        print(f"  chance run {k + 1}/{cfg['sims']}", file=sys.stderr, end="\r")
    print(" " * 30, file=sys.stderr, end="\r")
    scores = np.array(scores)
    return dict(scores=scores.tolist(), frac_as_good=float((scores <= real_score).mean()),
                n_found=int(np.isfinite(scores).sum()), held_rate=float(np.mean(held)))


# ---------------------------------------------------------------- report ----

def fmt_hl(x):
    return "none" if not math.isfinite(x) else f"{x:.0f}d"


def label(ctx, j, width=28):
    t = ctx.tickers[j]
    name, sector = ctx.names.get(t, (t, ""))
    return f"{t:<6} {name[:width]:<{width}} {sector[:22]}"


def describe(ctx, ev, title, cfg, notional=10_000):
    a = ev["idx"][0]
    td = today(ctx, ev["idx"])
    tr, va, te, bt = ev["train"], ev["val"], ev["test"], ev["test"]["bt"]
    L = [title, "-" * len(title), f"Positions per ${notional:,.0f} of {ctx.tickers[a]} (weights refit on all data):"]
    for j, w in zip(ev["idx"], td["w"]):
        L.append(f"   {'BUY  ' if w > 0 else 'SHORT'} ${abs(w) * notional:>8,.0f}  {label(ctx, j)}")
    L.append(f"Training   {ctx.span('tr')}: half-life {fmt_hl(tr['hl'])}, cointegration p={tr['p']:.3f}, "
             f"swing (1 sd) {tr['sd'] * 100:.1f}% of anchor")
    L.append(f"Validation {ctx.span('va')}: ADF p={va['p']:.3f}, half-life {fmt_hl(va['hl'])}, drift {va['drift']:+.2f} sd, "
             f"swing x{va['sd_ratio']:.2f}  -> {'ok' if ev['val_pass'] else 'FAILED'}")
    L.append(f"Unseen     {ctx.span('te')}: ADF p={te['p']:.3f}, half-life {fmt_hl(te['hl'])}, drift {te['drift']:+.2f} sd, "
             f"swing x{te['sd_ratio']:.2f}  -> {'HELD UP' if te['held'] else 'BROKE DOWN'}")
    L.append(f"   backtest: {bt['ret'] * 100:+.1f}% on gross capital, Sharpe {bt['sharpe']:.2f}, max DD "
             f"{bt['max_dd'] * 100:.1f}%, {bt['trades']} trades, in market {bt['in_mkt'] * 100:.0f}%, "
             f"{cfg['cost_bps']:.0f} bps/leg")
    z = td["z"]
    lean = ("CHEAP now - consistent with buying" if z <= -1 else
            "RICH now - the model would rather be short" if z >= 1 else
            "near its average - no strong signal for")
    L.append(f"Today: z = {z:+.2f}, basket {lean} {ctx.tickers[a]}")
    if not te["held"]:
        L.append("   (it broke down on the unseen year, so today's reading is not a reliable signal)")
    return "\n".join(L)


def chart(ctx, ev, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    idx, w = ev["idx"], ev["w_trva"]
    s = ctx.L_all[:, idx] @ w
    z = (s - ev["trva"]["mu"]) / ev["trva"]["sd"]
    d = ctx.dates
    fig, ax = plt.subplots(figsize=(11, 4.2), dpi=130)
    ax.plot(d[: ctx.va0], z[: ctx.va0], lw=1, color="#3b6ea5", label="training")
    ax.plot(d[ctx.va0 - 1: ctx.te0], z[ctx.va0 - 1: ctx.te0], lw=1, color="#6a9f58", label="validation")
    ax.plot(d[ctx.te0 - 1:], z[ctx.te0 - 1:], lw=1, color="#d9822b", label="unseen (weights frozen)")
    for y, ls in [(0, "-"), (2, "--"), (-2, "--")]:
        ax.axhline(y, color="#888", lw=0.8, ls=ls)
    for x in (ctx.va0 - 1, ctx.te0 - 1):
        ax.axvline(d[x], color="#444", lw=0.6)
    legs = "  ".join(("+" if v > 0 else "-") + f"{abs(v):.2f} {ctx.tickers[j]}" for j, v in zip(idx, w))
    ax.set_title(f"Spread z-score:  {legs}", fontsize=10)
    ax.set_ylabel("z")
    ax.legend(loc="best", fontsize=8, frameon=False)
    ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def ev_json(ctx, ev):
    return dict(tickers=[ctx.tickers[j] for j in ev["idx"]], w_train=np.round(ev["w_tr"], 4).tolist(),
                train_hl=ev["train"]["hl"], train_p=ev["train"]["p"], fit_pass=ev["fit_pass"],
                val_hl=ev["val"]["hl"], val_drift=ev["val"]["drift"], val_pass=ev["val_pass"],
                val_p=ev["val"]["p"], test_p=ev["test"]["p"], test_hl=ev["test"]["hl"], test_drift=ev["test"]["drift"], held=ev["test"]["held"],
                test_ret=ev["test"]["bt"]["ret"], test_sharpe=ev["test"]["bt"]["sharpe"])


# ------------------------------------------------------------------ main ----

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("anchor")
    ap.add_argument("--pick", help="comma-separated hedge tickers to evaluate exactly")
    ap.add_argument("--data", default="data/prices.csv")
    ap.add_argument("--names", default=None, help="tickers.csv (default: next to prices.csv)")
    ap.add_argument("--out", default="results")
    for k, v in DEFAULTS.items():
        ap.add_argument(f"--{k.replace('_', '-')}", type=type(v), default=v)
    args = ap.parse_args()
    cfg = {k: getattr(args, k) for k in DEFAULTS}

    prices, dropped = load_data(args.data, cfg)
    names = load_names(args.names or Path(args.data).with_name("tickers.csv"))
    anchor = args.anchor.upper()
    if anchor not in prices.columns:
        why = "lacks full history in the window" if anchor in dropped else "is not in the price file"
        sys.exit(f"{anchor} {why}. Add it to extra_tickers.txt (or shorten --years).")
    ctx = Context(np.log(prices.values), prices.index, prices.columns, cfg, names)
    a = ctx.ix[anchor]
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    print(f"Data: {prices.shape[1]} tickers through {prices.index[-1].date()} "
          f"({len(dropped)} skipped for short history). Training {ctx.span('tr')}, "
          f"validation {ctx.span('va')}, unseen {ctx.span('te')}.\n")

    if args.pick:
        legs = [t.strip().upper() for t in args.pick.split(",") if t.strip()]
        missing = [t for t in legs if t not in ctx.ix]
        if missing:
            sys.exit(f"Not in data: {', '.join(missing)}")
        ev = evaluate(ctx, [a] + [ctx.ix[t] for t in legs], cfg)
        print(describe(ctx, ev, f"{anchor} + {', '.join(legs)}", cfg))
        if not ev["fit_pass"]:
            print("Note: fails the training checks (half-life / cointegration).")
        chart(ctx, ev, out / f"{anchor}_{'_'.join(legs)}.png")
        return

    res = search(ctx, a, cfg)
    print(f"Searched {res['n_combos']:,} baskets (shortlist of {len(res['shortlist'])}); "
          f"{res['n_ok']:,} within size/swing limits; {len(res['ranked'])} of the top {cfg['n_detail']} "
          f"passed training checks AND kept mean-reverting in validation.\n")
    if not res["ranked"]:
        print("Nothing survived validation. That is a real answer: no reliable mean-reverting hedge for "
              f"{anchor} with these settings. Options: --max-gross 4, --max-hl 90, --shortlist 150.")
        return

    best = res["ranked"][0]
    groups = build_groups(ctx, a, best, res["shortlist"], cfg)
    grid = [evaluate(ctx, [a, *c], cfg) for c in product(*groups) if len(set(c)) == len(c)]
    good = [g for g in grid if g["fit_pass"] and g["val_pass"] and g["gross"] <= cfg["max_gross"]]
    held = [g for g in good if g["test"]["held"]]

    print(f"THREE GROUPS for {anchor}: pick one from each. {len(grid)} possible baskets; {len(good)} pass "
          f"training + validation; {len(held)} of those also held up on the unseen year.\n")
    for gi, members in enumerate(groups):
        print(f"Group {gi + 1}")
        for j in members:
            mine = [g for g in good if j in g["idx"][1:]]
            sides = [g["w_tr"][list(g["idx"]).index(j)] for g in mine]
            side = ("buy" if np.mean(sides) > 0 else "short") if sides else "-"
            hr = np.mean([g["test"]["held"] for g in mine]) * 100 if mine else 0
            rt = np.mean([g["test"]["bt"]["ret"] for g in mine]) * 100 if mine else 0
            print(f"   {label(ctx, j)}  {side:<5}  held up {hr:3.0f}%  avg unseen backtest {rt:+5.1f}%")
        print()

    best_ev = evaluate(ctx, best["idx"], cfg)
    print(describe(ctx, best_ev, "Top pick (strongest over training + validation)", cfg) + "\n")
    chart(ctx, best_ev, out / f"{anchor}_best.png")

    # Other strong baskets: the next survivors, skipping near-duplicates of ones already shown.
    shown, others = [set(best["idx"][1:])], []
    for r in res["ranked"][1:]:
        legs_r = set(r["idx"][1:])
        if any(len(legs_r & s_) >= 2 for s_ in shown):
            continue
        shown.append(legs_r)
        others.append(evaluate(ctx, r["idx"], cfg))
        if len(others) >= 7:
            break
    if others:
        print("Other strong baskets (different families), ranked by training + validation strength:")
        for ev in others:
            legs_txt = ", ".join(("+" if w > 0 else "-") + ctx.tickers[j] for j, w in zip(ev["idx"][1:], ev["w_trva"][1:]))
            te = ev["test"]
            print(f"   {legs_txt:<34} unseen: ADF p={te['p']:.2f}, drift {te['drift']:+.1f} sd -> "
                  f"{'HELD UP ' if te['held'] else 'broke   '} backtest {te['bt']['ret'] * 100:+5.1f}%")
        print()

    report = dict(anchor=anchor, config=cfg, n_combos=res["n_combos"], n_survivors=len(res["ranked"]),
                  groups=[[ctx.tickers[j] for j in g] for g in groups],
                  best=ev_json(ctx, best_ev), others=[ev_json(ctx, e) for e in others],
                  grid=[ev_json(ctx, g) for g in grid])

    if cfg["sims"] > 0:
        print(f"Chance benchmark: the same pipeline on {cfg['sims']} sets of random-walk prices...")
        cb = chance_benchmark(ctx, a, cfg, best["score"])
        report["chance"] = cb
        fin = [s for s in cb["scores"] if math.isfinite(s)]
        print(f"   Real top pick strength {best['score']:.2f} (ADF stat, more negative = stronger). Random runs "
              f"found a survivor in {cb['n_found']}/{cfg['sims']}"
              + (f", median {np.median(fin):.2f}, best {min(fin):.2f}." if fin else "."))
        print(f"   {cb['frac_as_good'] * 100:.0f}% of random runs did at least as well; "
              f"random top picks held up on the unseen year {cb['held_rate'] * 100:.0f}% of the time.")
        if cb["frac_as_good"] <= 0.10:
            print("   -> The top pick looks better than luck.")
        else:
            print("   -> Not clearly better than luck. Lean on the unseen-year results, and size small.")

    (out / f"{anchor}_report.json").write_text(json.dumps(report, indent=1, default=float))
    print(f"\nChart: {out / f'{anchor}_best.png'}   Full results: {out / f'{anchor}_report.json'}")


if __name__ == "__main__":
    main()
