#!/usr/bin/env python3
"""stage1c.py -- toolkit v7.1 library (v7.1.2 and v7.1.3 completeness exclusions) for Stage 1 (redaction check, redactions and methodology-note removals,
exactly as the redaction screener listed them) and Stage 1c (mask and rescale by the tag screener's tags).
No content judgment: every redaction, note, tag, identity token and consistency triple comes from the
screeners' JSON outputs (spec Appendix H). The driver is stage1.py."""
import sys, os, re, json, math, secrets
from decimal import Decimal, ROUND_HALF_EVEN

S0, S1 = "\x02", "\x03"   # sentinels around replacement text (stripped before hand-off)
TAGMAP = {"CT": "COMPANY_TOTAL", "PS": "PER_SHARE", "SH": "SHARES", "UN": "UNSCALED",
          "COMPANY_TOTAL": "COMPANY_TOTAL", "PER_SHARE": "PER_SHARE", "SHARES": "SHARES", "UNSCALED": "UNSCALED"}
RED_ITEMS = {"R-1", "R-2", "R-3"}


# ----------------------------------------------------------------------------- Stage 1: redactions
def apply_redactions(text, ops):
    lines = text.split("\n")
    log = []
    for kind in ("redactions", "notes"):
        for op in ops[kind]:
            i = op["line"] - 1
            to = op.get("to", "[methodology note removed]")
            n = lines[i].count(op["span"])
            if n != 1:
                log.append(dict(id=op["id"], line=op["line"], status=f"span found {n} times", kind=kind))
                if n == 0:
                    continue
            sp = op["span"]
            pre = 0
            while pre < min(len(sp), len(to)) and sp[pre] == to[pre]:
                pre += 1
            suf = 0
            while suf < min(len(sp), len(to)) - pre and sp[len(sp) - 1 - suf] == to[len(to) - 1 - suf]:
                suf += 1
            marked = to[:pre] + S0 + to[pre:len(to) - suf] + S1 + to[len(to) - suf:]
            lines[i] = lines[i].replace(sp, marked, 1)
            log.append(dict(id=op["id"], line=op["line"], status="applied", kind=kind, replacement=to))
    return "\n".join(lines), log


# ----------------------------------------------------------------------------- numbers
NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")


def span_regex(span):
    s = re.escape(span)
    left = r"(?<![\d.,])" if span[0].isdigit() else r"(?<![\d\w])" if span[0] in "$~>(" else ""
    right = r"(?![\d]|[.,]\d)" if span[-1].isdigit() else ""
    return re.compile(left + s + right)


def fmt_like(orig, value):
    dec = len(orig.split(".")[1]) if "." in orig else 0
    q = Decimal(1).scaleb(-dec)
    v = Decimal(repr(value)).quantize(q, rounding=ROUND_HALF_EVEN)
    s = f"{v:,.{dec}f}"
    return s


def scale_span(span_text, factor):
    def rep(m):
        t = m.group(0)
        if t.endswith(",") or t.endswith("."):
            t2 = t.rstrip(",.")
            tail = t[len(t2):]
        else:
            t2, tail = t, ""
        val = float(t2.replace(",", ""))
        return fmt_like(t2, val * factor) + tail
    return NUM.sub(rep, span_text)


def apply_tags(text, tags, k, j):
    lines = text.split("\n")
    factor = {"COMPANY_TOTAL": j, "PER_SHARE": 1.0 / k, "SHARES": k * j, "UNSCALED": 1.0}
    cover = {}          # (line, start, end) -> tag
    report = dict(applied=0, absent=[], conflicts=[], untagged_default=[])
    edits = {}          # line -> list of (start, end, newtext)
    for a, b, span, tg in tags:
        if tg is None:
            report["untagged_default"].append((a, span))
            continue
        tag = TAGMAP[tg]
        found = False
        rx = span_regex(span)
        for L in range(a, b + 1):
            if L - 1 >= len(lines):
                continue
            line = lines[L - 1]
            for m in rx.finditer(line):
                found = True
                key = (L, m.start(), m.end())
                prev = [kk for kk in cover if kk[0] == L and not (kk[2] <= m.start() or kk[1] >= m.end())]
                clash = [kk for kk in prev if cover[kk] != tag]
                if clash:
                    report["conflicts"].append((L, span, tag, [cover[c] for c in clash]))
                if key in cover:
                    continue
                if prev and not clash:
                    continue   # same tag, overlapping duplicate
                cover[key] = tag
                if tag != "UNSCALED":
                    edits.setdefault(L, []).append((m.start(), m.end(), scale_span(m.group(0), factor[tag])))
                report["applied"] += 1
        if not found:
            report["absent"].append((a, b, span, tg))
    for L, ed in edits.items():
        line = lines[L - 1]
        for s, e, new in sorted(ed, key=lambda x: -x[0]):
            line = line[:s] + new + line[e:]
        lines[L - 1] = line
    return "\n".join(lines), cover, report


