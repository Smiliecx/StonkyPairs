#!/usr/bin/env python3
"""stage1.py -- toolkit v9 driver for Stage 1 (redaction check, redactions, methodology notes) and Stage 1c (packs).

SPEC v9 (N1): masking and rescaling are off by default. With "masking": false (the default) each run's pack is
the redacted dossier as written (company names and figures unchanged), k = j = 1, and there is no completeness,
masking or consistency check. The tag screener's JSON then needs only its SHARES tags, which the redaction check
uses to refuse any redaction that touches a share count. "masking": true keeps the v8 path (factor draws,
rescaling, identity masking, completeness / masking / consistency checks) for replays of earlier executions.

  python3 stage1.py run CONFIG.json      # exit 0 = packs written; exit 2 = STOP (report says which screener to relaunch)
  python3 stage1.py selftest

CONFIG.json:
  {"ticker": "XYZ", "ticker_forms": ["XYZ", "Xyz"], "masking": false,
   "dossiers": {"A": {"raw": "path/raw_A.md", "name": "pack_h4.md", "tags_json": "path/tags_A.json"}, "B": {...}},
   "redaction_json": "path/redaction.json",
   "runs":   [{"token": "u7", "dossier": "A", "pack": "pack_k3.md"}, ...],
   "bridge": [{"token": "j6", "dossier": "A", "pack": "pack_m2.md"}],          (first v7 ticker only)
   "out": {"sealed": true} | {"dir": "path"},
   "final_dir": "path/final"}

Raw dossiers, screener outputs, packs, redlogs, the manifest (k, j) and the REDACTION_LOG are orchestrator-only:
with "sealed": true they are written only to the sealed store (seal.py; passphrase in env PP).
final/redaction_check.md holds counts, statuses and reasons only, never a redacted span.
"""
import os, sys, json, re

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import stage1c as C


def strip(t):
    return t.replace(C.S0, "").replace(C.S1, "")


def replacements(t):
    out = []
    for i, line in enumerate(t.split("\n"), start=1):
        for m in re.finditer(re.escape(C.S0) + "(.*?)" + re.escape(C.S1), line):
            out.append((i, m.group(1)))
    return out


class Out:
    def __init__(self, spec):
        self.sealed = bool(spec.get("sealed"))
        self.dir = spec.get("dir")
        if self.sealed:
            import seal
            self.seal = seal
        else:
            os.makedirs(self.dir, exist_ok=True)

    def write(self, name, text):
        if self.sealed:
            self.seal.write(name, text)
        else:
            open(os.path.join(self.dir, name), "w", encoding="utf-8").write(text)


# v9 keep-list backstop (review and closing check). A share-count line is a line that names shares ("shares", "share
# count") and carries a count-like number: a number that is not a currency amount (no currency symbol or ISO code before
# it, no ISO code after it), not a percentage and not a bare year, and that has thousands separators, a scale word or at
# least four digits. Both orders count: "5 million shares" and "diluted shares: FY2021 49,802,993".
SHARE_WORD = re.compile(r"\bshares\b|\bshare count\b", re.I)
NUM_TOKEN = re.compile(r"(?<![\w.,])(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)(\s*(?:million|billion|thousand|mn|bn|m|k)\b)?", re.I)
CUR_BEFORE = re.compile(r"(?:[$€£¥]|R\$|Ps\.|\b[A-Z]{3})\s?$")
CUR_AFTER = re.compile(r"^\s?(?:[A-Z]{3}\b|%)")


# Re-check R2-1: a currency unit anywhere on the line ("(US$ mn)", "USD", "R$") makes its numbers amounts, unless a
# number sits right next to "shares". R2-2: a share label with a count unit ("Diluted shares (m)") makes any number on
# the line count-like.
CUR_ANY = re.compile(r"US\$|R\$|[$€£¥]|\bPs\.|\b(?:USD|EUR|GBP|BRL|MXN|ARS|CLP|COP|PEN|UYU|CAD|AUD|NZD|CHF|JPY|CNY|"
                     r"HKD|SGD|INR|KRW|TWD|SEK|NOK|DKK|PLN|ZAR|ILS|TRY)\b")
SHARE_UNIT = re.compile(r"shares?\b[^|\n]{0,30}?\((?:m|mn|mm|millions?|bn|billions?|thousands?|000s?|'000s?)\)", re.I)
ADJ_SHARES = re.compile(r"\s*(?:[\w-]+\s+){0,2}?shares\b", re.I)


def count_numbers(text, line=None):
    """Count-like numbers in `text` (see above); `line` (default `text`) gives the context. Returns their strings."""
    ctx = text if line is None else line
    cur_line, unit_line = bool(CUR_ANY.search(ctx)), bool(SHARE_UNIT.search(ctx))
    out = []
    for m in NUM_TOKEN.finditer(text):
        num_, scale = m.group(1), m.group(2)
        if CUR_BEFORE.search(text[max(0, m.start() - 4):m.start()]) or CUR_AFTER.match(text[m.end():m.end() + 4]):
            continue
        digits = num_.replace(",", "").split(".")[0]
        if not scale and "," not in num_ and len(digits) == 4 and 1900 <= int(digits) <= 2100:
            continue   # a year
        if cur_line and not ADJ_SHARES.match(text[m.end():m.end() + 40]):
            continue   # an amount on a line stated in a currency unit
        if scale or "," in num_ or len(digits) >= 4 or (unit_line and not cur_line):
            out.append(num_)
    return out


