#!/usr/bin/env python3
"""rollup.py -- toolkit v10 season roll-up writer (spec Stage 3, "Season roll-up").

  python3 rollup.py STAGE3_DIR CFG.json CHECKLISTS.json [--version v10] [--validation [in-sample]]  > rows.md

v10 rows carry mechanism_version "v10", the seven seats' weights and three more columns at the end, debt_path,
systematic_risk_class and VALIDATION (SPEC v10 T6); earlier rows read "n/a" there. Because the header gains those
columns, v10 rows are written under their own header (the first 35 columns as before); the orchestrator appends them as
a new table headed "v10 rows" in SEASON_FRAME_ROLLUP.md. --validation writes "VALIDATION" (or "VALIDATION (in-sample)")
in the VALIDATION column of every row (spec Stage 0, T6); the ticker cell stays the ticker.

v9 rows (the default) carry mechanism_version "v9" and "n/a" in ln_k, ln_j and probe (SPEC v9 N1); the header is
unchanged, so the season table stays one table. The version defaults to the one stage3.json records (v9 -> "v9",
v8 -> "v8-grad", ...); a --version that contradicts it is an error.

STAGE3_DIR holds stage3.json (from frozen_arith.py stage3). CFG.json is the Stage-3 configuration (configure.py).
CHECKLISTS.json maps token -> the critic's C1-C8 JSON (extract.py checklist). The rows are appended to
SEASON_FRAME_ROLLUP.md (durable storage) only after this ticker's Stage 6 is published (so rows record final results).
"""
import os, sys, json, math

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import frozen_arith as F


def rows(s3, cfg, chk, version="v10", validation=""):
    toks = [r["token"] for r in s3["runs"]]
    fc, fco = s3["frame_categorical"], s3["frame_continuous"]

    def cat(field, t):
        for v, d in fc.get(field, {}).items():
            if t in d["runs"]:
                return v.replace("|", "/")
        return ""

    def cont(field, t, nd=4):
        v = fco.get(field, {}).get("values", {}).get(t)
        return "" if v is None else f"{v:.{nd}f}"
    v10 = version == "v10"
    W = F.ROSTER_V10 if v10 else F.ROSTER_V8 if (version.startswith("v8") or version == "v9") else F.COMMITTEE
    v9 = version in ("v9", "v10")
    v71 = s3.get("v71") or {}
    hdr = ["ticker", "token", "dossier", "model", "mechanism_version", "business_type", "denominator_type", "gross_source (masked units)",
           "basis_period", "valuation_date", "per_share_count_date", "per_share_count_basis", "denominator_count_m",
           "declared_dps", "sum_adj", "alt_type", "risk_free", "erp", "macro_base", "guidance", "floor_type", "weights",
           "tail_term (w)", "denominator normalised (ratio)", "acq mismatches (org+ded / inc-ded / undeclared)", "at_cap seats",
           "AS_OF", "currency", "MARKET_INPUTS SHA-256", "checklist C1–C8", "headline (blind, back-scaled)",
           "log_rel_headline", "ln_k", "ln_j", "probe"] + (["debt_path", "systematic_risk_class", "VALIDATION"] if v10 else [])
    L = ["| " + " | ".join(hdr) + " |", "|" + "---|" * len(hdr)]
    mi = cfg["market_inputs"]
    for r in s3["runs"]:
        t = r["token"]
        c = chk.get(t) or {}
        cl = " ".join(f"C{i}{'✓' if (c.get(f'C{i}') or {}).get('met') else '✗'}" for i in range(1, 9)) if c else "n/a"
        w = "{" + ", ".join(f"{x.title()}: {fco.get('weights.' + x, {}).get('values', {}).get(t)}" for x in W) + "}"
        dn = (v71.get("denom") or {}).get(t) or {}
        am = (v71.get("acq_mismatch") or {}).get(t) or {}
        L.append("| " + " | ".join([
            cfg["ticker"], t, r["dossier"], cfg.get("model", "configured model"), version, cat("business_type", t), cat("denominator_type", t),
            cat("gross_source", t), cat("basis_period", t), cat("valuation_date", t), cat("per_share_count_date", t),
            cat("per_share_count_basis", t), cont("denominator_count_m", t, 2), cont("declared_denominator_per_share", t),
            cont("sum_adjustments_per_share", t), cat("alternative_denominator_type", t), str(mi.get("risk_free")),
            str(mi.get("erp")), cont("macro_base", t, 2), cat("guidance_stance", t), cat("helena_floor.floor_type", t), w,
            cont("weighted_mean_tail_term", t), f"{'yes' if dn.get('normalised') else 'no'} ({dn.get('ratio')})",
            f"{am.get('organic_with_deduction')} / {am.get('including_without_deduction')} / {am.get('undeclared')}",
            str((v71.get("at_cap") or {}).get(t)), cfg["as_of"], mi.get("currency", ""), mi.get("sha256", ""), cl,
            f"{r['headline']:.2f}", f"{s3['log_rel_headline'][t]:+.4f}"] +
            (["n/a", "n/a", "n/a"] if v9 else
             [f"{r['ln_k']:+.4f}", f"{r['ln_j']:+.4f}", str((cfg.get("probe", {}).get(r["dossier"]) or {}).get("result"))]) +
            ([cat("debt_path", t) or "n/a", cat("systematic_risk_class", t) or "n/a", validation] if v10 else [])) + " |")
    for b in s3.get("bridge", []):
        L.append("| " + " | ".join([cfg["ticker"], b["token"] + " (BRIDGE)", b["dossier"], cfg.get("model", "configured model"), version] +
                                   [""] * (len(hdr) - 10) + [f"{b['headline']:.2f}", "excluded", "0", "0",
                                                              str((cfg.get("probe", {}).get(b["dossier"]) or {}).get("result"))]) + " |")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)
    s3 = json.load(open(os.path.join(sys.argv[1], "stage3.json")))
    own = F.MECH_VERSION.get(s3.get("spec") or "v10")
    ver = sys.argv[sys.argv.index("--version") + 1] if "--version" in sys.argv else own
    if ver != own:
        sys.exit(f"--version {ver} contradicts stage3.json (spec {s3.get('spec')} -> {own})")
    val = ""
    if "--validation" in sys.argv:
        nxt = sys.argv[sys.argv.index("--validation") + 1] if sys.argv.index("--validation") + 1 < len(sys.argv) else ""
        val = "VALIDATION (in-sample)" if nxt == "in-sample" else "VALIDATION"
    print(rows(s3, json.load(open(sys.argv[2])), json.load(open(sys.argv[3])), ver, val))
