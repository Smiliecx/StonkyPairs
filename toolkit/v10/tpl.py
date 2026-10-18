#!/usr/bin/env python3
"""Template extraction, instantiation and mechanical diff -- toolkit v10 (SPEC v10).

Templates are read from the spec copy shipped with the toolkit (spec_v10.md beside this file),
or from the path in the environment variable TOOLKIT_SPEC.

  python3 tpl.py list                    # every template name, length and first line
  python3 tpl.py diff NAME FILE [--masked] [--card] [--validation]   # diff an instantiated text against its template

v10 (T6): Appendix G carries a multi-line validation block, kept (marker removed) with validation=True and removed
whole (through its closing blank line) otherwise; its slot <BASELINE> is a SHA-256. New card slots: <CARD_L12>,
<CARD_OFFBASE>, <CARD_OFFBASE_FOLD>, <CARD_DEBTDED>, <CARD_SRC_D/A/C>, <CARD_WMULT>.
"""
import re, sys, json, hashlib, os

SPEC = os.environ.get("TOOLKIT_SPEC") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "spec_v10.md")
MASK_LABEL = "the Company"   # v9: fills <TICKER> in Stage-2/4/4b templates; packs are not masked (SPEC v9 N1)
SLOT_NAMES = ["TICKER", "UNIT", "PACK", "RUN", "CRITIQUE", "REDLOG", "OUT", "OUT2", "SCRATCH", "FILES", "N_RUNS",
              "REPLICATES", "MODEL", "TIMESTAMP", "SCRIPT_SHA", "AS_OF", "BASELINE"]


def spec_text():
    return open(SPEC, encoding="utf-8").read()


def section(letter):
    t = spec_text()
    m = re.search(r"^## Appendix " + letter + r" .*$", t, re.M)
    rest = t[m.end():]
    n = re.search(r"^## |^---\s*$", rest, re.M)
    return rest[:n.start()] if n else rest


def unquote(lines):
    out = []
    for ln in lines:
        if ln.startswith("> "):
            out.append(ln[2:])
        elif ln.rstrip() == ">":
            out.append("")
    return "\n".join(out).strip("\n") + "\n"


def blockquotes(sec):
    """Return list of contiguous blockquote blocks in a section."""
    blocks, cur = [], []
    for ln in sec.split("\n"):
        if ln.startswith(">"):
            cur.append(ln)
        else:
            if cur:
                blocks.append(unquote(cur))
                cur = []
    if cur:
        blocks.append(unquote(cur))
    return blocks


def template(name):
    if name == "B":
        return blockquotes(section("B"))[0]
    if name == "C":
        sec = section("C")
        return sec.strip("\n") + "\n"
    if name == "E":
        return blockquotes(section("E"))[0]
    if name == "F":
        return blockquotes(section("F"))[0]
    if name == "G":
        return blockquotes(section("G"))[0]
    if name == "J":
        return blockquotes(section("J"))[0]
    if name in ("I_card", "I_headline"):
        b = blockquotes(section("I"))
        return b[0] if name == "I_card" else b[1]
    h = section("H")
    bq = blockquotes(h)
    if name == "H_redaction":
        return bq[0]
    if name == "H_tag":
        return bq[1]
    if name in ("H_probe", "L_probe"):
        raise KeyError(f"{name}: the identification probe is removed in SPEC v9 (N1)")
    if name == "H_auditor":
        return bq[2]
    if name == "H_writer":
        return bq[3]
    if name.startswith("L_"):
        key = {"L_redaction": "Redaction screener", "L_tag": "Tag screener",
               "L_auditor": "Neutrality auditor",
               "L_run": "Stage-2 run", "L_critic": "Critic", "L_verifier": "Verifier", "L_writer": "Stage-6 writer"}[name]
        m = re.search(r"^- \*\*" + re.escape(key) + r":\*\* \"(.*)\"$", h, re.M)
        return m.group(1)
    raise KeyError(name)


VALIDATION_IF = "⟨IF VALIDATION ≠ NONE:⟩"