# ----------------------------------------------------------------------------- completeness check
CUR_SYM = r"(?:US\$|C\$|A\$|HK\$|S\$|R\$|\$|€|£|¥|₹|₩|CHF|EUR|USD|GBP|JPY|CAD|AUD|SEK|NOK|DKK|CNY|RMB|INR|KRW|BRL|MXN|ZAR|HKD|SGD)"
CURR = re.compile(r"[−\-+~>(]?" + CUR_SYM + r"\s?\(?\d[\d,]*(?:\.\d+)?\)?|\d[\d,]*(?:\.\d+)?\s?(?:EUR|USD|GBP|CHF|JPY|CAD|AUD)\b")
CUR_HDR = re.compile(CUR_SYM + r"|\((?:US)?\$?[MBK]\)|\b(?:millions|billions|thousands) of (?:dollars|euros|pounds|yen)\b", re.I)
STANDALONE = re.compile(r"(?<![\w.,/])\(?[−\-+~>]?(?:[$€£¥₹₩])?\d[\d,]*(?:\.\d+)?\)?%?(?![\d])")


def label_like(text, end):
    rest = text[end:]
    return rest.startswith("M FY") or bool(re.match(r"-[KQ]\b", rest))


def is_year(t):
    return bool(re.fullmatch(r"(19|20)\d\d", t))


# v7.1.1: spec Stage 1c check 1 excludes dates, percentages, period labels and list numbering from "amounts".
MONTH = (r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|June?|July?|Aug(?:ust)?|"
         r"Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)")
MONTH_WORD = re.compile(r"[(\[]?" + MONTH + r"\.?")
MONTH_BEFORE = re.compile(r"(?<![A-Za-z])" + MONTH + r"\.?\s+$")
FY_RANGE_BEFORE = re.compile(r"\bFY\s?\d{2,4}\s?[–—-]$")
PCT_RANGE_AFTER = re.compile(r"^\s?[–—-]\s?[+−\-]?\d[\d,]*(?:\.\d+)?%")
# v7.1.2: further non-amount classes under spec Stage 1c check 1 (period labels, unit labels, durations, ratios),
# and the five-word window stays within one sentence.
PERIOD_AFTER = re.compile(r"^[QH]\d{2}(?:\d{2})?\b")                     # "3Q21", "1H26": a period label
DURATION_AFTER = re.compile(r"^\+?\s?(?:years?|yrs?|months?|mos?|weeks?|days?|quarters?)\b", re.I)   # "4.9 years", "5+ yrs"
RATIO_AFTER = re.compile(r"^/\d")                                          # "1/100": a ratio
UNIT_LABEL = re.compile(r"[−\-+~>(]?" + CUR_SYM + r"\s?\(?0{3},?\)?")      # "US$000": a unit label, not an amount
# v7.1.3: a parenthesised thousand/million scale label ("(000)", "(000s)", "[000's]") is a unit label, not an amount.
SCALE_LABEL = re.compile(r"[(\[]0{3}(?:,?0{3})?(?:'?s)?[)\]][.,;:]?")
SENT_ABBR = {"approx.", "inc.", "corp.", "ltd.", "no.", "vs.", "etc.", "co.", "est."}


def non_amount_after(t, rest):
    """v7.1.2: a number followed by a period-label, duration or ratio continuation is not an amount."""
    if re.search(r"[$€£¥₹₩]", t):
        return False
    return bool(PERIOD_AFTER.match(rest) or DURATION_AFTER.match(rest) or RATIO_AFTER.match(rest))


def ends_sentence(w):
    """v7.1.2: a word that closes a sentence ("outstanding.")."""
    core = re.sub(r"[*_)\]\"']+$", "", w)
    return len(core) >= 4 and core.endswith(".") and core[-2].islower() and core.lower() not in SENT_ABBR


def is_pct_token(t):
    return t.rstrip(")]").endswith("%")