def share_count_lines(text, exempt=()):
    """1-based line numbers that state share counts (lines in `exempt` are skipped)."""
    return [i + 1 for i, ln in enumerate(text.split("\n"))
            if (i + 1) not in exempt and SHARE_WORD.search(ln) and count_numbers(ln)]


def exemptions(tag_json):
    """The tag screener's logged list of lines that name shares but state no share count: {line: reason}."""
    out = {}
    for e in (tag_json or {}).get("not_share_counts", []) if isinstance(tag_json, dict) else []:
        try:
            if isinstance(e, dict) and str(e.get("reason", "")).strip():
                out[int(e["line"])] = str(e["reason"]).strip()
        except (KeyError, TypeError, ValueError):
            continue
    return out


class _ShareRx:   # kept for the self-test's name; a span "contains a share count" if it holds a count-like number on a share line
    @staticmethod
    def search(span, line=None):
        return bool(count_numbers(span, line)) and bool(SHARE_WORD.search(line if line is not None else span))


SHARECOUNT_RX = _ShareRx()


def tag_json_problems(tag_json, raw_text):
    """v9 (masking off): the SHARES list is the keep-list's only input, so a malformed or empty list stops Stage 1."""
    if not isinstance(tag_json, dict) or not isinstance(tag_json.get("tags"), list):
        return ["tag JSON has no \"tags\" list"]
    lines, why, n_shares, tagged_lines = raw_text.split("\n"), [], 0, set()
    for i, t in enumerate(tag_json["tags"]):
        if not isinstance(t, dict) or "line" not in t or "span" not in t:
            why.append(f"tag {i} lacks line or span")   # also stops tags_from_json crashing on it
            continue
        try:
            ln = int(t["line"])
        except (TypeError, ValueError):
            why.append(f"tag {i} has a non-numeric line")
            continue
        if str(t.get("tag", "")).strip().upper() not in ("SHARES", "SH"):
            continue   # v9 uses only the SHARES tags; other tags (an earlier template's) are ignored, never checked
        n_shares += 1
        tagged_lines.add(ln)
        if not str(t["span"]).strip():
            why.append(f"SHARES tag {i} has an empty span")
        elif not (1 <= ln <= len(lines)) or str(t["span"]) not in lines[ln - 1]:
            why.append(f"SHARES tag {i} span {str(t['span'])[:40]!r} not found on line {t['line']}")
    missed = [ln for ln in share_count_lines(raw_text, exemptions(tag_json)) if ln not in tagged_lines]
    if missed:
        why.append(f"share-count line(s) with no SHARES tag: {missed[:12]}")
    return why


