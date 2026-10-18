#!/usr/bin/env python3
"""checks.py -- toolkit v10 hash checks, the staged FRAMEWORK check and the season file's ERP arithmetic
(spec Stage 0.5 Step 1, Stage 1, Stage 4b, Appendix J).

  python3 checks.py toolkit [DIR]                       # every file vs TOOLKIT_MANIFEST.md; prints the manifest SHA-256
  python3 checks.py file PATH NAME                      # one staged copy (e.g. a verifier's frozen_arith.py) vs the manifest
  python3 checks.py framework STAGED_FRAMEWORK          # v10 (T5): dossier/FRAMEWORK_stage.md vs the manifest's FRAMEWORK_v10.md
  python3 checks.py market STAGED SEASON [ROLLUP] [--spec v8]
        # MARKET_INPUTS: staged = season file, and = any hash in the roll-up for that AS_OF/currency. Under v9 and v10
        # (default v10) the file must be on the v9 Appendix-J template and its ERP must equal ERP_RAW + ERP_RF - RF within
        # 0.005pp (N4).
  python3 checks.py probe PROBE_OUTPUT TICKER NAME [NAME ...]   # v8 and earlier only (Stage 1d): IDENTIFIED / NOT IDENTIFIED
  python3 checks.py selftest                            # the v9 ERP check on constructed files; the v10 FRAMEWORK check
Exit 0 = pass, 1 = fail. The orchestrator appends every result to final/hash_checks.txt.
"""
import os, re, sys, hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
MANIFEST = os.path.join(HERE, "TOOLKIT_MANIFEST.md")


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def manifest_entries(path=MANIFEST):
    out = {}
    for m in re.finditer(r"^\| `([^`]+)` \| `([0-9a-f]{64})` \|$", open(path, encoding="utf-8").read(), re.M):
        out[m.group(1)] = m.group(2)
    return out


def verify_toolkit(d=HERE):
    ent = manifest_entries(os.path.join(d, "TOOLKIT_MANIFEST.md"))
    bad = [f for f, h in ent.items() if not os.path.exists(os.path.join(d, f)) or sha(os.path.join(d, f)) != h]
    return (not bad and bool(ent)), bad, sha(os.path.join(d, "TOOLKIT_MANIFEST.md"))


def verify_file(path, name):
    ent = manifest_entries()
    if name not in ent:
        return False, f"{name} not in manifest"
    h = sha(path)
    return h == ent[name], f"{h} vs manifest {ent[name]}"


FRAMEWORK_NAME = "FRAMEWORK_v10.md"   # v10 T5: FRAMEWORK ships in the toolkit and is hashed in the manifest


def verify_framework(path):
    """v10 T5: the staged FRAMEWORK copy must be byte-identical to the toolkit's FRAMEWORK_v10.md (manifest entry)."""
    return verify_file(path, FRAMEWORK_NAME)


def verify_market(staged, season, rollup=None, spec="v10"):
    hs, hseason = sha(staged), sha(season)
    why = []
    if spec in ("v9", "v10"):
        why += check_erp(open(staged, encoding="utf-8").read())
    if hs != hseason:
        why.append(f"staged {hs} != season file {hseason}")
    if rollup and os.path.exists(rollup):
        txt = open(staged, encoding="utf-8").read()
        m = re.search(r"AS_OF: (\d{4}-\d\d-\d\d)\. Currency: ([A-Z]{3})", txt)
        if m:
            for line in open(rollup, encoding="utf-8"):
                if m.group(1) in line and f"| {m.group(2)} |" in line:
                    for h in re.findall(r"\b[0-9a-f]{64}\b", line):
                        if h != hs:
                            why.append(f"roll-up row records {h} for {m.group(1)} {m.group(2)}")
    return not why, why, hs


ERP_TOL = 0.005                 # percentage points (spec Stage 0.5, v9 N4)
ERP_RANGE = (2.0, 8.0)          # a rebased ERP outside this range stops (spec Appendix J)
ERP_MAX_AGE_DAYS = 31           # the source's date may precede RF_DATE by at most this (spec Appendix J)
_N = r"([−-]?\d+(?:\.\d+)?)"


def _f(m, g=1):
    return float(m.group(g).replace("−", "-")) if m else None


def market_erp(txt):
    """v9 Appendix J: returns (rf, erp, erp_raw, erp_rf) from a MARKET_INPUTS text; erp_raw and erp_rf are None for a file
    on the v8 template (no source risk-free basis)."""
    rf = re.search(r"\*\*Risk-free rate:\*\* " + _N + "%", txt)
    erp = re.search(r"\*\*Equity risk premium:\*\* " + _N + "%", txt)
    raw = re.search(r"\*\*Equity risk premium:\*\* [−-]?[\d.]+% — the source's implied premium of " + _N + r"% \(", txt)
    erf = re.search(r"10-year government yield \(series [^)]*\) of " + _N + r"% on that date, rebased to this file's risk-free rate", txt)
    return _f(rf), _f(erp), _f(raw), _f(erf)