def completeness(redacted_text, cover):
    lines = redacted_text.split("\n")
    misses = []
    heading = ""
    table_cur_cols, in_table, section_cols = set(), False, set()
    for i, raw in enumerate(lines, start=1):
        line = raw
        if line.startswith("#"):
            heading = line
            continue
        covered = [(s, e) for (L, s, e) in cover if L == i]

        def is_cov(s, e):
            return any(not (e <= cs or s >= ce) for cs, ce in covered)
        # (1) currency amounts
        for m in CURR.finditer(line):
            if S0 in line[max(0, m.start() - 200):m.start()] and S1 in line[m.end():m.end() + 400] and \
                    line.rfind(S0, 0, m.start()) > line.rfind(S1, 0, m.start()):
                continue  # inside replacement text
            if UNIT_LABEL.fullmatch(m.group(0)) and not re.match(r"[\d.]", line[m.end():m.end() + 1]):
                continue   # v7.1.2: a currency unit label ("US$000"), not an amount
            if not is_cov(m.start(), m.end()):
                misses.append((i, "currency amount", m.group(0)))
        # (2) numeric cells under currency headers
        if line.startswith("|"):
            cells = [c for c in line.strip().strip("|").split("|")]
            if not in_table:
                in_table = True
                hdr_cur = bool(CUR_HDR.search(heading))
                table_cur_cols = {ci for ci, c in enumerate(cells) if CUR_HDR.search(c)}
                section_cols = {ci for ci, c in enumerate(cells) if c.strip().lower() == "section"}
                table_all = bool(hdr_cur)
                table_hdr = (table_cur_cols, table_all)
                continue
            if set(line.replace("|", "").strip()) <= set("-: "):
                continue
            cols, allc = table_hdr
            pos = 1
            for ci, c in enumerate(cells):
                start = line.index("|", pos - 1) + 1 if ci == 0 else pos
                cstart = line.find(c, start)
                pos = cstart + len(c) + 1
                if ci == 0 or not (allc or ci in cols):
                    continue
                for m in STANDALONE.finditer(c):
                    t = m.group(0)
                    core = re.sub(r"[^\d.]", "", t)
                    if is_year(core) and not re.search(r"[$€£¥₹₩]", t):
                        continue
                    if label_like(c, m.end()):
                        continue
                    if is_pct_token(t) or PCT_RANGE_AFTER.match(c[m.end():]):
                        continue   # v7.1.1: a percentage, or the first number of a percentage range
                    if not re.search(r"[$€£¥₹₩]", t) and MONTH_BEFORE.search(c[:m.start()]):
                        continue   # v7.1.1: the day of a date ("August 15, 2024")
                    if FY_RANGE_BEFORE.search(c[:m.start()]):
                        continue   # v7.1.1: the end of a fiscal-period range ("FY28–30"), a period label
                    if non_amount_after(t, c[m.end():]):
                        continue   # v7.1.2: a period label, a duration or a ratio
                    s0 = cstart + m.start()
                    if S0 in c:
                        continue
                    if not is_cov(s0, s0 + len(t)):
                        misses.append((i, "numeric cell under currency header", t))
        else:
            in_table = False
        # (3) numbers within five words of share / per share / EPS (excluding years, dates, percentages,
        #     form names, period labels and cells under a "Section" header)
        chk = line
        if line.startswith("|") and in_table and section_cols:
            cells2 = line.strip().strip("|").split("|")
            for ci in section_cols:
                if ci < len(cells2):
                    chk = chk.replace("|" + cells2[ci] + "|", "|" + " " * len(cells2[ci]) + "|")
        words = [(m.start(), m.end(), m.group(0)) for m in re.finditer(r"\S+", chk)]
        anchors = [wi for wi, (_, _, w) in enumerate(words) if re.search(r"\bshares?\b|\bEPS\b", w, re.I)]
        sid, cur_sid = [], 0   # v7.1.2: the five-word window does not cross a sentence boundary
        for _, _, w in words:
            sid.append(cur_sid)
            if ends_sentence(w):
                cur_sid += 1
        if anchors:
            for wi, (ws, we, w) in enumerate(words):
                near = [a for a in anchors if sid[a] == sid[wi]]
                if not near or min(abs(wi - a) for a in near) > 5:
                    continue
                for m in STANDALONE.finditer(w):
                    t = m.group(0)
                    core = re.sub(r"[^\d.]", "", t)
                    if not core or t.endswith("%") or is_year(core) or label_like(w, m.end()):
                        continue
                    if w.rstrip(".,;:)]").endswith("%"):
                        continue   # v7.1.1: a percentage range ("17.5–18.0%", "22–23%;")
                    if wi == 0 and re.fullmatch(r"\d{1,3}\.", w):
                        continue   # v7.1.1: list numbering ("4.")
                    if SCALE_LABEL.fullmatch(w):
                        continue   # v7.1.3: a scale unit label ("(000s)", "(000)"), not an amount
                    if FY_RANGE_BEFORE.search(w[:m.start()]):
                        continue   # v7.1.1: the end of a fiscal-period range ("FY28–30"), a period label
                    if non_amount_after(t, chk[ws + m.end():ws + m.end() + 16]):
                        continue   # v7.1.2: a period label ("3Q21"), a duration ("5+ yrs") or a ratio ("1/100")
                    if wi > 0 and MONTH_WORD.fullmatch(words[wi - 1][2]) and not re.search(r"[$€£¥₹₩]", t):
                        continue   # v7.1.1: the day of a date, full or abbreviated month, after "(" too
                    s0 = ws + m.start()
                    seg = line[:s0]
                    if seg.rfind(S0) > seg.rfind(S1):
                        continue
                    if not is_cov(s0, s0 + len(t)):
                        misses.append((i, "number near share/EPS", t))
    # dedupe
    out, seen = [], set()
    for x in misses:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


