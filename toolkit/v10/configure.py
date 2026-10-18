#!/usr/bin/env python3
"""configure.py -- toolkit v10 builder of the Stage-3/5 configuration (no hand assembly).

SPEC v10: "spec_version" defaults to "v10"; otherwise as v9 below.

SPEC v9: "spec_version" defaults to "v9". A v9 manifest carries k = j = 1; there is no probe and no pooled
memory test, so "probe" and "rollup" are not needed (they are still read for a v8 or earlier spec_version).
The thinness parser accepts "**Cash flow**", "**Cash flow.**" and "**Cash flow:**" (N6).

  python3 configure.py INPUT.json OUT_cfg.json

INPUT.json:
  {"ticker", "unit", "as_of", "model", "first_v7_ticker": false, "stage7": "not run", "mandate": "NONE",
   "manifest": "manifest.json" (sealed name, read with seal.py when "sealed": true) | path,
   "sealed": true,
   "run_files": {"<token>": "runs/run_<token>.md", ...},          (masked and bridge runs)
   "verifications": {"<token>": "critiques/verification_<token>.md", ...},
   "probe": {"A": "path/probe_A.md", "B": ...}, "probe_names": ["Company name", ...],
   "market_inputs": {"path", "currency"},                          (risk-free and ERP are read from the file)
   "thinness": {"A": "path/thin_A.md", "B": ...},
   "rollup": "path/SEASON_FRAME_ROLLUP.md"}                        (prior v7 / v7.1 / v8 rows for the pooled test)

thin_metrics (⟨CARD_THIN⟩): every denominator metric of the tag-screener vocabulary that ANY dossier's thinness list
names, in vocabulary order, each followed by the dossiers that name it (spec Appendix I slot rules).
"""
import os, re, sys, json, hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import checks

VOCAB = ["Cash flow", "Capex", "SBC", "Share count", "Tax", "Acquisitions"]


BOLD = re.compile(r"(?:\*\*|__)\s*([^*_\n]+?)\s*(?:\*\*|__)")
EXTRA_OK = ("growth indicators",)


def _vocab_of(label):
    """v9 N6 (review): a bold label names a vocabulary metric if, case-insensitively and ignoring trailing punctuation
    and a parenthetical, it equals that metric's name."""
    s = re.sub(r"\s*\([^)]*\)\s*", " ", label).strip().rstrip(".:;,").strip().lower()
    for v in VOCAB:
        if s == v.lower():
            return v
    return None


def thin_metrics(paths, warn=None):
    """{dossier: path} -> ["Share count (A, B)", "Tax (B)", ...] in vocabulary order (union, tagged by dossier).
    Accepts **Cash flow**, **Cash flow.**, **cash flow:**, __Tax__ and **Cash flow (FCF).**; a bold list-entry label
    that names no vocabulary metric is reported in `warn` (and printed by the CLI), never dropped silently."""
    named = {}
    for d, p in sorted(paths.items()):
        for line in open(p, encoding="utf-8").read().split("\n"):
            m = re.match(r"\s*(?:[-*+]|\d+[.)])?\s*" + BOLD.pattern, line)
            if not m:
                continue
            v = _vocab_of(m.group(1))
            if v:
                if d not in named.setdefault(v, []):
                    named[v].append(d)
            elif warn is not None and m.group(1).strip().rstrip(".:").lower() not in EXTRA_OK:
                warn.append(f"{d}: thinness entry label {m.group(1)!r} names no vocabulary metric")
    return [f"{v} ({', '.join(named[v])})" for v in VOCAB if v in named]