def check_erp(txt):
    """v9 N4: [] if the file is on the v9 template, its printed equation repeats its stated figures, ERP = ERP_RAW +
    ERP_RF - RF within ERP_TOL, the ERP lies in ERP_RANGE, the source is in the file's currency and dated at most
    ERP_MAX_AGE_DAYS before RF_DATE; else the reasons."""
    import datetime
    rf, erp, raw, erf = market_erp(txt)
    if rf is None or erp is None:
        return ["risk-free rate or equity risk premium not found"]
    if raw is None or erf is None:
        return ["file is not on the v9 Appendix-J template (no source ERP and its risk-free basis): a v9 execution "
                "ignores it (spec Rule O-2, 'v9 files')"]
    why = []
    if abs(erp - (raw + erf - rf)) > ERP_TOL + 1e-12:
        why.append(f"ERP {erp} != ERP_RAW {raw} + ERP_RF {erf} - RF {rf} = {raw + erf - rf:.4f} (tolerance {ERP_TOL}pp)")
    eq = re.search(r"rebased to this file's risk-free rate: " + _N + r" \+ " + _N + " − " + _N + " = " + _N + r"\.", txt)
    if not eq:
        why.append("the printed equation ERP_RAW + ERP_RF − RF = ERP is missing")
    elif any(abs(_f(eq, g) - v) > 1e-9 for g, v in ((1, raw), (2, erf), (3, rf), (4, erp))):
        why.append("the printed equation's figures differ from the stated ERP_RAW, ERP_RF, RF or ERP")
    if not (ERP_RANGE[0] <= erp <= ERP_RANGE[1]):
        why.append(f"rebased ERP {erp} outside {ERP_RANGE[0]}-{ERP_RANGE[1]}%: ask the spec owner")
    s1 = re.search(r"10-year government bond yield in [A-Z]{3}, series ([^,]+),", txt)
    s2 = re.search(r"10-year government yield \(series ([^)]*)\) of ", txt)
    if not (s1 and s2 and s1.group(1).strip() == s2.group(1).strip()):
        why.append("the source premium's risk-free series (ERP_RF_SERIES) is not the file's own series (SERIES): "
                   "a cross-currency or cross-tenor rebase is not allowed")
    d_rf = re.search(r"observed at the close of (\d{4}-\d\d-\d\d)", txt)
    d_erp = re.search(r"the source's implied premium of [−-]?[\d.]+% \(source .*?, dated (\d{4}-\d\d-\d\d),", txt)
    if not (d_rf and d_erp):
        why.append("RF_DATE or ERP_DATE not found")
    else:
        gap = (datetime.date.fromisoformat(d_rf.group(1)) - datetime.date.fromisoformat(d_erp.group(1))).days
        if gap < 0 or gap > ERP_MAX_AGE_DAYS:
            why.append(f"ERP_DATE is {gap} days before RF_DATE (allowed 0-{ERP_MAX_AGE_DAYS})")
    return why


def score_probe(text, ticker, names, generic=()):
    """Mechanical scoring (spec Stage 1d): IDENTIFIED if item 1 of the answer names the ticker or a company name.
    Names match on word boundaries; names that are also ordinary words (`generic`) match case-sensitively only."""
    head = re.split(r"(?m)^\s*2[.)]", text, maxsplit=1)[0]
    hit = re.search(r"(?<![A-Za-z])" + re.escape(ticker) + r"(?![A-Za-z])", head)
    for n in names:
        flags = 0 if n in generic else re.I
        if re.search(r"(?<![\w])" + re.escape(n) + r"(?![\w])", head, flags):
            hit = True
    conf = re.search(r"confidence[^\d\n]{0,30}(\d{1,3})\s*%", head, re.I) or re.search(r"(\d{1,3})\s*%", head)
    return ("IDENTIFIED" if hit else "NOT IDENTIFIED"), (conf.group(1) + "%" if conf else "not stated")