def run(cfg, draws=None):
    """Returns (ok, report). `draws` (optional, tests only): {dossier: (ks, js)}."""
    out = Out(cfg["out"])
    names = {d: v["name"] for d, v in cfg["dossiers"].items()}
    raw = {d: open(v["raw"], encoding="utf-8").read() for d, v in cfg["dossiers"].items()}
    tagj = {d: json.load(open(v["tags_json"], encoding="utf-8")) for d, v in cfg["dossiers"].items()}
    redj = json.load(open(cfg["redaction_json"], encoding="utf-8"))
    masking = bool(cfg.get("masking", False))
    if not masking:   # v9: validate the SHARES lists before anything uses them (fail closed)
        tp = {d: tag_json_problems(tagj[d], raw[d]) for d in raw}
        if any(tp.values()):
            report = dict(tag_lists={d: v for d, v in tp.items() if v})
            report["stop"] = [f"{d}: {'; '.join(v)}: relaunch the tag screener for this dossier (same template)"
                              for d, v in tp.items() if v]
            return False, report
    tags = {d: C.tags_from_json(tagj[d]) for d in raw}
    rc = C.redaction_check(redj, {names[d]: raw[d] for d in raw}, {names[d]: tags[d] for d in raw})
    if not masking:   # v9 backstop: refuse any accepted span that contains a share count, tagged or not
        by_name = {names[d]: raw[d].split("\n") for d in raw}
        exempt = {names[d]: exemptions(tagj[d]) for d in raw}

        def _ln(e):
            try:
                return int(e.get("line", 0))
            except (TypeError, ValueError):
                return 0

        def line_of(e):
            ls = by_name.get(e.get("dossier"), [])
            try:
                return ls[int(e.get("line", 0)) - 1]
            except (ValueError, IndexError):
                return ""
        for nm in list(rc["accepted"]):
            keep_ = []
            for e in rc["accepted"][nm]:
                if _ln(e) not in exempt.get(nm, {}) and SHARECOUNT_RX.search(str(e.get("span", "")), line_of(e)):
                    rc["rejected"].append(dict(e, reason="keep-list violation (v9 backstop): span contains a share count"))
                    rc["stop"] = True
                else:
                    keep_.append(e)
            rc["accepted"][nm] = keep_
        for nt in redj.get("methodology_notes", []):
            if _ln(nt) not in exempt.get(nt.get("dossier"), {}) and SHARECOUNT_RX.search(str(nt.get("span", "")), line_of(nt)):
                rc["rejected"].append(dict(nt, item="note", reason="keep-list violation (v9 backstop): note contains a share count"))
                rc["stop"] = True
    report = dict(share_count_exemptions={d: exemptions(tagj[d]) for d in raw} if not masking else {},
                  redaction_check=dict(stop=rc["stop"], why=rc["why"], classes=rc["classes"],
                                       accepted_counts={n: {it: sum(1 for x in v if x["item"] == it) for it in sorted(C.RED_ITEMS)}
                                                        for n, v in rc["accepted"].items()},
                                       rejected=[dict(dossier=x.get("dossier"), line=x.get("line"), item=x.get("item"),
                                                      reason=x["reason"]) for x in rc["rejected"]],
                                       soft_routes=[dict(dossier=x.get("dossier"), route=x.get("route")) for x in rc["soft_routes"]]))
    write_check_md(cfg, report)
    if rc["stop"]:
        report["stop"] = "redaction check failed: relaunch the redaction screener (same template)"
        return False, report
    red_texts, red_logs, stop = {}, {}, []
    for d in raw:
        ops = C.ops_from_json(rc, redj, names[d])
        red, rlog = C.apply_redactions(raw[d], ops)
        red_logs[d] = rlog
        bad = [x for x in rlog if x["status"] != "applied"]
        if bad:
            stop.append(f"{d}: redaction/note spans not applied: {bad}")
        if not masking:   # v9 N1: no tagging completeness; the pack is the redacted dossier
            report.setdefault("dossiers", {})[d] = dict(redactions_applied=sum(1 for x in rlog if x["status"] == "applied"),
                                                         share_count_tags=sum(1 for t_ in tags[d] if t_[3] in ("SHARES", "SH")))
            red_texts[d] = red
            continue
        _, cover, rep = C.apply_tags(red, tags[d], 1.0, 1.0)
        miss = C.completeness(red, cover)
        report.setdefault("dossiers", {})[d] = dict(redactions_applied=sum(1 for x in rlog if x["status"] == "applied"),
                                                     tags=len(tags[d]), absent_spans=len(rep["absent"]),
                                                     conflicts=rep["conflicts"], completeness_misses=miss,
                                                     untagged=rep["untagged_default"])
        if miss or rep["conflicts"] or rep["untagged_default"]:
            stop.append(f"{d}: tagging incomplete or conflicting: relaunch the tag screener for this dossier")
        red_texts[d] = red
    if stop:
        report["stop"] = stop
        return False, report
    for d in raw:
        out.write(f"redacted_{d}.md", strip(red_texts[d]))
    if not masking:   # v9 N1: one pack per run = the redacted dossier; k = j = 1
        manifest = {"runs": [dict(token=r["token"], dossier=r["dossier"], pack=r["pack"], k=1.0, j=1.0)
                             for r in cfg["runs"]], "bridge": [], "masking": False}
        for m in manifest["runs"]:
            t = red_texts[m["dossier"]]
            out.write(f"pack_{m['token']}_{m['pack']}", strip(t))
            lines = [f"- Line {ln}: \"{txt}\"" for ln, txt in replacements(t)]
            out.write(f"redlog_{m['token']}.md", ("\n".join(lines) or "(no redactions applied to this pack)") + "\n")
        out.write("manifest.json", json.dumps(manifest, indent=1))
        out.write("stage1c_report.json", json.dumps(report, indent=1, default=str, ensure_ascii=False))
        rl = ["# REDACTION_LOG (orchestrator-only; from the redaction screener's JSON, applied exactly as listed)", ""]
        rl += ["```json", json.dumps(redj, indent=1, ensure_ascii=False), "```", "", "## Applied", ""]
        for d in raw:
            rl += [f"- {d} {x['id']} line {x['line']} ({x['kind']}): {x['status']}" for x in red_logs[d]]
        out.write("REDACTION_LOG.md", "\n".join(rl) + "\n")
        return True, report
    manifest = {"runs": [], "bridge": []}
    for d in raw:
        runs = [r for r in cfg["runs"] if r["dossier"] == d]
        ks, js = (draws or {}).get(d) or C.draw_factors(len(runs))
        for r, k, j in zip(runs, ks, js):
            manifest["runs"].append(dict(token=r["token"], dossier=d, pack=r["pack"], k=k, j=j))
    for b in cfg.get("bridge", []):
        manifest["bridge"].append(dict(token=b["token"], dossier=b["dossier"], pack=b["pack"], k=1.0, j=1.0))
    third_by = {d: {x.lower() for x in tagj[d].get("third_party_domains", [])} for d in raw}
    checks = {}
    for m in manifest["runs"] + manifest["bridge"]:
        d = m["dossier"]
        scaled, cover, rep = C.apply_tags(red_texts[d], tags[d], m["k"], m["j"])
        cons = C.consistency_check(strip(red_texts[d]), strip(scaled), tagj[d].get("consistency", []))
        bridge = m in manifest["bridge"]
        if bridge:
            t = red_texts[d]
            hits = []
        else:
            t, _ = C.mask_identity(scaled, C.identity_from_json(tagj[d]))
            hits = C.masking_check(strip(t), C.identity_from_json(tagj[d]), cfg.get("ticker_forms", []))
        hard = [h for h in hits if h[0].lower() not in third_by[d]]
        if not tagj[d].get("consistency"):
            report.setdefault("notes", []).append(f"dossier {d}: no consistency triple listed (logged)")
        checks[m["token"]] = dict(masking_fail=hard, third_party=[h for h in hits if h not in hard],
                                  consistency=cons, consistency_fail=[c for c in cons if c["pre"]["ok"] is False or c["post"]["ok"] is False])
        if hard:
            stop.append(f"{m['token']}: masking check hits {hard[:5]}: relaunch the tag screener for dossier {d}")
        if checks[m["token"]]["consistency_fail"]:
            stop.append(f"{m['token']}: consistency check failed: relaunch the tag screener for dossier {d}")
        out.write(f"pack_{m['token']}_{m['pack']}", strip(t))
        if not bridge:
            lines = [f"- Line {ln}: \"{txt}\"" for ln, txt in replacements(t)]
            out.write(f"redlog_{m['token']}.md", "\n".join(lines) + "\n")
    report["checks"] = checks
    out.write("manifest.json", json.dumps(manifest, indent=1))
    out.write("stage1c_report.json", json.dumps(report, indent=1, default=str, ensure_ascii=False))
    rl = ["# REDACTION_LOG (orchestrator-only; from the redaction screener's JSON, applied exactly as listed)", ""]
    rl += ["```json", json.dumps(redj, indent=1, ensure_ascii=False), "```", "", "## Applied", ""]
    for d in raw:
        rl += [f"- {d} {x['id']} line {x['line']} ({x['kind']}): {x['status']}" for x in red_logs[d]]
    out.write("REDACTION_LOG.md", "\n".join(rl) + "\n")
    if stop:
        report["stop"] = stop
        return False, report
    return True, report