# ----------------------------------------------------------------------------- identity masking
def mask_identity(text, identity):
    rep_log = {}
    # v7.1.1: every variant of every entry is applied longest-first, so a longer variant ("Brand.com") is replaced
    # before a shorter one from another entry ("Brand") can split it.
    flat = [(v, repl, generic) for variants, repl, generic in identity for v in variants]
    for v, repl, generic in sorted(flat, key=lambda x: len(x[0]), reverse=True):
        if True:
            if generic:
                rx = re.compile(r"(?<![\w-])" + re.escape(v) + r"(?![\w-])")
            else:
                rx = re.compile(r"(?<![\w])" + re.escape(v) + r"(?![\w])", re.I)

            def sub(m, repl=repl):
                s = m.string
                pre = s[max(0, m.start() - 3):m.start()]
                at_start = m.start() == 0 or s[m.start() - 1] == "\n" or re.search(r"(^|[.!?:]\s|\*\*|\|\s|-\s|\n)$", s[max(0, m.start() - 3):m.start()])
                r = repl
                if at_start and r.startswith("the "):
                    r = "The " + r[4:]
                return r
            text, n = rx.subn(sub, text)
            rep_log[v] = rep_log.get(v, 0) + n
    return text, rep_log


def masking_check(text, identity, ticker_forms):
    hits = []
    for variants, repl, generic in identity:
        for v in variants:
            rx = re.compile(r"(?<![\w-])" + re.escape(v) + r"(?![\w-])") if generic else \
                re.compile(r"(?<![\w])" + re.escape(v) + r"(?![\w])", re.I)
            for m in rx.finditer(text):
                hits.append((v, text.count("\n", 0, m.start()) + 1))
    for t in ticker_forms:
        for m in re.finditer(re.escape(t), text, re.I):
            hits.append((t, text.count("\n", 0, m.start()) + 1))
    for m in re.finditer(r"\b(?:[a-z0-9-]+\.)+[a-z]{2,24}\b", text, re.I):
        if re.fullmatch(r"[\d.]+|[a-z]\.[a-z]|(?:e\.g|i\.e|etc|inc|corp|co|ltd|no|vs|fig)\.?", m.group(0), re.I):
            continue
        if not re.search(r"\.(?:com|net|org|io|ai|co|gov|edu|info|biz|[a-z]{2})(?:\b|$)", m.group(0), re.I):
            continue
        hits.append((m.group(0), text.count("\n", 0, m.start()) + 1))
    return hits


# ----------------------------------------------------------------------------- factor draws
def near_ratio(x):
    for p in range(1, 7):
        for q in range(1, 7):
            r = p / q
            if abs(x / r - 1) <= 0.02:
                return True
    return False