def selftest():
    import tempfile
    sys.path.insert(0, HERE)
    import tpl

    def mk(**kw):
        sl = dict(AS_OF="2026-10-10", CURRENCY="USD", RF="4.95", SERIES="DGS10", RF_DATE="2026-10-09", ERP="3.89",
                  ERP_RAW="4.09", ERP_RF="4.75", ERP_RF_SERIES="DGS10", ERP_SOURCE="Damodaran implied ERP", ERP_DATE="2026-10-01",
                  ERP_CONVENTION="implied, trailing-12-month cash yield")
        sl.update(kw)
        return tpl.instantiate("J", sl)
    v8 = ("# MARKET INPUTS\nAS_OF: 2026-09-10. Currency: USD.\n\n- **Risk-free rate:** 4.95% — x.\n"
          "- **Equity risk premium:** 4.09% — source X, dated 2026-09-01, convention y as the source states it.\n")
    good = mk()
    tamper = good.replace("4.09 + 4.75 − 4.95 = 3.89.", "4.29 + 4.75 − 4.95 = 4.09.")
    cases = [("K1 the spec's Appendix J filled with 4.09 + 4.75 − 4.95 = 3.89 passes", check_erp(good) == []),
             ("K2 an un-rebased ERP (4.09) fails", bool(check_erp(mk(ERP="4.09")))),
             ("K3 a printed equation that contradicts the stated figures fails", bool(check_erp(tamper))),
             ("K4 a rebased ERP outside 2-8% fails (EUR negative-rate case reads its sign)",
              bool(check_erp(mk(RF="13.00", ERP="-4.16"))) and market_erp(mk(RF="-0.20", ERP="9.04"))[0] == -0.2),
             ("K5 a source dated more than 31 days before RF_DATE fails", bool(check_erp(mk(ERP_DATE="2026-08-31")))),
             ("K6 the regexes read rf 4.95, erp 3.89, raw 4.09, basis 4.75", market_erp(good) == (4.95, 3.89, 4.09, 4.75)),
             ("K8 a source premium measured on another series (an EUR file rebased on a US Treasury basis) fails, even "
              "inside 2-8%", bool(check_erp(mk(CURRENCY="EUR", SERIES="IRLTLT01DEM156N", RF="2.60", ERP="6.24",
                                                ERP_RF_SERIES="DGS10"))))]
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "mi.md")
        open(p, "w", encoding="utf-8").write(good)
        okm, _, _ = verify_market(p, p)
        open(p, "w", encoding="utf-8").write(v8)
        okv8, _, _ = verify_market(p, p)
        okv8c, _, _ = verify_market(p, p, spec="v8")
    cases.append(("K7 verify_market passes the v9 file; a v8-template file fails under v9 and v10 and passes in --spec v8 mode",
                  okm and not okv8 and okv8c))
    with tempfile.TemporaryDirectory() as td:
        fw = os.path.join(HERE, FRAMEWORK_NAME)
        cp, ed = os.path.join(td, "FRAMEWORK_stage.md"), os.path.join(td, "edited.md")
        txt = open(fw, "rb").read()
        open(cp, "wb").write(txt)
        open(ed, "wb").write(txt.replace(b"Rule 2", b"Rule 2 ", 1))
        ok_c, _ = verify_framework(cp)
        ok_e, _ = verify_framework(ed)
        has_rule10 = b"Regional same-store sales growth falls below 0% for two consecutive quarters" in txt
    cases.append(("K9 v10: a verbatim FRAMEWORK copy matches the manifest; a one-byte edit fails; the copy carries the "
                  "neutral Rule-10 example", ok_c and not ok_e and has_rule10))
    ok = all(c for _, c in cases)
    print("\n".join(f"{'PASS' if c else 'FAIL'}  {n}" for n, c in cases))
    print("CHECKS SELF-TEST " + ("PASSED" if ok else "FAILED"))
    return ok


if __name__ == "__main__":
    a = sys.argv
    if len(a) >= 2 and a[1] == "toolkit":
        ok, bad, h = verify_toolkit(a[2] if len(a) > 2 else HERE)
        print(f"toolkit manifest SHA-256 {h}; {'MATCH' if ok else 'MISMATCH ' + ', '.join(bad)}")
        sys.exit(0 if ok else 1)
    if len(a) >= 4 and a[1] == "file":
        ok, why = verify_file(a[2], a[3])
        print(f"{a[3]} staged copy: {'MATCH' if ok else 'MISMATCH'} ({why})")
        sys.exit(0 if ok else 1)
    if len(a) >= 3 and a[1] == "framework":
        ok, why = verify_framework(a[2])
        print(f"FRAMEWORK staged copy {a[2]}: {'MATCH' if ok else 'MISMATCH'} ({why})")
        sys.exit(0 if ok else 1)
    if len(a) >= 4 and a[1] == "market":
        spec = a[a.index("--spec") + 1] if "--spec" in a else "v10"
        pos = [x for i, x in enumerate(a) if x != "--spec" and (i == 0 or a[i - 1] != "--spec")]
        ok, why, h = verify_market(pos[2], pos[3], pos[4] if len(pos) > 4 else None, spec)
        print(f"MARKET_INPUTS {h}: {'PASS' if ok else 'FAIL ' + '; '.join(why)}")
        sys.exit(0 if ok else 1)
    if len(a) >= 2 and a[1] == "selftest":
        sys.exit(0 if selftest() else 1)
    if len(a) >= 5 and a[1] == "probe":
        res, conf = score_probe(open(a[2], encoding="utf-8").read(), a[3], a[4:])
        print(f"{res} ({conf})")
        sys.exit(0)
    print(__doc__)