def strip_conditionals(t, mandate=None, stage7=False, validation=False):
    lines = t.split("\n")
    out = []
    skip_blank = False
    skip_block = False
    for ln in lines:
        if skip_block:   # v10: the rest of the validation block, through its closing blank line
            if ln.strip() == "":
                skip_block = False
            continue
        if VALIDATION_IF in ln:
            if not validation:
                skip_block = True
                continue
            ln = ln.replace(VALIDATION_IF + " ", "")
        if "⟨IF USER_MANDATE ≠ NONE:⟩" in ln:
            if mandate is None:
                skip_blank = True
                continue
            ln = ln.replace("⟨IF USER_MANDATE ≠ NONE:⟩ ", "").replace("⟨verbatim text⟩", mandate)
        if "⟨IF STAGE 7:⟩" in ln:
            if not stage7:
                skip_blank = True
                continue
            ln = ln.replace("⟨IF STAGE 7:⟩ ", "")
        if skip_blank and ln.strip() == "":
            skip_blank = False
            continue
        skip_blank = False
        out.append(ln)
    return "\n".join(out)


def instantiate(name, slots, mandate=None, stage7=False, validation=False):
    t = strip_conditionals(template(name), mandate, stage7, validation)
    if "FILES" in slots:  # Appendix H: one path per line
        t = t.replace(" ⟨FILES⟩ ", "\n" + slots["FILES"] + "\n")
    for k, v in slots.items():
        t = t.replace("⟨" + k + "⟩", v)
    masked = {k for k, v in slots.items() if v == "⟨" + k + "⟩"}
    for v in slots.values():
        masked |= set(re.findall("⟨([A-Z_0-9]+)⟩", v))
    left = [x for x in re.findall("⟨([A-Z_0-9]+)⟩", t) if x not in masked]
    if left:
        raise ValueError(f"unfilled slots in {name}: {left}")
    return t


INLINE_IF = re.compile(r"⟨IF [A-Z_]+ ≠ NONE:⟩")


def regex_for(name, mandate=None, stage7=False, card=False, validation=False):
    t = strip_conditionals(template(name), mandate, stage7, validation)
    if INLINE_IF.search(t):
        # Inline conditionals (Appendix I headline): each conditional tail is optional in the diff.
        head, *tails = INLINE_IF.split(t)
        rx_h, used = regex_for_text(head.rstrip("\n"), card)
        rx = rx_h[1:-len(r"\s*$")]
        for tl in tails:
            r_t, used_t = regex_for_text(tl.rstrip("\n").lstrip(" "), card, used)
            rx += "(?: ?" + r_t[1:-len(r"\s*$")] + ")?"
        return "^" + rx + r"\s*$", used
    return regex_for_text(t, card)


def regex_for_text(t, card=False, used=None):
    parts = re.split("(⟨[A-Z_0-9]+⟩)", t)
    rx, used = "", (used if used is not None else {})
    for p in parts:
        m = re.fullmatch("⟨([A-Z_0-9]+)⟩", p)
        if m:
            nm = m.group(1)
            ok = nm in SLOT_NAMES or (card and nm.startswith("CARD_"))
            if not ok:
                rx += re.escape(p)
                continue
            if nm in used:
                rx += "(?P=" + used[nm] + ")"
            else:
                g = nm + "_" + str(len(used))
                used[nm] = g
                rx += "(?P<" + g + ">.*?)"
        else:
            # whitespace adjacent to a slot may be any whitespace (FILES are one path per line)
            esc = re.escape(p)
            esc = re.sub(r"^(\\ )+", r"\\s+", esc)
            esc = re.sub(r"(\\ )+$", r"\\s+", esc)
            rx += esc
    return "^" + rx + r"\s*$", used