def draw_factors(n):
    """Half (rounded down, at least one) below 1 for k and, independently, for j."""
    nb = max(1, n // 2)
    def draw(lo, hi, signs):
        out = []
        for s in signs:
            while True:
                u = lo + (hi - lo) * (secrets.randbelow(10 ** 9) / 10 ** 9)
                out.append(s * u)
                break
        return out
    while True:
        sk = [-1] * nb + [1] * (n - nb)
        sj = [-1] * nb + [1] * (n - nb)
        # shuffle signs with secrets
        for arr in (sk, sj):
            for i in range(len(arr) - 1, 0, -1):
                r = secrets.randbelow(i + 1)
                arr[i], arr[r] = arr[r], arr[i]
        lk = draw(0.70, 1.40, sk)
        lj = draw(0.20, 0.50, sj)
        ks = [math.exp(x) for x in lk]
        js = [math.exp(x) for x in lj]
        if any(near_ratio(k) or near_ratio(j) or near_ratio(k * j) for k, j in zip(ks, js)):
            continue
        return ks, js


# ----------------------------------------------------------------------------- v7.1: screener JSON (Appendix H)
def tags_from_json(tag_json):
    """Tag-screener JSON -> list of (line_from, line_to, span, tag)."""
    out = []
    for t in tag_json.get("tags", []):
        tg = str(t.get("tag", "")).strip().upper()
        if tg not in TAGMAP:
            out.append((int(t["line"]), int(t["line"]), str(t["span"]), None))
        else:
            out.append((int(t["line"]), int(t["line"]), str(t["span"]), tg))
    return out


def identity_from_json(tag_json):
    return [(list(e.get("variants", [])), str(e.get("replacement")), bool(e.get("generic_word")))
            for e in tag_json.get("identity", [])]


def _span_positions(line, span):
    return [(m.start(), m.end()) for m in span_regex(span).finditer(line)] if span else []


def redaction_check(red_json, raw_by_name, tags_by_name):
    """Spec Stage 1 'Redaction check'. raw_by_name / tags_by_name are keyed by the dossier file names the
    redaction screener saw. Returns dict(accepted={name: [entries]}, rejected=[...], classes={...}, stop=bool, why=[])."""
    accepted = {n: [] for n in raw_by_name}
    rejected, why = [], []
    for e in red_json.get("redactions", []):
        d, item = e.get("dossier"), str(e.get("item", "")).strip().upper()
        if d not in raw_by_name:
            rejected.append(dict(e, reason="unknown dossier"))
            continue
        if item not in RED_ITEMS:
            rejected.append(dict(e, reason="names no redact-list item"))
            continue
        lines = raw_by_name[d].split("\n")
        ln = int(e.get("line", 0))
        if not (1 <= ln <= len(lines)) or e.get("span") not in lines[ln - 1]:
            rejected.append(dict(e, reason="span not found on its line"))
            continue
        pos = _span_positions(lines[ln - 1], e["span"])
        clash = False
        for (a, b, sp, tg) in tags_by_name.get(d, []):
            if a != ln or TAGMAP.get(tg or "") != "SHARES":
                continue
            for (ts, te) in _span_positions(lines[ln - 1], sp):
                if any(not (te <= s0 or ts >= e0) for s0, e0 in pos):
                    clash = True
        if clash:
            rejected.append(dict(e, reason="keep-list violation: span contains a SHARES-tagged figure"))
            continue
        accepted[d].append(dict(e, item=item))
    classes = {}
    for c in red_json.get("class_status", []):
        classes.setdefault(c.get("dossier"), {})[str(c.get("item", "")).upper()] = str(c.get("status", "")).strip().lower()
    for n in raw_by_name:
        for it in sorted(RED_ITEMS):
            st = classes.get(n, {}).get(it)
            if st not in ("redacted", "not present"):
                why.append(f"{n}: {it} status '{st}' (must be 'redacted' or 'not present')")
            n_acc = sum(1 for x in accepted[n] if x["item"] == it)
            if st == "redacted" and n_acc == 0:
                why.append(f"{n}: {it} marked redacted but no accepted entry")
            if st == "not present" and n_acc > 0:
                why.append(f"{n}: {it} marked not present but {n_acc} entries listed")
    for nt in red_json.get("methodology_notes", []):
        d = nt.get("dossier")
        if d not in raw_by_name:
            rejected.append(dict(nt, item="note", reason="unknown dossier"))
            continue
        lines = raw_by_name[d].split("\n")
        ln = int(nt.get("line", 0))
        if not (1 <= ln <= len(lines)) or nt.get("span") not in lines[ln - 1]:
            rejected.append(dict(nt, item="note", reason="note span not found on its line"))
            continue
        pos = [(m.start(), m.end()) for m in re.finditer(re.escape(nt["span"]), lines[ln - 1])]
        for (a, b, sp, tg) in tags_by_name.get(d, []):
            if a == ln and TAGMAP.get(tg or "") == "SHARES" and any(
                    not (te <= s0 or ts >= e0) for ts, te in _span_positions(lines[ln - 1], sp) for s0, e0 in pos):
                rejected.append(dict(nt, item="note", reason="keep-list violation: note would remove a SHARES-tagged figure"))
                break
    if rejected:
        why.append(f"{len(rejected)} entr{'y' if len(rejected) == 1 else 'ies'} rejected")
    return dict(accepted=accepted, rejected=rejected, classes=classes, stop=bool(why), why=why,
                soft_routes=red_json.get("soft_routes", []))


def ops_from_json(red_check, red_json, name):
    """Accepted redactions and methodology notes for one dossier, in apply_redactions' format."""
    reds = [dict(id=e["item"], line=int(e["line"]), span=e["span"], to=e.get("replacement") or "[redacted]")
            for e in red_check["accepted"][name]]
    notes = [dict(id=f"M{i + 1}", line=int(n["line"]), span=n["span"])
             for i, n in enumerate(x for x in red_json.get("methodology_notes", []) if x.get("dossier") == name)]
    return {"redactions": reds, "notes": notes}


def _nth_number(line, idx):
    ms = list(NUM.finditer(line))
    return float(ms[idx].group(0).replace(",", "")) if 0 <= idx < len(ms) else None


def _num_index(line, span):
    mm = span_regex(span).search(line) if span else None
    if not mm:
        return None
    p = mm.start()
    m = NUM.search(line, p)
    if not m or m.start() >= p + len(span):
        return None
    return sum(1 for x in NUM.finditer(line) if x.start() < m.start())


def _nth_half_unit(line, idx):
    """Half a unit of the last printed decimal of the idx-th number on the line (toolkit v8.0.1)."""
    ms = list(NUM.finditer(line))
    if not (0 <= idx < len(ms)):
        return None
    g = ms[idx].group(0)
    dec = len(g.split(".")[1]) if "." in g else 0
    return 0.5 * 10 ** (-dec)


def consistency_check(pre_text, post_text, triples, tol=0.02):
    """Spec Stage 1c check 3. Locates each triple's number by its index among the numbers on its line in the
    pre-transform text, reads the same index in the post-transform text (scaling keeps the count of numbers on a
    line; identity masking runs after this check).
    v8.0.1: after the transform, the tolerance also allows the rounding that format-preserving rescaling adds
    (each figure keeps its printed decimals): |EPS*shares*f - NI| <= tol*|NI| + f*(|shares|*h_eps + |EPS|*h_sh
    + h_eps*h_sh) + h_ni, where h is half a unit of each figure's last printed decimal. A tag error moves the
    product by a factor k or j (at least e^0.2), which this allowance does not cover. The pre-transform check is
    unchanged."""
    pre, post = pre_text.split("\n"), post_text.split("\n")
    res = []
    for t in triples:
        vals, halves = {}, {}
        for key in ("eps", "shares", "net_income"):
            ref = t.get(key) or {}
            ln = int(ref.get("line", 0))
            if not (1 <= ln <= len(pre)):
                vals[key] = (None, None)
                continue
            idx = _num_index(pre[ln - 1], str(ref.get("span", "")))
            vals[key] = (None, None) if idx is None else (_nth_number(pre[ln - 1], idx), _nth_number(post[ln - 1], idx))
            halves[key] = None if idx is None else _nth_half_unit(post[ln - 1], idx)
        row = dict(period=t.get("period"), basis=t.get("basis"))
        uf = t.get("unit_factor")
        try:
            uf = float(uf) if uf is not None else 1.0
        except (TypeError, ValueError):
            uf = 1.0
        for stage, i in (("pre", 0), ("post", 1)):
            e, s_, n = vals["eps"][i], vals["shares"][i], vals["net_income"][i]
            # a triple that cannot be located fails (spec Stage 1c, check 3)
            slack = 0.0
            if stage == "post" and None not in (e, s_, n) and None not in (halves.get("eps"), halves.get("shares"), halves.get("net_income")):
                he, hs, hn = halves["eps"], halves["shares"], halves["net_income"]
                slack = abs(uf) * (abs(s_) * he + abs(e) * hs + he * hs) + hn
            ok = False if None in (e, s_, n) or not n else abs(e * s_ * uf - n) <= tol * abs(n) + slack
            row[stage] = dict(eps=e, shares=s_, net_income=n, unit_factor=uf, ok=ok, located=None not in (e, s_, n),
                              err=(abs(e * s_ * uf - n) / abs(n)) if (None not in (e, s_, n) and n) else None,
                              rounding_allowance=(slack / abs(n)) if (n and stage == "post") else 0.0)
        res.append(row)
    return res