def write_check_md(cfg, report):
    fd = cfg.get("final_dir")
    if not fd:
        return
    os.makedirs(fd, exist_ok=True)
    r = report["redaction_check"]
    L = ["# Redaction check (toolkit v9, spec Stage 1)", "",
         f"Result: {'STOP' if r['stop'] else 'PASS'}" + (f" — {'; '.join(r['why'])}" if r["why"] else ""), "",
         "| dossier | R-1 | R-2 | R-3 | status R-1 / R-2 / R-3 |", "|---|---|---|---|---|"]
    for n, c in r["accepted_counts"].items():
        st = r["classes"].get(n, {})
        L.append(f"| {n} | {c['R-1']} | {c['R-2']} | {c['R-3']} | {st.get('R-1')} / {st.get('R-2')} / {st.get('R-3')} |")
    L += ["", f"Soft routes logged: {len(r['soft_routes'])} (" + "; ".join(f"{x['dossier']}: {x['route']}" for x in r["soft_routes"]) + ")",
          "", "Rejected entries: " + (", ".join(f"{x['dossier']} line {x['line']} ({x['item']}): {x['reason']}" for x in r["rejected"]) or "none"),
          "", "Spans and replacement texts are in the orchestrator-only REDACTION_LOG."]
    open(os.path.join(fd, "redaction_check.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")


# ----------------------------------------------------------------------------- self-test
def selftest():
    import tempfile
    out, ok_all = [], True

    def check(name, cond, detail=""):
        nonlocal ok_all
        ok_all &= bool(cond)
        out.append(f"{'PASS' if cond else 'FAIL'}  {name}  {detail}")
    A = ("# Acme Data Pack\n"
         "Acme Corp sells widgets.\n"
         "| Year | Revenue ($M) | Net income ($M) | Diluted EPS | Diluted shares (M) |\n"
         "|---|---|---|---|---|\n"
         "| FY2024 | 1,000 | 200 | 2.00 | 100 |\n"
         "| FY2025 | 1,100 | 231 | 2.31 | 100 |\n"
         "Repurchases: 5 million shares for $150M in FY2025.\n"
         "Use diluted weighted-average shares throughout.\n")
    B = ("# Acme Review\n"
         "Acme Corp, revenue $1,100M in FY2025; net income $231M; diluted EPS $2.31 on 100 million shares.\n")
    tA = {"identity": [{"variants": ["Acme Corp", "Acme"], "replacement": "the Company", "generic_word": False}],
          "tags": [{"line": 5, "span": "1,000", "tag": "COMPANY_TOTAL"}, {"line": 5, "span": "200", "tag": "COMPANY_TOTAL"},
                   {"line": 5, "span": "2.00", "tag": "PER_SHARE"}, {"line": 5, "span": "100", "tag": "SHARES"},
                   {"line": 6, "span": "1,100", "tag": "COMPANY_TOTAL"}, {"line": 6, "span": "231", "tag": "COMPANY_TOTAL"},
                   {"line": 6, "span": "2.31", "tag": "PER_SHARE"}, {"line": 6, "span": "100", "tag": "SHARES"},
                   {"line": 7, "span": "5 million", "tag": "SHARES"}, {"line": 7, "span": "$150M", "tag": "COMPANY_TOTAL"}],
          "consistency": [{"period": "FY2025", "basis": "GAAP", "eps": {"line": 6, "span": "2.31"},
                           "shares": {"line": 6, "span": "100"}, "net_income": {"line": 6, "span": "231"}}]}
    tB = {"identity": [{"variants": ["Acme Corp", "Acme"], "replacement": "the Company", "generic_word": False}],
          "tags": [{"line": 2, "span": "$1,100M", "tag": "COMPANY_TOTAL"}, {"line": 2, "span": "$231M", "tag": "COMPANY_TOTAL"},
                   {"line": 2, "span": "$2.31", "tag": "PER_SHARE"}, {"line": 2, "span": "100 million", "tag": "SHARES"}],
          "consistency": [{"period": "FY2025", "basis": "GAAP", "eps": {"line": 2, "span": "$2.31"},
                           "shares": {"line": 2, "span": "100 million"}, "net_income": {"line": 2, "span": "$231M"}}]}
    good = {"redactions": [{"item": "R-2", "dossier": "a.md", "line": 7, "span": "$150M", "replacement": "[amount redacted]"}],
            "class_status": [{"dossier": "a.md", "item": "R-1", "status": "not present"}, {"dossier": "a.md", "item": "R-2", "status": "redacted"},
                             {"dossier": "a.md", "item": "R-3", "status": "not present"}, {"dossier": "b.md", "item": "R-1", "status": "not present"},
                             {"dossier": "b.md", "item": "R-2", "status": "not present"}, {"dossier": "b.md", "item": "R-3", "status": "not present"}],
            "soft_routes": [{"dossier": "a.md", "route": "net income / change in shares", "figures": "rows FY2024-25"}],
            "methodology_notes": [{"dossier": "a.md", "line": 8, "span": "Use diluted weighted-average shares throughout."}]}
    with tempfile.TemporaryDirectory() as td:
        for n, t in (("a.md", A), ("b.md", B)):
            open(os.path.join(td, n), "w").write(t)
        json.dump(tA, open(os.path.join(td, "tA.json"), "w"))
        json.dump(tB, open(os.path.join(td, "tB.json"), "w"))

        def cfg_with(red):
            json.dump(red, open(os.path.join(td, "red.json"), "w"))
            return {"ticker": "ACME", "ticker_forms": ["ACME", "Acme"],
                    "dossiers": {"A": {"raw": os.path.join(td, "a.md"), "name": "a.md", "tags_json": os.path.join(td, "tA.json")},
                                 "B": {"raw": os.path.join(td, "b.md"), "name": "b.md", "tags_json": os.path.join(td, "tB.json")}},
                    "redaction_json": os.path.join(td, "red.json"),
                    "runs": [{"token": "r1", "dossier": "A", "pack": "pack_x1.md"}, {"token": "r2", "dossier": "B", "pack": "pack_x2.md"}],
                    "out": {"dir": os.path.join(td, "out")}, "final_dir": os.path.join(td, "final"), "masking": True}
        bad1 = json.loads(json.dumps(good))
        bad1["redactions"].append({"dossier": "a.md", "line": 6, "span": "231", "replacement": "x"})
        okb, rep = run(cfg_with(bad1))
        check("9a redaction check rejects an entry that names no list item", not okb and any(
            "names no redact-list item" in x["reason"] for x in rep["redaction_check"]["rejected"]))
        bad2 = json.loads(json.dumps(good))
        bad2["redactions"].append({"item": "R-2", "dossier": "a.md", "line": 7, "span": "5 million shares", "replacement": "x"})
        okb, rep = run(cfg_with(bad2))
        check("9b redaction check rejects an entry over a SHARES-tagged span (keep list)", not okb and any(
            "keep-list" in x["reason"] for x in rep["redaction_check"]["rejected"]))
        bad3 = json.loads(json.dumps(good))
        bad3["class_status"][4]["status"] = "present"
        okb, rep = run(cfg_with(bad3))
        check("9c a class marked present but unredacted stops Stage 2", not okb and any("status 'present'" in w for w in rep["redaction_check"]["why"]))
        bad4 = json.loads(json.dumps(good))
        bad4["methodology_notes"].append({"dossier": "a.md", "line": 7, "span": "Repurchases: 5 million shares"})
        okb, rep = run(cfg_with(bad4))
        check("9g a methodology note that would remove a SHARES-tagged figure is rejected", not okb and any(
            "note would remove" in x["reason"] for x in rep["redaction_check"]["rejected"]))
        boundary = C.redaction_check({"redactions": [{"item": "R-2", "dossier": "x.md", "line": 1, "span": "$1,100M", "replacement": "r"}],
                                      "class_status": [{"dossier": "x.md", "item": i, "status": st} for i, st in
                                                       (("R-1", "not present"), ("R-2", "redacted"), ("R-3", "not present"))]},
                                     {"x.md": "Repurchased 100 million shares for $1,100M"}, {"x.md": [(1, 1, "100", "SHARES")]})
        check("9h digit boundaries: SHARES tag '100' does not match inside '$1,100M' (negative control)",
              not boundary["stop"] and len(boundary["accepted"]["x.md"]) == 1, json.dumps(boundary["why"]))
        txt = "Revenue was €1,200 million in FY2025.\n| Item | Revenue (€M) |\n|---|---|\n| FY2025 | 1,200 |"
        miss = C.completeness(txt, {})
        check("9i completeness flags non-USD amounts and cells under a currency header",
              any("€1,200" in m[2] for m in miss) and any(m[1] == "numeric cell under currency header" for m in miss), str(miss))
        txt2 = ("## Sales (US$ millions)\n"
                "4. **Buybacks.** About 2,500 shares were repurchased between April 1 and May 1, 2026 (May 20, 2021).\n"
                "OM 17.5–18.0% with EPS growth; tax 22–23%; EPS $1.20; FY28–30 EPS framework.\n"
                "| Item | Revenue | Growth |\n|---|---|---|\n| FY2025 | 1,200 (+8.4%) | +5.5% |\n| Sold | August 15, 2024 | (−6.3%) |")
        miss2 = {m[2] for m in C.completeness(txt2, {})}
        check("9j v7.1.1: dates (full month, after '('), percentages, percentage ranges, fiscal-period ranges and list numbers are not amounts; "
              "real amounts are still flagged", {"2,500", "1,200", "$1.20"} <= miss2 and miss2 <= {"2,500", "1,200", "$1.20"},
              str(sorted(miss2)))
        txt3 = ("Cumulative repurchases from 3Q21 to 1Q25 were 3,076,725 shares. About 2,500 shares remained.\n"
                "Debt fell (1/100 depositary) over 5+ yrs of EPS growth; 1H26 EPS $2.10.\n"
                "There were 36,035 shares outstanding. 21 of 71 vessels were unencumbered.\n"
                "Repurchased 1,000 shares in 2Q23 and paid $3.0M.\n"
                "## Balance (US$ thousands)\n| US$000 | FY2025 |\n|---|---|\n| Debt | 676,400 |\n| Maturity | 4.5 years |")
        miss3 = {m[2] for m in C.completeness(txt3, {})}
        want3 = {"3,076,725", "2,500", "$2.10", "36,035", "1,000", "$3.0", "676,400"}
        check("9l v7.1.2: period labels (3Q21, 1H26), unit labels (US$000), durations (4.5 years, 5+ yrs), ratios (1/100) and "
              "numbers in another sentence than the share word are not amounts; real amounts are still flagged",
              miss3 == want3, str(sorted(miss3)))
        txt4 = ("| Item | FY2025 |\n|---|---|\n| Diluted weighted shares (000s) | 14,147 |\n"
                "Diluted weighted average shares (000) were 14,181 in the half; a further (1,250) shares and 300 shares [000's] lapsed.\n")
        miss4 = {m[2] for m in C.completeness(txt4, {})}
        want4 = {"14,147", "14,181", "(1,250)", "300"}
        check("9m v7.1.3: parenthesised scale labels ((000s), (000), [000's]) are not amounts; share counts beside them, "
              "including a parenthesised one, are still flagged", miss4 == want4, str(sorted(miss4)))
        masked3, _ = C.mask_identity("Widgetco closed widgetco.com in FY2025.",
                                     [(["Widgetco"], "Brand 1", False), (["widgetco.com"], "the Brand 1 website", False)])
        check("9k v7.1.1: identity variants are applied longest-first across entries (a domain listed after its brand is masked whole)",
              masked3 == "Brand 1 closed the Brand 1 website in FY2025." and not C.masking_check(masked3, [(["Widgetco"], "Brand 1", False)], []),
              masked3)
        okg, rep = run(cfg_with(good), draws={"A": ([0.5], [1.5]), "B": ([2.2], [0.7])})
        packA = open(os.path.join(td, "out", "pack_r1_pack_x1.md")).read()
        check("9d valid screener JSON passes; pack written, masked, redacted and noted", okg and "Acme" not in packA
              and "$150M" not in packA and "[methodology note removed]" in packA, json.dumps(rep.get("stop")))
        c = rep["checks"]["r1"]["consistency"][0]
        check("9e consistency triple holds before and after rescaling (EPS 2.31 / k, shares x k.j, NI x j)",
              c["pre"]["ok"] and c["post"]["ok"] and abs(c["post"]["eps"] - 4.62) < 1e-9, json.dumps(c))
        # 9n (v8.0.1): format-preserved rounding of a small EPS after a large k passes; a mis-tag still fails
        pre = "EPS 0.82 shares 222.5 NI 183.2"
        trip = [{"period": "P", "basis": "GAAP", "eps": {"line": 1, "span": "0.82"}, "shares": {"line": 1, "span": "222.5"},
                 "net_income": {"line": 1, "span": "183.2"}, "unit_factor": 1}]
        ok_r = C.consistency_check(pre, "EPS 0.21 shares 1199.0 NI 257.7", trip)[0]
        bad_r = C.consistency_check(pre, "EPS 0.82 shares 1199.0 NI 257.7", trip)[0]
        bad_s = C.consistency_check(pre, "EPS 0.21 shares 853.2 NI 257.7", trip)[0]
        check("9n rounding allowance: EPS 0.82/k printed 0.21 passes; EPS left unscaled or shares scaled by j only fail",
              ok_r["pre"]["ok"] and ok_r["post"]["ok"] and not bad_r["post"]["ok"] and not bad_s["post"]["ok"], json.dumps([ok_r["post"], bad_r["post"], bad_s["post"]]))
        # 9o (v9 N1): masking off -- the pack is the redacted dossier, unmasked and unscaled; untagged amounts do not
        # stop it; k = j = 1; a redaction over a share count is still refused (the keep list needs only SHARES tags)
        cfg9 = cfg_with(good)
        cfg9.update(masking=False, out={"dir": os.path.join(td, "out9")})
        json.dump({"tags": [t_ for t_ in tA["tags"] if t_["tag"] == "SHARES"]}, open(os.path.join(td, "tA9.json"), "w"))
        json.dump({"tags": [t_ for t_ in tB["tags"] if t_["tag"] == "SHARES"]}, open(os.path.join(td, "tB9.json"), "w"))
        cfg9["dossiers"]["A"]["tags_json"] = os.path.join(td, "tA9.json")
        cfg9["dossiers"]["B"]["tags_json"] = os.path.join(td, "tB9.json")
        ok9, rep9 = run(cfg9)
        pk9 = open(os.path.join(td, "out9", "pack_r1_pack_x1.md")).read()
        man9 = json.load(open(os.path.join(td, "out9", "manifest.json")))
        rl9 = open(os.path.join(td, "out9", "redlog_r1.md")).read()
        bad9 = json.loads(json.dumps(good))
        bad9["redactions"].append({"item": "R-2", "dossier": "a.md", "line": 7, "span": "5 million shares", "replacement": "x"})
        json.dump(bad9, open(os.path.join(td, "red.json"), "w"))
        okb9, repb9 = run(cfg9)
        check("9o v9: masking off -- pack is the redacted dossier (names and figures unchanged, $150M redacted, note "
              "removed), k = j = 1, redlog written; a redaction over a SHARES figure is still refused",
              ok9 and "Acme Corp sells widgets." in pk9 and "| FY2025 | 1,100 | 231 | 2.31 | 100 |" in pk9
              and "$150M" not in pk9 and "[methodology note removed]" in pk9 and "[amount redacted]" in rl9
              and all(m_["k"] == 1.0 and m_["j"] == 1.0 for m_ in man9["runs"]) and not okb9
              and any("keep-list" in x["reason"] for x in repb9["redaction_check"]["rejected"]), json.dumps(rep9.get("stop")))
        # 9p (v9 review): fail closed -- no "tags" list, an empty list, a tag without a line, or a span not on its line
        # stops Stage 1 (relaunch the tag screener); an untagged share count inside a redaction span is refused by the
        # backstop; a dollar amount of shares is not a share count
        json.dump(good, open(os.path.join(td, "red.json"), "w"))
        res9p = []
        for k_, tj in (("none", {}), ("empty", {"tags": []}), ("noline", {"tags": [{"span": "5 million", "tag": "SHARES"}]}),
                       ("absent", {"tags": [{"line": 7, "span": "6 million", "tag": "SHARES"}]})):
            json.dump(tj, open(os.path.join(td, "tA9p.json"), "w"))
            c_ = json.loads(json.dumps(cfg9))
            c_["dossiers"]["A"]["tags_json"] = os.path.join(td, "tA9p.json")
            c_["out"] = {"dir": os.path.join(td, "out9p")}
            ok_, rep_ = run(c_)
            res9p.append(not ok_ and "relaunch the tag screener" in json.dumps(rep_.get("stop")))
        json.dump({"tags": [{"line": 5, "span": "100", "tag": "SHARES"}, {"line": 6, "span": "100", "tag": "SHARES"},
                            {"line": 7, "span": "Repurchases", "tag": "SHARES"}]},   # recall met, the figure itself untagged
                  open(os.path.join(td, "tA9p.json"), "w"))
        c_ = json.loads(json.dumps(cfg9))
        c_["dossiers"]["A"]["tags_json"] = os.path.join(td, "tA9p.json")
        c_["out"] = {"dir": os.path.join(td, "out9q")}
        json.dump(bad9, open(os.path.join(td, "red.json"), "w"))
        okq, repq = run(c_)
        backstop = (not okq) and any("v9 backstop" in x["reason"] for x in repq["redaction_check"]["rejected"])
        amounts = ["$2.1 billion of shares", "US$ 3 million of shares", "EUR 300 million of shares", "R$ 2.1 billion of shares",
                   "MXN 500 million of shares", "CHF 1.2bn of shares", "$ 2.1 billion of shares", "Ps. 450 million in shares",
                   "in 2025 shares", "300 million EUR of shares", "12% of shares"]
        counts = ["repurchased 5.2 million of its shares", "1,234 shares",
                  "**Weighted-average diluted shares:** FY2021 49,802,993; FY2022 51,335,621",
                  "Shares outstanding at 2026-06-30: 50.7 million"]
        dollars = not any(SHARECOUNT_RX.search(x) for x in amounts) and all(SHARECOUNT_RX.search(x) for x in counts)
        # MELI's label-first format: an untagged share-count line stops Stage 1; with the line tagged, a redaction of
        # its other figures is refused by the backstop
        A2 = A + "**Weighted-average diluted shares:** FY2021 49,802,993; FY2022 51,335,621\n"
        open(os.path.join(td, "a2.md"), "w").write(A2)
        c2 = json.loads(json.dumps(cfg9))
        c2["dossiers"]["A"]["raw"] = os.path.join(td, "a2.md")
        c2["out"] = {"dir": os.path.join(td, "out9r")}
        json.dump(good, open(os.path.join(td, "red.json"), "w"))
        ok_u, rep_u = run(c2)   # tA9 has no tag on line 9
        json.dump({"tags": [t_ for t_ in tA["tags"] if t_["tag"] == "SHARES"] +
                           [{"line": 9, "span": "49,802,993", "tag": "SHARES"}]}, open(os.path.join(td, "tA9r.json"), "w"))
        c2["dossiers"]["A"]["tags_json"] = os.path.join(td, "tA9r.json")
        red2 = json.loads(json.dumps(good))
        red2["redactions"].append({"item": "R-3", "dossier": "a.md", "line": 9, "span": "FY2022 51,335,621", "replacement": "x"})
        json.dump(red2, open(os.path.join(td, "red.json"), "w"))
        ok_r, rep_r = run(c2)
        meli_like = (not ok_u and "share-count line(s) with no SHARES tag: [9]" in json.dumps(rep_u.get("stop"))
                     and not ok_r and any("v9 backstop" in x["reason"] for x in rep_r["redaction_check"]["rejected"]))
        dollars = dollars and meli_like
        # R2-1: a currency unit in the label makes the line's numbers amounts (no deadlock); a number next to "shares"
        # still counts; R2-2: "Diluted shares (m) | 50.7" is a count; the logged exemption list skips a line
        r21 = (not SHARECOUNT_RX.search("Repurchases of common shares (US$ mn): FY2025 1,500")
               and SHARECOUNT_RX.search("Repurchased (US$ mn): 1,500 for 12,345 shares")
               and SHARECOUNT_RX.search("| Diluted shares (m) | 50.7 | 51.3 |")
               and not SHARECOUNT_RX.search("| Revenue (US$ m) per share data | 50.7 |")
               and share_count_lines("a\nShares bought: 12,345 (odd lot)\n", {2: "x"}) == []
               and share_count_lines("a\nShares bought: 12,345 (odd lot)\n") == [2]
               and exemptions({"not_share_counts": [{"line": 2, "reason": "a share class name, not a count"},
                                                    {"line": 3, "reason": ""}]}) == {2: "a share class name, not a count"})
        dollars = dollars and bool(r21)
        check("9p v9 fail-closed: missing, empty, line-less or misquoted SHARES lists, and any share-count line without a "
              "SHARES tag (both orders, including the 'diluted shares: FY2021 49,802,993' format), stop Stage 1; an untagged "
              "share count in a redaction span is refused by the backstop; currency amounts of shares (any symbol or ISO "
              "code, or a currency unit stated in the line's label), percentages and years are not share counts; a share "
              "label with a count unit ('shares (m)') makes its numbers counts; a logged exemption skips a line",
              all(res9p) and backstop and bool(dollars), f"{res9p} backstop={backstop}")
        json.dump(good, open(os.path.join(td, "red.json"), "w"))
        run(cfg9)
        md = open(os.path.join(td, "final", "redaction_check.md")).read()
        check("9f final/redaction_check.md carries counts and reasons, never a redacted span", "$150M" not in md and "| a.md | 0 | 1 | 0 |" in md)
    return ok_all, out


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "selftest":
        ok, lines = selftest()
        print("\n".join(lines))
        print("STAGE-1 SELF-TEST " + ("PASSED" if ok else "FAILED"))
        sys.exit(0 if ok else 1)
    if len(sys.argv) > 2 and sys.argv[1] == "run":
        ok, rep = run(json.load(open(sys.argv[2])))
        print(json.dumps({k: rep[k] for k in rep if k in ("stop", "redaction_check")}, indent=1, default=str, ensure_ascii=False))
        sys.exit(0 if ok else 2)
    print(__doc__)