MASKED = re.compile(r"^⟨[A-Z_0-9]+⟩$")
PATH_RX = re.compile(r"^[\w./~-]*(?:⟨[A-Z_0-9]+⟩[\w./~-]*)*$")
NUM = r"[+−-]?[\d,]*\.?\d+%?"
CARD_RULES = {
    "CARD_T": rf"^(?:{NUM}|n/a)$", "CARD_DF": r"^\d+$", "CARD_RUNS": r"^\d+$", "CARD_TIER_N": r"^\d+$", "CARD_SEATS": r"^\d+$",
    "CARD_CAP": r"^\d+$", "CARD_ACQ": r"^\d+$", "CARD_ACQ_U": r"^\d+$", "CARD_DENOM": r"^\d+$", "CARD_NEAR": r"^\d+$",
    "CARD_NOTREE": r"^\d+$", "CARD_ALT_UP": r"^\d+$", "CARD_ALT_DN": r"^\d+$", "CARD_ALT_NONE": r"^\d+$",
    "CARD_ALT_K": r"^\d+$", "CARD_L11": rf"^(?:{NUM} / {NUM}|n/a)$",   # L11: v9 N2 (review), n/a when no seat is valued
    "CARD_L12": rf"^(?:{NUM} / {NUM}|n/a)$",   # v10 T2: n/a when no retained run is measured
    "CARD_OFFBASE": r"^\d+$", "CARD_OFFBASE_FOLD": r"^\d+$", "CARD_DEBTDED": r"^\d+$",
    "CARD_SRC_D": r"^\d+$", "CARD_SRC_A": r"^\d+$", "CARD_SRC_C": r"^\d+$",
    "CARD_WMULT": r"^(?:\d+\.\d{3}|n/a)$",
    "CARD_R1": rf"^(?:{NUM}|n/a)$", "CARD_R2": rf"^(?:{NUM}|n/a)$", "CARD_R3": rf"^(?:{NUM}|n/a)$",
    "CARD_K0": r"^(?:\d+(?:\.\d+)?:1|n/a)$", "CARD_K1": r"^(?:\d+(?:\.\d+)?:1|n/a)$",
    "CARD_K2": r"^(?:\d+(?:\.\d+)?:1|n/a)$", "CARD_K3": r"^(?:\d+(?:\.\d+)?:1|n/a)$",
    "CARD_BK": rf"^(?:{NUM} \(90% CI {NUM} to {NUM}\)|n/a)$", "CARD_BJ": rf"^(?:{NUM} \(90% CI {NUM} to {NUM}\)|n/a)$",
    "CARD_VDATE": r"^\d{4}-\d\d-\d\d(?:, \d{4}-\d\d-\d\d)*$", "CARD_SDATE": r"^\d{4}-\d\d-\d\d(?:, \d{4}-\d\d-\d\d)*$",
    "CARD_MI": r"^\d{4}-\d\d-\d\d [A-Z]{3} [0-9a-f]{64}$",
    "CARD_PROBE": r"^(?:[A-Z] (?:NOT )?IDENTIFIED(?:; [A-Z] (?:NOT )?IDENTIFIED)*|n/a)$",
    "CARD_MFLAG": r"^(?:NONE|PRICE-MEMORY SUSPECTED|SCALE-DEPENDENCE \(possible price memory\))$",
    "CARD_BRIDGE_V6": rf"^(?:{NUM}|n/a)$", "CARD_BRIDGE_RUNS": rf"^(?:[A-Z] {NUM}(?:; [A-Z] {NUM})*|n/a)$",
    "CARD_S7": r"^(?:run|not run)$", "CARD_MANDATE": r"^(?:NONE|conditional)$",
    "CARD_TIER": r"^(?:Exceptional|High Quality|Average|Below Average)$",
    "CARD_THIN": r"^(?:n/a|(?:Cash flow|Capex|SBC|Share count|Tax|Acquisitions) \([A-Z](?:, [A-Z])*\)"
                 r"(?:; (?:Cash flow|Capex|SBC|Share count|Tax|Acquisitions) \([A-Z](?:, [A-Z])*\))*)$",
}
CARD_TEXT = {"CARD_BIGROW"}   # checked against the ledger row names of frozen_arith.py
CARD_LEVER = rf"^{NUM} / {NUM}$"


def _ledger_rows():
    try:
        src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "frozen_arith.py"), encoding="utf-8").read()
        return set(re.findall(r'^ROW_[A-Z0-9_]+ = "([^"]+)"', src, re.M))
    except OSError:
        return set()