def prior_rows(rollup, ticker, version="v8-grad"):
    """v7 / v7.1 / v8 rows of other tickers: {ticker, dossier, ln_k, ln_j, y, probe}. BRIDGE rows are excluded.
    Masking and rescaling are unchanged across these versions, so the pooled memory test spans them (spec Stage 3)."""
    if not rollup or not os.path.exists(rollup):
        return []
    out, hdr = [], None
    for line in open(rollup, encoding="utf-8"):
        if line.startswith("| ticker |"):
            hdr = [c.strip() for c in line.strip().strip("|").split("|")]
            continue
        if not hdr or not line.startswith("| ") or line.startswith("|---"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != len(hdr):
            continue
        row = dict(zip(hdr, cells))
        if row.get("mechanism_version") not in ("v7-tail", "v7.1-tail", "v8-grad"):
            continue
        if row.get("ticker") == ticker and row.get("mechanism_version") == version:   # this execution's own rows
            continue
        if "BRIDGE" in row.get("token", ""):
            continue
        try:
            out.append(dict(ticker=row["ticker"], dossier=row["dossier"], ln_k=float(row["ln_k"]), ln_j=float(row["ln_j"]),
                            y=float(row["log_rel_headline"]), probe=row.get("probe"), version=row.get("mechanism_version")))
        except (KeyError, ValueError):
            continue
    return out


def build(inp):
    thin_warn = []
    if inp.get("sealed"):
        import seal
        man = json.loads(seal.read(inp["manifest"]))
    else:
        man = json.load(open(inp["manifest"]))
    mi_txt = open(inp["market_inputs"]["path"], encoding="utf-8").read()
    rf = float(re.search(r"\*\*Risk-free rate:\*\* ([\d.]+)%", mi_txt).group(1))
    erp = float(re.search(r"\*\*Equity risk premium:\*\* ([\d.]+)%", mi_txt).group(1))
    probe = {}
    for d, p in inp.get("probe", {}).items():
        res, conf = checks.score_probe(open(p, encoding="utf-8").read(), inp["ticker"], inp.get("probe_names", []))
        probe[d] = dict(result=res, confidence=conf)
    rf_ = inp["run_files"]
    cfg = dict(ticker=inp["ticker"], unit=inp["unit"], as_of=inp["as_of"], model=inp.get("model", "configured model"), first_v7_ticker=bool(inp.get("first_v7_ticker")),
               market_inputs=dict(path=inp["market_inputs"]["path"], sha256=hashlib.sha256(mi_txt.encode("utf-8")).hexdigest(),
                                  currency=inp["market_inputs"]["currency"], risk_free=rf, erp=erp),
               runs=[dict(token=r["token"], dossier=r["dossier"], k=r["k"], j=r["j"], run_file=rf_[r["token"]]) for r in man["runs"]],
               bridge_runs=[dict(token=r["token"], dossier=r["dossier"], run_file=rf_[r["token"]]) for r in man.get("bridge", [])
                            if r["token"] in rf_],
               probe=probe, methodology_note_fields=[],
               season_prior_v7_rows=([] if inp.get("spec_version", "v10") in ("v9", "v10") else   # v9 N1: no pooled memory test
                                     prior_rows(inp.get("rollup"), inp["ticker"],
                                                {"v8": "v8-grad", "v7.1": "v7.1-tail", "v7": "v7-tail"}[inp.get("spec_version", "v10")])),
               spec_version=inp.get("spec_version", "v10"),
               stage7=inp.get("stage7", "not run"), mandate=inp.get("mandate", "NONE"),
               verifications=inp.get("verifications", {}),
               thin_metrics=thin_metrics(inp.get("thinness", {}), thin_warn))
    cfg["thin_unmatched"] = thin_warn
    return cfg


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    cfg = build(json.load(open(sys.argv[1])))
    json.dump(cfg, open(sys.argv[2], "w"), indent=1, ensure_ascii=False)
    for w_ in cfg.get("thin_unmatched", []):
        print("WARNING " + w_)
    print(f"config written: {len(cfg['runs'])} runs, {len(cfg['bridge_runs'])} bridge, thin_metrics {cfg['thin_metrics']}, "
          f"{len(cfg['season_prior_v7_rows'])} prior season rows")