PATH_SLOTS = {"OUT", "OUT2", "SCRATCH", "RUN", "PACK", "CRITIQUE", "REDLOG"}
FORMATS = {"N_RUNS": r"^\d{1,3}$", "SCRIPT_SHA": r"^[0-9a-f]{64}$", "BASELINE": r"^[0-9a-f]{64}$",
           "TIMESTAMP": r"^\d{4}-\d\d-\d\d[T ]\d\d:\d\d(:\d\d(\.\d+)?)?(Z|[+-]\d\d:?\d\d)?$",
           "AS_OF": r"^\d{4}-\d\d-\d\d$", "REPLICATES": r"^[A-Z] → \d+(, [A-Z] → \d+)*$", "MODEL": r"^[\w.:/-]+$"}


def slot_type_error(nm, v):
    """Returns an error string if a slot value fails its type; None if it passes. Masked placeholders pass."""
    if MASKED.match(v.strip()):
        return None
    if nm in PATH_SLOTS:
        return None if (v and "\n" not in v and PATH_RX.match(v)) else "not a single path without whitespace"
    if nm == "FILES":
        lines = v.strip("\n").split("\n")
        bad = [ln for ln in lines if not ln or not PATH_RX.match(ln)]
        return None if not bad else f"not one path per line: {bad[:2]}"
    if nm in FORMATS:
        return None if re.match(FORMATS[nm], v) else f"does not match {FORMATS[nm]}"
    if nm.startswith("CARD_"):
        if "\n" in v:
            return "contains a line break"
        if nm in CARD_RULES:
            return None if re.match(CARD_RULES[nm], v) else "fails the Appendix-I slot rule"
        if nm in CARD_TEXT:
            return None if v in _ledger_rows() else "not a ledger row name"
        if re.fullmatch(r"CARD_L\d+", nm):
            return None if re.match(CARD_LEVER, v) else "not a lever (change / run-noise SDs)"
        return None if re.match(rf"^{NUM}$", v) else "not a number"
    if nm in ("TICKER", "UNIT") and ("\n" in v or len(v) > 80):
        return "not a short name or unit"
    return None


def diff(name, text, masked_stage=False, mandate=None, stage7=False, card=False, validation=False):
    rx, used = regex_for(name, mandate, stage7, card, validation)
    m = re.match(rx, text, re.S)
    if not m:
        # locate first divergence for the report
        t = strip_conditionals(template(name), mandate, stage7, validation)
        a, b = t.split("\n"), text.split("\n")
        first = None
        for i in range(max(len(a), len(b))):
            x = a[i] if i < len(a) else None
            y = b[i] if i < len(b) else None
            if x != y and not (x and "⟨" in x):
                first = (i + 1, x, y)
                break
        return dict(ok=False, reason="text outside declared slots", first_divergence=first)
    vals = {g: m.group(g) for g in m.groupdict()}
    probs = []
    for nm, g in used.items():   # typed slot values (spec Stage 0.5, Step 1)
        v = vals[g]
        if v is None:
            continue
        err = slot_type_error(nm, v)
        if err:
            probs.append(f"slot {nm}: {err}")
    for nm, g in used.items():
        v = vals[g]
        if nm == "TICKER" and masked_stage and v != MASK_LABEL:
            probs.append(f"TICKER slot '{v}' != MASK_LABEL")
        if nm == "UNIT" and masked_stage and not re.fullmatch(r"[A-Z]{3} per share", v):
            probs.append(f"UNIT slot '{v}' does not match '[A-Z]{{3}} per share'")
        if nm in ("TICKER",) and not masked_stage and v.strip() == "":
            probs.append("empty TICKER")
    return dict(ok=not probs, reason="; ".join(probs) if probs else "matches template; slots only",
                slots={nm: vals[g] for nm, g in used.items()})


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


if __name__ == "__main__":
    names = ["B", "C", "E", "F", "G", "J", "I_card", "I_headline", "H_redaction", "H_tag", "H_auditor",
             "H_writer", "L_redaction", "L_tag", "L_auditor", "L_run", "L_critic", "L_verifier", "L_writer"]
    if len(sys.argv) > 1 and sys.argv[1] == "diff":
        txt = open(sys.argv[3], encoding="utf-8").read()
        print(json.dumps(diff(sys.argv[2], txt, masked_stage="--masked" in sys.argv, card="--card" in sys.argv,
                              validation="--validation" in sys.argv),
                         ensure_ascii=False, indent=1))
        sys.exit(0)
    for n in names:
        t = template(n)
        print(f"== {n}: {len(t)} chars; first: {t[:70]!r}")
