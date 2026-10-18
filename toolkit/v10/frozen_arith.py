#!/usr/bin/env python3
"""frozen_arith.py -- frozen arithmetic for the multi-stage valuation pipeline, toolkit v10 (SPEC v10).

Default mode is SPEC v10. Four compatibility modes reproduce earlier arithmetic exactly:
  --spec v9   (or "spec_version": "v9" in a config): the SPEC v9 arithmetic (eight seats; no v10 checks or rows);
  --spec v8   (or "spec_version": "v8" in a config): the SPEC v8 arithmetic (masked executions, memory test);
  --spec v7.1 (or "spec_version": "v7.1" in a config): the SPEC v7.1 arithmetic (step tiers);
  --spec v7   (or "spec_version": "v7"): the SPEC v7 arithmetic, for the replay gate (spec Stage 5b, "Replay gate").

v10 differences (spec T1-T4, T6), on top of v9. The seat, margin and BUY arithmetic is v9's (the same functions):
  * T4 roster: seven seated investors (Marcus, Sophie, Claire, Graham, Walter, Helena, Alexander). A seat named
    Simon (as Victor and Max) is outside the roster: logged C5 and kept out of every statistic.
  * T1-T4 logged checks, never corrected and moving no number (v10_checks): a seat whose discount_rate is missing or
    not MARKET_INPUTS' risk-free + ERP (0.005pp; the run's macro_base only where the configuration has none), or whose
    fair_value_macro_base differs from its fair_value (0.1% / 0.01), is off the macro base (C2); the run's macro_base,
    risk_free and erp against MARKET_INPUTS; a non-zero debt_deducted_per_share (C1: a claim deducted from cash flow to
    equity); a missing debt_deducted_per_share or net_claims_per_share (C8); systematic_risk_class (C8); the risk
    register (closed channel list incl. non_break_branch, a size or a reason, fv_mapping only for Walter or Alexander,
    one risk in two channels for one seat, seats with no entry; C6); Walter's management_grade (six integer components
    -2..+2, score = sum, multiplier = 1 + 0.015 x score within 0.0005, CAUTION/FAIL caps, two FAILs without NO BUY;
    C5) and Alexander's earnings_quality mapping (+0.10 above 80, 0 from 60 to 80, -0.15 below; C5).
  * T4 NO BUY: a reported no_buy is honoured only for Walter with two or more FAIL gates (or by a verifier patch);
    any other is logged (C7) and the seat kept.
  * T2 debt row (the v9 count reapplied): every headline seat's fair value less its run's net_claims_per_share, the
    required margin held; runs with no or zero net claims keep their headline. A ledger row and card lever <CARD_L12>
    (n/a when no retained run is measured); never the card's largest sensitivity.
  * T6 channel monitor (descriptive): seats off the base; seat-weighted terminal growth, five-year forecast growth,
    quality score, break_p and tail term; Walter's multiplier and score; runs with debt deducted and risk-class
    counts; the register by channel with a derived BUY effect; the debt row's change; a seat-mapping table (T4).
  * Card: <CARD_L12>, <CARD_OFFBASE>, <CARD_OFFBASE_FOLD>, <CARD_DEBTDED>, <CARD_SRC_D/A/C>, <CARD_WMULT>.
  * rebase prints the route-(d) patch set for a seat off the macro base: fair_value set to fair_value_macro_base,
    every non-break branch scaled by the same ratio, the break value held, fair_value_macro_base unchanged. A fold
    finding whose patches have exactly that form is labelled approximate in the fold log.
  * undebt prints the patch set for a run that deducted claims from cash flow to equity: debt_deducted_per_share
    added back to every seat's values and tree and to the balance-sheet add.
  * An induced-field row for the rate rule.

v9 differences (spec N1, N2, N5, N6), on top of v8. The seat and BUY arithmetic is unchanged:
  * N1 no masking or rescaling: a v9 execution's configuration carries k = j = 1 for every run. The
    scale-dependence memory test (per ticker and pooled for the season) is not run, and the Decision Card
    has no memory or bridge line. Back-scaling by a configured k and j is kept, so masked executions of
    earlier versions still replay in v9 mode.
  * N2 alternative-denominator row: every headline seat on fair_value_alternative_denominator, its
    required margin held fixed; a seat without the field keeps its fair value (logged, C8). The field is a
    companion patch path and scales with a fair-value patch, as fair_value_rf_plus_50bp does.
    The row counts each run's direction (alternative above / below the declared denominator, or none) and the
    headline seats valued; a seat whose alternative fair value is zero or negative is left out of the row (NO BUY
    there; logged); with no seat valued the card prints n/a and the row is not a largest-sensitivity candidate.
    Logged (C1/C4/C8, moving nothing): a basis outside period|margin|none; "none" without the two equalities; an
    alternative / declared ratio outside 0.5-2.0 or of opposite sign; a seat whose alternative implies a different
    scaling of its operating value than the two denominators do.
  * N5 zero acquisition spend: when the pack shows no acquisition cash (frame.acq_cash_by_year empty or summing to 0)
    and frame.acq_spend_normalised_per_share is 0, every declared growth_basis x acq_spend_deducted pair counts as
    matched, and both acquisition rows equal the headline (logged). A run that excludes a deal from non-zero
    acquisition cash is still checked for mismatches.
  * N6 quality_tier_modal must name a tier; anything else is logged (C8). It moves no number.
  * The verifier's "mechanism" flag is read strictly in v9 (true only for JSON true or "true"; anything else that
    is not a boolean is logged).

v8 differences (spec G1-G3), on top of v7.1:
  * G1 quality premium: base(tier) is replaced by pi(quality_score), piecewise-linear through
        (52.5, 0.40), (67.5, 0.325), (82.5, 0.225), (95, 0.125); 0.40 at or below 52.5, 0.125 at or above 95.
    The tier is still derived from the score (FRAMEWORK table) as a label (Rule 8, tier distribution). A seat
    with no numeric score takes pi at its reported tier's midpoint score (logged, C7).
    required = clamp(pi(score) + p*L, 0.10, 0.60); AT CAP, NO BUY, L and the floor as in v7.1.
  * G2 roster: eight seated investors (Simon, Marcus, Sophie, Claire, Graham, Walter, Helena, Alexander).
    A Victor or Max seat, or a seat with irr_entry true, is not part of a v8 committee: it is logged and kept out
    of every statistic (replayed v7 summaries keep their v7 IRR segregation, which has the same effect).
  * G3 margin-rule alternatives, computed from the same seats and trees and never averaged into the headline:
        step tiers    : the v7.1 rule, base(tier) + p*L, clamped, AT CAP as v7.1;
        tuned Victor  : TUNED_C x the expected value of the seat's floored tree;
        tuned Max     : the price P with E[(V-P)+] = TUNED_K x E[(P-V)+] over the floored tree,
                        i.e. the 1/(1+TUNED_K) expectile;
    each headline = the run's own-weight mean over headline seats (a seat with no valid tree is left out of
    the two tuned lines and its weight dropped; logged). Constants fixed in spec v8: TUNED_K 7.75, TUNED_C 0.670.

v7.1 differences (spec F1, F4, F5):
  * AT CAP: a seat with base(tier) + p*L > 0.60 gets required = 0.60 and STAYS in the headline. NO BUY only
    for a FRAMEWORK uninvestability rule: a reported no_buy naming its rule in no_buy_reason_or_null, or a
    verifier's no_buy patch. A no_buy with no reason on a seat above 0.60 is treated as AT CAP (logged, C7).
  * L = 1 - (break value after floor) / fair_value_macro_base, floored at 0. If fair_value_macro_base is
    missing, it is estimated log-linearly in the rate from fair_value and fair_value_rf_plus_50bp, and logged.
  * Denominator count: if frame.denominator_count_m (v7 summaries: share_count_m) differs from
    per_share_count_m by more than 0.1%, every per-share value is rescaled on its operating part
    (v - bsa) * denominator_count_m / per_share_count_m + bsa, before any seat is recomputed. Logged (C1).
  * Acquisition matching: growth_basis x acq_spend_deducted tabulated; mismatches counted; two ledger rows
    (every seat organic; every seat including acquisitions) from fair_value_other_acquisition_basis.
  * New convention row 4: denominator on the period-weighted count.

Ticker-generic. Contains no company-specific constant. One file serves every ticker of the
toolkit version; its SHA-256 is listed in TOOLKIT_MANIFEST.md, whose own SHA-256 is pre-registered.

Implements (SPEC v7.1 arithmetic; default mode v8 adds the quality premium and G2-G3 above):
  * the Appendix-B margin arithmetic:
        base(tier): Exceptional 0.125, High Quality 0.225, Average 0.325, Below Average 0.40
        tier from quality_score: >=90 Exceptional, >=75 High Quality, >=60 Average, else Below Average
        every tree branch value is raised to Helena's floor (if not null)
        p = break-branch probability
        L = max(0, 1 - (break value after floor) / fair_value_macro_base)
        tail_term = p * L
        required = clamp(base(tier) + tail_term, 0.10, 0.60); BUY = fair_value * (1 - required)
        AT CAP if base(tier) + tail_term > 0.60 before clamping (required 0.60; the seat stays in)
        NO BUY only under a FRAMEWORK rule (no_buy with no_buy_reason_or_null, or a verifier patch)
        headline = sum(w*buy)/sum(w) over seats that are not IRR seats (Victor, Max, or irr_entry)
                   and not NO BUY, with the run's own Phase-0 weights;
  * the F1 denominator-count normalisation, before any seat is recomputed;
  * the Stage-3 per-seat recompute from trees and the Stage-3 statistics, including the F4 acquisition rows;
  * the Stage-5 point estimate, interval and sensitivity ledger;
  * the Stage-5b patch validation and fold;
  * the Appendix-I Decision Card.
Compatibility mode (--spec v7): L against fair_value; NO BUY above 0.60; no normalisation; v7 patch list.

USAGE (verifiers)
  python3 frozen_arith.py recompute RUN_FILE
      RUN_FILE is a run .md ending with "## MACHINE SUMMARY" + JSON, or a .json summary.
      Recomputes every seat and the headline with the pre-registered arithmetic (run units).
  python3 frozen_arith.py patch RUN_FILE PATCHES_FILE
      PATCHES_FILE: a JSON list of {"path","from","to"} (or an object with "changed_inputs").
      Validates the patches against the closed list, applies them, recomputes, and prints the
      blind headline, the patched headline and the delta (run units).
  python3 frozen_arith.py verify RUN_FILE VERIFICATION_FILE
      VERIFICATION_FILE: a .json or .md holding {"rulings":[...],"joint_changed_inputs":[...]}.
      Prints each CONFIRMED+quantified finding's standalone delta and the joint delta.
  python3 frozen_arith.py rebase RUN_FILE INVESTOR
      v10 (T1): prints the patch set for a seat whose rate is not the macro base, as {"changed_inputs":[...]}:
      fair_value -> fair_value_macro_base, every tree value x the same ratio (an approximation), and
      fair_value_macro_base unchanged. Exit 2 if the seat reports no usable fair_value_macro_base.
  python3 frozen_arith.py undebt RUN_FILE
      v10 (T2): prints the patch set adding the run's debt_deducted_per_share back to every seat's fair value,
      fair_value_macro_base, companion fair values and tree values, and to balance_sheet_add_per_share.
ORCHESTRATOR
  python3 frozen_arith.py selftest
  python3 frozen_arith.py stage3 CONFIG_JSON OUT_DIR
  python3 frozen_arith.py stage5 CONFIG_JSON OUT_DIR

Closed patch-path list (Appendix F, v7.1):
  investors.<Investor>.fair_value                  (needs a fair_value_macro_base patch too, from = to if unchanged,
                                                    whenever the seat reports fair_value_macro_base)
  investors.<Investor>.fair_value_macro_base       (sets the seat's L)
  investors.<Investor>.tree.<branch>.p / .value   (to=null removes a branch; a new name adds one, needs both)
  investors.<Investor>.quality_score              (quality_tier patch allowed only if it matches the score)
  investors.<Investor>.no_buy                      (FRAMEWORK uninvestability rule only; the 0.60 cap is never a patch)
  investors.<Investor>.growth_basis / .acq_spend_deducted
                                                   (only with an explicit fair_value_other_acquisition_basis patch)
  frame.weights.<Investor>                         (0 to 2.0)
  helena_floor.floor_per_share_or_null
  investors.<Investor>.break_p / .break_loss       (only for a seat with no valid tree)
  companions: investors.<Investor>.fair_value_rf_plus_50bp, investors.<Investor>.fair_value_other_acquisition_basis,
              frame.valuation_date, frame.per_share_count_date, frame.balance_sheet_add_per_share,
              and in v9 investors.<Investor>.fair_value_alternative_denominator
              (only together with fair-value or tree patches)
  Share counts are never patched: the script normalises denominator_count_m against per_share_count_m itself.
  (--spec v7 keeps the v7 list, including frame.per_share_count_m.)

Fixed numerical conventions of this script:
  * probability-sum tolerance 0.005; base-equals-FV tolerance max(0.1% of FV, 0.01 unit);
  * a patch "from" matches the current value if equal within half a unit of its last printed
    decimal (at least 2 decimals) or 1e-6;
  * years between dates = days / 365.25;
  * trimmed mean drops one highest and one lowest headline when N >= 6;
  * the interval half-width is t(0.90, df) * s / sqrt(N), df = N - D.
"""
import sys, os, json, math, re, copy, itertools, statistics, hashlib, datetime

# ----------------------------------------------------------------------------- constants
TIERS = ["Exceptional", "High Quality", "Average", "Below Average"]
TIER_BASE = {"Exceptional": 0.125, "High Quality": 0.225, "Average": 0.325, "Below Average": 0.40}
CLAMP_LO, CLAMP_HI, NOBUY_BOUND = 0.10, 0.60, 0.60
RULE4_MIN = 0.10
IRR_NAMES = {"victor", "max"}
COMMITTEE = ["victor", "simon", "marcus", "sophie", "claire", "max", "graham", "walter", "helena", "alexander"]
EPS = 1e-9
SPEC = "v10"           # "v9", "v8", "v7.1" or "v7" by --spec or cfg["spec_version"] (compatibility modes)
SPECS = ("v10", "v9", "v8", "v7.1", "v7")
PREMIUM_POINTS = [(52.5, 0.40), (67.5, 0.325), (82.5, 0.225), (95.0, 0.125)]   # v8 G1: (quality score, premium)
TIER_MID_SCORE = {"Exceptional": 95.0, "High Quality": 82.5, "Average": 67.5, "Below Average": 52.5}
TIER_CUTS = (60.0, 75.0, 90.0)
NEAR_CUT = 3.0          # v8 card: seats within 3 points of a tier cut-off
TUNED_K = 7.75          # v8 G3 tuned Max: upside TUNED_K x downside -> the 1/(1 + TUNED_K) expectile
TUNED_C = 0.670         # v8 G3 tuned Victor: TUNED_C x the floored tree's expected value
ROSTER_V8 = ["simon", "marcus", "sophie", "claire", "graham", "walter", "helena", "alexander"]
ROSTER_V10 = ["marcus", "sophie", "claire", "graham", "walter", "helena", "alexander"]   # v10 T4: Simon merged into Walter
V10_UNSEATED = {"simon"}
V10_NOBUY_RULE = True   # v10 T4: only Walter's two FAILs make NO BUY (switched off only inside the shared self-test cases)
WALTER_K = 0.015        # v10 T4: Walter's multiplier = 1 + WALTER_K x score (score -12..+12)
GRADE_COMPONENTS = ("capital_allocation", "trust_guidance", "incentive_alignment", "insider_transactions",
                    "board_governance", "returns_vs_sector")
GATE_COMPONENT = {"trust": "trust_guidance", "incentive_alignment": "incentive_alignment",
                  "board_governance": "board_governance", "capital_structure": "capital_allocation"}
CHANNELS = ("base_cash_flows", "break_branch", "quality_score", "fv_mapping", "non_break_branch", "not_priced")   # v10 T3
RISK_CLASSES = ("defensive", "average", "cyclical")  # v10 T1 (descriptive)
RATE_TOL = 0.005        # v10 T1: percentage points between a seat's rate and the macro base
LINE_STEP = "Step tiers (SPEC v7.1 rule)"
LINE_VICTOR = "EV rule, tuned Victor (0.67 × tree expected value)"
LINE_MAX = "Expectile rule, tuned Max (expected upside 7.75 × expected downside)"
LINE_EVP = "EV × (1 − quality premium) (ledger only)"
LINES = (("buy_step", LINE_STEP), ("buy_victor", LINE_VICTOR), ("buy_max", LINE_MAX))   # on the card
LINES_ALL = LINES + (("buy_evp", LINE_EVP),)                                              # tables and ledger
SPEC_GIVEN = False      # set when --spec is passed on the command line
MECH_VERSION = {"v10": "v10", "v9": "v9", "v8": "v8-grad", "v7.1": "v7.1-tail", "v7": "v7-tail"}
DENOM_TOL = 0.001      # F1: relative difference above which the denominator count is normalised

INTERVAL_LABEL = ("80% confidence interval for this pipeline's expected BUY on these packs, with this model "
                  "and this orchestration. A fresh execution's figure is expected within a range √2 wider. "
                  "Neither range covers the items in the sensitivity ledger.")

ROW_BP_DN = "Break probability −5pp on every headline seat"
ROW_BP_UP = "Break probability +5pp on every headline seat"
ROW_VDATE = "Valuation date rolled to the pack date"
ROW_SDATE = "Share-count date"
ROW_BOTH = "Valuation date and share-count date (both)"
ROW_RF = "Risk-free +50bp"
ROW_MEM = "Memory control: β̂ₖ and β̂ⱼ with 90% CIs, and any flag"
ROW_INFL = "Published figure without the single finding whose removal moves it most"
ROW_CONTRAST = "Dossier contrast: t, p and camp means"
ROW_MEAN = "Point rule: equal-weighted mean"
ROW_MEDIAN = "Point rule: median"
ROW_DENOM = "Denominator on the period-weighted count instead of the per-share count"
ROW_ACQ_ORG = "Acquisitions: every seat on the organic basis"
ROW_ACQ_INC = "Acquisitions: every seat including acquisitions"
ROW_ALTDEN = "Alternative denominator: every seat on its run's alternative denominator"   # v9 N2
ROW_DEBT = "Debt: net claims deducted again (the v9 count)"   # v10 T2 (never the card's largest sensitivity)


def v71():
    """True in v7.1 and v8 (they share the v7.1 arithmetic apart from the quality premium)."""
    return SPEC != "v7"


def v8():
    """True in v8, v9 and v10 (they share the quality premium and the margin-rule lines)."""
    return SPEC in ("v8", "v9", "v10")


def v9():
    """True in v9 and v10 (v10 keeps every v9 feature: N1, N2, N5, N6)."""
    return SPEC in ("v9", "v10")


def v10():
    return SPEC == "v10"


def committee():
    """The seats whose weights are tabulated: seven in v10, eight in v8 and v9, ten before."""
    return ROSTER_V10 if v10() else ROSTER_V8 if v8() else COMMITTEE


def premium(score):
    """v8 G1: the quality premium, piecewise-linear in the quality score through PREMIUM_POINTS, flat outside."""
    pts = PREMIUM_POINTS
    if score <= pts[0][0]:
        return pts[0][1]
    if score >= pts[-1][0]:
        return pts[-1][1]
    for (a, pa), (b, pb) in zip(pts, pts[1:]):
        if a <= score <= b:
            return pa + (score - a) / (b - a) * (pb - pa)
    return pts[-1][1]


def near_cut(score):
    return score is not None and min(abs(score - c) for c in TIER_CUTS) <= NEAR_CUT + EPS


def tree_ev(tree):
    """Probability-weighted mean of the tree (divided by the probability sum, which the checks allow to be 1 +/- 0.005)."""
    sp = sum(b["p"] for b in tree)
    return sum(b["p"] * b["value"] for b in tree) / sp if sp > 0 else None


def implied_ratio(seats, H, key="buy"):
    """Expected upside / expected downside at price H on the committee's pooled floored trees: the mixture of the
    headline seats eligible for the rule `key`, each weighted by its Phase-0 weight (run units). None if undefined."""
    up = dn = 0.0
    for s in seats:
        if s["irr"] or s["no_buy"] or s.get(key) is None or not s.get("tree_f") or not (s.get("w") or 0) > 0:
            continue
        sp = sum(b["p"] for b in s["tree_f"])
        for b in s["tree_f"]:
            q = s["w"] * b["p"] / sp
            up += q * max(b["value"] - H, 0.0)
            dn += q * max(H - b["value"], 0.0)
    return (up / dn) if (H is not None and dn > 0) else None


def expectile(tree, tau):
    """The tau-expectile of a discrete tree: the P with tau*E[(V-P)+] = (1-tau)*E[(P-V)+] (bisection, exact to 1e-12)."""
    lo, hi = min(b["value"] for b in tree), max(b["value"] for b in tree)
    f = lambda P: tau * sum(b["p"] * max(b["value"] - P, 0.0) for b in tree) - \
        (1 - tau) * sum(b["p"] * max(P - b["value"], 0.0) for b in tree)
    if f(lo) <= 0:
        return lo
    if f(hi) >= 0:
        return hi
    for _ in range(200):
        mid = (lo + hi) / 2
        if f(mid) > 0:
            lo = mid
        else:
            hi = mid
        if hi - lo < 1e-12 * max(1.0, abs(hi)):
            break
    return (lo + hi) / 2

ADJ_CLASSES = [  # generic keyword classes for the adjustment ledger (descriptive only)
    ("SBC", r"\bsbc\b|stock[- ]based|share[- ]based|stock comp"),
    ("acquisitions/M&A", r"acqui|m&a|\bdeal"),
    ("interest", r"interest"),
    ("tax", r"\btax"),
    ("working capital / deferred revenue", r"working capital|deferred revenue|float|unearned"),
    ("lease", r"lease"),
    ("capex / capitalised costs", r"capex|capital expenditure|capitali[sz]ed"),
    ("legal / one-time", r"legal|settle|litigation|one[- ]time|non[- ]recurring|termination"),
]

CARD_TEMPLATE = """**DECISION CARD — ⟨TICKER⟩ (⟨UNIT⟩), as of ⟨AS_OF⟩**

1. **Fair value (the estimate):** ⟨CARD_FV⟩. Run range ⟨CARD_FV_LO⟩–⟨CARD_FV_HI⟩.
2. **Required margin (the policy):** effective ⟨CARD_M⟩ = base tier margin ⟨CARD_BASE⟩ + tail term p·L ⟨CARD_TAIL⟩ + weighting residual ⟨CARD_RESID⟩. Each term is the seat-weighted mean within runs, averaged with equal weight over the runs retained for ⟨CARD_BUY⟩; ⟨CARD_RESID⟩ is ⟨CARD_M⟩ minus the two terms.
3. **BUY: ⟨CARD_BUY⟩.** 80% confidence interval for this pipeline's expected BUY on these packs, with this model and this orchestration: ⟨CARD_LO⟩–⟨CARD_HI⟩. A fresh execution's figure is expected within ⟨CARD_REP_LO⟩–⟨CARD_REP_HI⟩. Neither range covers the levers in item 5.
4. **BUY at base tier margins alone, with no tail term** (policy alternatives, not the committee's figure): Exceptional ⟨CARD_B1⟩; High Quality ⟨CARD_B2⟩; Average ⟨CARD_B3⟩; Below Average ⟨CARD_B4⟩. Modal tier: ⟨CARD_TIER⟩ (⟨CARD_TIER_N⟩ of ⟨CARD_SEATS⟩ headline seats).
5. **Levers** (change in BUY, ⟨UNIT⟩ / run-noise SDs):
   - break probability −5pp ⟨CARD_L1⟩, +5pp ⟨CARD_L2⟩;
   - valuation date rolled to pack date ⟨CARD_L3⟩;
   - share-count date ⟨CARD_L4⟩;
   - both ⟨CARD_L5⟩;
   - risk-free +50bp ⟨CARD_L6⟩;
   - without the most influential finding ⟨CARD_L7⟩;
   - dossier contrast t = ⟨CARD_T⟩ (df ⟨CARD_DF⟩).
6. **Reproducibility:** run-noise SD ⟨CARD_SW⟩ (df ⟨CARD_DF⟩; 90% range ⟨CARD_SW_LO⟩–⟨CARD_SW_HI⟩). Within-dossier noise is ⟨CARD_FV_NOISE⟩ of the mean on fair value and ⟨CARD_BUY_NOISE⟩ on BUY. Two published BUYs from fresh executions of these packs that differ by less than ⟨CARD_SW⟩ are within run noise (about a 90% band); single runs differ by more than ⟨CARD_SW⟩ about half the time.
7. **Status:**
   - runs ⟨CARD_RUNS⟩;
   - valuation date(s) ⟨CARD_VDATE⟩; per-share count date(s) ⟨CARD_SDATE⟩;
   - MARKET_INPUTS ⟨CARD_MI⟩;
   - memory control: probe ⟨CARD_PROBE⟩, β̂ₖ ⟨CARD_BK⟩, β̂ⱼ ⟨CARD_BJ⟩, flag ⟨CARD_MFLAG⟩;
   - first v7 ticker only: v6-rule bridge ⟨CARD_BRIDGE_V6⟩; unmasked bridge runs ⟨CARD_BRIDGE_RUNS⟩;
   - orchestration replicate ⟨CARD_S7⟩;
   - mandate ⟨CARD_MANDATE⟩;
   - thin-data decisive inputs ⟨CARD_THIN⟩."""

CARD_TEMPLATE_V71 = CARD_TEMPLATE.replace(
    "   - both ⟨CARD_L5⟩;\n",
    "   - both ⟨CARD_L5⟩;\n   - denominator on the period-weighted count ⟨CARD_L8⟩;\n"
    "   - acquisitions: every seat organic ⟨CARD_L9⟩, every seat including acquisitions ⟨CARD_L10⟩;\n").replace(
    "   - mandate ⟨CARD_MANDATE⟩;\n",
    "   - mandate ⟨CARD_MANDATE⟩;\n   - seats at the 0.60 cap ⟨CARD_CAP⟩; acquisition-matching mismatches ⟨CARD_ACQ⟩ "
    "(undeclared ⟨CARD_ACQ_U⟩); denominator counts normalised ⟨CARD_DENOM⟩;\n")

CARD_TEMPLATE_V8 = CARD_TEMPLATE_V71.replace(
    "= base tier margin ⟨CARD_BASE⟩ + tail term", "= quality premium ⟨CARD_BASE⟩ + tail term").replace(
    "Neither range covers the levers in item 5.", "Neither range covers the levers in item 6 or the margin rules in item 5.").replace(
    "4. **BUY at base tier margins alone, with no tail term** (policy alternatives, not the committee's figure): "
    "Exceptional ⟨CARD_B1⟩; High Quality ⟨CARD_B2⟩; Average ⟨CARD_B3⟩; Below Average ⟨CARD_B4⟩.",
    "4. **BUY at one quality premium for every seat, with no tail term** (policy alternatives, not the committee's figure): "
    "12.5% ⟨CARD_B1⟩; 22.5% ⟨CARD_B2⟩; 32.5% ⟨CARD_B3⟩; 40% ⟨CARD_B4⟩.").replace(
    "5. **Levers**",
    "5. **Other margin rules on the same seats and trees** (policy alternatives, not estimates and not a confidence range; "
    "never averaged; constants fixed in the spec at the v7.1 step rule's average strictness on two earlier tickers): "
    "step tiers ⟨CARD_R1⟩; EV rule, tuned Victor (0.67 × tree expected value) ⟨CARD_R2⟩; expectile rule, tuned Max "
    "(expected upside 7.75 × expected downside) ⟨CARD_R3⟩. Expected upside ÷ expected downside at each BUY, on the "
    "committee's pooled trees: published ⟨CARD_K0⟩; step tiers ⟨CARD_K1⟩; EV rule ⟨CARD_K2⟩; expectile rule ⟨CARD_K3⟩. "
    "Seats left out of the tree rules: ⟨CARD_NOTREE⟩. Seats within 3 points of a tier cut-off: ⟨CARD_NEAR⟩ of ⟨CARD_SEATS⟩.\n"
    "6. **Levers**").replace("6. **Reproducibility:**", "7. **Reproducibility:**").replace("7. **Status:**", "8. **Status:**")

HEADLINE_TEMPLATE = ("Published BUY ⟨CARD_BUY⟩ ⟨UNIT⟩ (80% confidence interval for this pipeline's expected BUY "
                     "on these packs: ⟨CARD_LO⟩–⟨CARD_HI⟩); committee fair value ⟨CARD_FV⟩; largest "
                     "sensitivity not in the interval: ⟨CARD_BIGROW⟩, ⟨CARD_BIGSIZE⟩ ⟨UNIT⟩."
                     "⟨IF CARD_MANDATE ≠ NONE:⟩ The figure is conditional on the user mandate."
                     "⟨IF CARD_MFLAG ≠ NONE:⟩ ⟨CARD_MFLAG⟩.")

# v9 (N1, N2): no memory or bridge line; a lever for the alternative-denominator row; no memory flag in the sentence
CARD_TEMPLATE_V9 = CARD_TEMPLATE_V8.replace(
    "   - acquisitions: every seat organic ⟨CARD_L9⟩, every seat including acquisitions ⟨CARD_L10⟩;\n",
    "   - acquisitions: every seat organic ⟨CARD_L9⟩, every seat including acquisitions ⟨CARD_L10⟩;\n"
    "   - every seat on its run's alternative denominator ⟨CARD_L11⟩ (runs with the alternative above the declared "
    "denominator ⟨CARD_ALT_UP⟩, below ⟨CARD_ALT_DN⟩, none ⟨CARD_ALT_NONE⟩; seats valued ⟨CARD_ALT_K⟩ of ⟨CARD_SEATS⟩; "
    "each seat's margin held);\n").replace(
    "   - memory control: probe ⟨CARD_PROBE⟩, β̂ₖ ⟨CARD_BK⟩, β̂ⱼ ⟨CARD_BJ⟩, flag ⟨CARD_MFLAG⟩;\n", "").replace(
    "   - first v7 ticker only: v6-rule bridge ⟨CARD_BRIDGE_V6⟩; unmasked bridge runs ⟨CARD_BRIDGE_RUNS⟩;\n", "")
HEADLINE_TEMPLATE_V9 = HEADLINE_TEMPLATE.replace("⟨IF CARD_MFLAG ≠ NONE:⟩ ⟨CARD_MFLAG⟩.", "")
assert "⟨CARD_L11⟩" in CARD_TEMPLATE_V9 and "CARD_MFLAG" not in CARD_TEMPLATE_V9 and "CARD_BRIDGE" not in CARD_TEMPLATE_V9

# v10 (T1, T2, T4): a debt lever; a status line for the rate, flow-basis, risk-class and Walter counts
CARD_TEMPLATE_V10 = CARD_TEMPLATE_V9.replace(
    "each seat's margin held);\n",
    "each seat's margin held);\n   - debt: net claims deducted again, the v9 count (each seat's margin held) ⟨CARD_L12⟩;\n").replace(
    "denominator counts normalised ⟨CARD_DENOM⟩;\n",
    "denominator counts normalised ⟨CARD_DENOM⟩;\n   - seats off the macro base ⟨CARD_OFFBASE⟩ (fair value still off it "
    "after the fold ⟨CARD_OFFBASE_FOLD⟩); runs with debt deducted ⟨CARD_DEBTDED⟩; systematic risk class (descriptive): "
    "defensive ⟨CARD_SRC_D⟩, average ⟨CARD_SRC_A⟩, cyclical "
    "⟨CARD_SRC_C⟩ runs; Walter's mean multiplier ⟨CARD_WMULT⟩;\n")
HEADLINE_TEMPLATE_V10 = HEADLINE_TEMPLATE_V9
assert "⟨CARD_L12⟩" in CARD_TEMPLATE_V10 and "⟨CARD_WMULT⟩" in CARD_TEMPLATE_V10


# ----------------------------------------------------------------------------- helpers
def num(x):
    if x is None or isinstance(x, bool):
        return None
    if isinstance(x, (int, float)):
        return float(x) if math.isfinite(float(x)) else None
    if isinstance(x, str):
        m = re.search(r"[-−]?\d[\d,]*\.?\d*(?:[eE][-+]?\d+)?", x)
        if not m:
            return None
        s = m.group(0).replace(",", "").replace("−", "-")
        try:
            return float(s)
        except ValueError:
            return None
    return None


def canon(name):
    if name is None:
        return ""
    s = str(name).strip().lower()
    for c in COMMITTEE:
        if re.search(r"\b" + c + r"\b", s):
            return c
    return s


def tier_of(score):
    if score is None:
        return None
    if score >= 90 - EPS:
        return "Exceptional"
    if score >= 75 - EPS:
        return "High Quality"
    if score >= 60 - EPS:
        return "Average"
    return "Below Average"


def norm_tier(t):
    if t is None:
        return None
    s = str(t).strip().lower()
    if s.startswith("exc"):
        return "Exceptional"
    if s.startswith("high"):
        return "High Quality"
    if s.startswith("aver"):
        return "Average"
    if s.startswith("below"):
        return "Below Average"
    return None


def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def parse_date(s):
    if not s:
        return None
    try:
        return datetime.date.fromisoformat(str(s)[:10])
    except ValueError:
        return None


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def sd(xs):
    xs = [x for x in xs if x is not None]
    return statistics.stdev(xs) if len(xs) > 1 else None


def fmt(x, d=2):
    if x is None:
        return "n/a"
    if isinstance(x, str):
        return x
    return f"{x:,.{d}f}"


def sfmt(x, d=2):
    if x is None:
        return "n/a"
    return ("+" if x >= 0 else "−") + f"{abs(x):,.{d}f}"


def extract_json_objects(text):
    dec = json.JSONDecoder()
    out = []
    i = 0
    while True:
        i = text.find("{", i)
        if i < 0:
            break
        try:
            obj, end = dec.raw_decode(text, i)
            out.append(obj)
            i = end
        except ValueError:
            i += 1
    return out


def load_summary(path):
    text = open(path, encoding="utf-8").read()
    if path.endswith(".json"):
        return json.loads(text)
    idx = text.rfind("## MACHINE SUMMARY")
    seg = text[idx:] if idx >= 0 else text
    for obj in extract_json_objects(seg):
        if isinstance(obj, dict) and "investors" in obj:
            return obj
    for obj in reversed(extract_json_objects(text)):
        if isinstance(obj, dict) and "investors" in obj:
            return obj
    raise ValueError("no MACHINE SUMMARY JSON with 'investors' found in " + path)


def load_verification(path):
    text = open(path, encoding="utf-8").read()
    if path.endswith(".json"):
        return json.loads(text)
    cands = [o for o in extract_json_objects(text) if isinstance(o, dict) and "rulings" in o]
    if not cands:
        raise ValueError("no verification JSON with 'rulings' found in " + path)
    return cands[-1]


# ----------------------------------------------------------------------------- tree checks
def check_tree(tree, fv):
    """The five Stage-3 checks on the tree as reported (before Helena's floor)."""
    reasons = []
    if not isinstance(tree, list) or not tree:
        return False, ["no tree"]
    names, ps, vs = [], [], []
    for b in tree:
        if not isinstance(b, dict):
            return False, ["branch is not an object"]
        names.append(str(b.get("branch", "")).strip())
        ps.append(num(b.get("p")))
        vs.append(num(b.get("value")))
    if any(p is None for p in ps) or any(v is None for v in vs):
        return False, ["non-numeric p or value"]
    low = [n.lower() for n in names]
    if len(set(low)) != len(low):
        reasons.append("branch names not unique")
    if low.count("base") != 1:
        reasons.append("not exactly one base branch")
    if low.count("break") != 1:
        reasons.append("not exactly one break branch")
    if any(p < -EPS or p > 1 + EPS for p in ps):
        reasons.append("probability outside [0,1]")
    if abs(sum(ps) - 1.0) > 0.005 + EPS:
        reasons.append(f"probabilities sum to {sum(ps):.6f}")
    if reasons:
        return False, reasons
    ib, ik = low.index("base"), low.index("break")
    vb, vk = vs[ib], vs[ik]
    if fv is None:
        return False, ["no fair_value"]
    if abs(vb - fv) > max(0.001 * abs(fv), 0.01) + EPS:
        reasons.append(f"base value {vb} != fair_value {fv}")
    pge = sum(p for p, v in zip(ps, vs) if v >= vb - EPS)
    ple = sum(p for p, v in zip(ps, vs) if v <= vb + EPS)
    if pge < 0.5 - EPS or ple < 0.5 - EPS:
        reasons.append(f"base not the median (P(V>=base)={pge:.4f}, P(V<=base)={ple:.4f})")
    others = [v for i, v in enumerate(vs) if i != ik]
    if others and vk > min(others) + EPS:
        reasons.append("break branch is not the lowest-valued branch")
    return (not reasons), reasons


# ----------------------------------------------------------------------------- seat recompute
def seat_margin(base, p, L, framework_nobuy=False, fv=None):
    raw = base + p * L
    if v71():   # F5: above the bound the seat is AT CAP (required 0.60) and stays in; NO BUY = FRAMEWORK rule only
        no_buy = framework_nobuy or fv is None or fv <= 0
    else:
        no_buy = (raw > NOBUY_BOUND + EPS) or framework_nobuy or fv is None or fv <= 0
    req = clamp(raw, CLAMP_LO, CLAMP_HI)
    buy = None if no_buy else fv * (1 - req)
    return raw, req, no_buy, buy


def fv_macro_base(inv, fv, macro_base, lg, label, name):
    """F5: the seat's fair value at the macro base. Reported field, else a logged log-linear estimate."""
    f = num(inv.get("fair_value_macro_base"))
    if f is not None and f > 0:
        return f, False
    rate, f50 = num(inv.get("discount_rate")), num(inv.get("fair_value_rf_plus_50bp"))
    if fv is None or fv <= 0:
        return fv, True
    if rate is None or macro_base is None:
        lg.append(f"{label}{name}: C7 no fair_value_macro_base and no rate/macro base to estimate it; fair_value used")
        return fv, True
    if abs(rate - macro_base) < 1e-9:
        lg.append(f"{label}{name}: C7 no fair_value_macro_base; rate equals the macro base, fair_value used")
        return fv, True
    if f50 is None or f50 <= 0 or f50 >= fv:
        lg.append(f"{label}{name}: C7 no fair_value_macro_base; no usable fair_value_rf_plus_50bp to estimate it; fair_value used")
        return fv, True
    est = fv * (fv / f50) ** ((rate - macro_base) / 0.5)
    lg.append(f"{label}{name}: C7 no fair_value_macro_base; estimated {est:.4f} from fair_value, fair_value_rf_plus_50bp "
              f"and rate {rate} vs macro base {macro_base} (log-linear)")
    return est, True


def recompute_seat(inv, floor, log=None, label="", macro_base=None):
    lg = log if log is not None else []
    name = canon(inv.get("investor"))
    fv = num(inv.get("fair_value"))
    score = num(inv.get("quality_score"))
    rep_tier = norm_tier(inv.get("quality_tier"))
    tier = tier_of(score) if score is not None else rep_tier
    if score is None:
        lg.append(f"{label}{name}: C7 no numeric quality_score; tier taken from quality_tier ({rep_tier})")
    elif rep_tier is not None and rep_tier != tier:
        lg.append(f"{label}{name}: C7 quality_tier '{inv.get('quality_tier')}' does not match score {score} ({tier}); script uses {tier}")
    if tier is None:
        tier = "Below Average"
        lg.append(f"{label}{name}: C7 no tier derivable; Below Average used")
    base_step = TIER_BASE[tier]
    if v8():   # G1: the quality premium is continuous in the score; the tier is a label
        sc = score if score is not None else TIER_MID_SCORE[tier]
        if score is None:
            lg.append(f"{label}{name}: C7 no numeric quality_score; quality premium taken at the {tier} midpoint score {sc}")
        base = premium(sc)
    else:
        base = base_step
    irr_flag = bool(inv.get("irr_entry"))
    irr = irr_flag or name in IRR_NAMES or (v10() and name in V10_UNSEATED)
    if score is not None and v8() and (score < 0 - EPS or score > 100 + EPS):
        lg.append(f"{label}{name}: C7 quality_score {score} outside 0-100; the quality premium is flat beyond its end points")
    if irr and v10():
        lg.append(f"{label}{name}: C5 not a seated investor under v10 (seven seats; Simon is merged into Walter; "
                  f"Victor and Max are not seated); kept out of every statistic")
    elif irr and v8():
        lg.append(f"{label}{name}: C5 not a seated investor under v8 (Victor and Max are not seated; no entry prices); "
                  f"kept out of every statistic")
    elif irr and not irr_flag:
        lg.append(f"{label}{name}: irr_entry not true but seat is an IRR seat by Appendix B; segregated")
    tree = inv.get("tree")
    ok, reasons = check_tree(tree, fv)
    fl = num(floor)
    tree_f = None
    if ok:
        tree_f = []
        for b in tree:
            v = num(b["value"])
            tree_f.append({"branch": str(b["branch"]).strip(), "p": num(b["p"]),
                           "value": max(v, fl) if fl is not None else v, "value_reported": v})
        brk = [b for b in tree_f if b["branch"].lower() == "break"][0]
        p = brk["p"]
        L_own = 1 - brk["value"] / fv
        if v71():
            fmb, _est = fv_macro_base(inv, fv, macro_base, lg, label, name)
            L = max(0.0, 1 - brk["value"] / fmb) if fmb else L_own
        else:
            fmb, L = fv, L_own
        if len(tree) < 4:
            lg.append(f"{label}{name}: C7 tree has {len(tree)} branches (<4)")
    else:
        p = num(inv.get("break_p"))
        L = num(inv.get("break_loss"))
        L_own, fmb = L, fv
        lg.append(f"{label}{name}: C7 tree invalid ({'; '.join(reasons)}); recomputed from reported break_p/break_loss")
        if v71() and L is not None and fv and inv.get("fair_value_macro_base") is None:
            fmb, _est = fv_macro_base(inv, fv, macro_base, lg, label, name)
            if fmb and fmb > 0:   # replay only: a v7 summary reports L on its own FV; restate it on the macro-base FV
                L = max(0.0, 1 - (1 - L) * fv / fmb)
        if v71() and L is not None:
            L = max(0.0, L)
    rep_base = num(inv.get("quality_premium"))
    if rep_base is None:
        rep_base = num(inv.get("base_tier_margin"))
    rep_tail = num(inv.get("tail_term"))
    rep_nobuy = bool(inv.get("no_buy"))
    rep_raw = (rep_base + rep_tail) if (rep_base is not None and rep_tail is not None) else None
    framework_nobuy = rep_nobuy and not (rep_raw is not None and rep_raw > NOBUY_BOUND + EPS)
    if v71() and rep_nobuy:
        reason = inv.get("no_buy_reason_or_null") or inv.get("_no_buy_patched")
        raw_now = (base + p * L) if (p is not None and L is not None) else None
        if reason:
            framework_nobuy = True
        elif raw_now is not None and raw_now > NOBUY_BOUND + EPS:
            framework_nobuy = False
            lg.append(f"{label}{name}: C7 no_buy reported with no FRAMEWORK reason on a seat above 0.60; treated as AT CAP")
        else:
            framework_nobuy = True
            lg.append(f"{label}{name}: C7 no_buy reported with no no_buy_reason_or_null; honoured as a FRAMEWORK NO BUY")
    if v10() and V10_NOBUY_RULE and rep_nobuy and not inv.get("_no_buy_patched"):
        # T4: the only FRAMEWORK uninvestability rule is two or more FAILs among Walter's gates
        if not (name == "walter" and walter_fails(inv.get("management_grade")) >= 2):
            framework_nobuy, rep_nobuy = False, False
            lg.append(f"{label}{name}: C7 no_buy reported, but under v10 only Walter with two or more FAIL gates is NO BUY; "
                      f"the seat is kept")
    if p is None or L is None:
        lg.append(f"{label}{name}: no break_p/break_loss computable; seat excluded (uncomputable)")
        seat = dict(name=name, investor=inv.get("investor"), fv=fv, score=score, tier=tier, base=base, irr=irr,
                    base_step=base_step, buy_step=None, buy_victor=None, buy_max=None, buy_evp=None,
                    near_cut=near_cut(score), forecast=inv.get("forecast_5y"), forecast_def=inv.get("forecast_definition"),
                    horizon=None,
                    p=None, L=None, L_own=None, at_cap=False, tail=None, raw=None, required=None, no_buy=True, buy=None,
                    uncomputable=True, fv_mb=None, fv_oth=num(inv.get("fair_value_other_acquisition_basis")), fv_alt=num(inv.get("fair_value_alternative_denominator")),
                    growth_basis=inv.get("growth_basis"), acq_deducted=inv.get("acq_spend_deducted"),
                    tree_ok=ok, tree_f=tree_f, framework_nobuy=framework_nobuy,
                    rate=num(inv.get("discount_rate")), fv50=num(inv.get("fair_value_rf_plus_50bp")),
                    entry=num(inv.get("buy")) if irr else None)
        return seat
    if framework_nobuy and not v71() and not (base + p * L > NOBUY_BOUND + EPS):
        lg.append(f"{label}{name}: reported NO BUY retained (not produced by the 0.60 bound; framework rule)")
    raw, req, no_buy, buy = seat_margin(base, p, L, framework_nobuy, fv)
    at_cap = v71() and (raw > NOBUY_BOUND + EPS) and not no_buy
    fw_step = framework_nobuy   # the step line repeats the v7.1 F5 decision with the step base (exactly the v7.1 rule)
    if v71() and rep_nobuy and not (inv.get("no_buy_reason_or_null") or inv.get("_no_buy_patched")):
        fw_step = not (base_step + p * L > NOBUY_BOUND + EPS)
    _r, _q, nb_step, buy_step = seat_margin(base_step, p, L, fw_step, fv)
    seat = dict(name=name, investor=inv.get("investor"), fv=fv, score=score, tier=tier, base=base, irr=irr,
                base_step=base_step, buy_step=None if nb_step else buy_step, near_cut=near_cut(score),
                buy_victor=(TUNED_C * tree_ev(tree_f)) if (tree_f and not no_buy) else None,
                buy_max=expectile(tree_f, 1.0 / (1.0 + TUNED_K)) if (tree_f and not no_buy) else None,
                buy_evp=(tree_ev(tree_f) * (1 - base)) if (tree_f and not no_buy) else None,
                forecast=inv.get("forecast_5y"), forecast_def=inv.get("forecast_definition"),
                horizon=num((inv.get("break_derivation") or {}).get("horizon_years"))
                if isinstance(inv.get("break_derivation"), dict) else None,
                p=p, L=L, L_own=L_own, at_cap=at_cap, fv_mb=fmb, tail=p * L, raw=raw, required=req, no_buy=no_buy,
                buy=buy, uncomputable=False, fv_oth=num(inv.get("fair_value_other_acquisition_basis")), fv_alt=num(inv.get("fair_value_alternative_denominator")),
                growth_basis=inv.get("growth_basis"), acq_deducted=inv.get("acq_spend_deducted"),
                tree_ok=ok, tree_f=tree_f, framework_nobuy=framework_nobuy,
                rate=num(inv.get("discount_rate")), fv50=num(inv.get("fair_value_rf_plus_50bp")))
    if irr:
        seat["entry"] = num(inv.get("buy"))
        seat["ref_buy"] = buy
    # mismatch log against reported fields
    for fld, val in (("break_p", p), ("break_loss", L), ("tail_term", p * L), ("required_margin", req)):
        r = num(inv.get(fld))
        if r is not None and abs(r - val) > 0.0005:
            lg.append(f"{label}{name}: reported {fld} {r} corrected to {val:.6f}")
    if v8() and not irr:
        rq = num(inv.get("quality_premium"))
        if rq is None:
            lg.append(f"{label}{name}: C7 no quality_premium reported; script value {base:.4f}")
        elif abs(rq - base) > 0.00005 + EPS:
            lg.append(f"{label}{name}: reported quality_premium {rq} corrected to {base:.6f} (C7)")
        if seat.get("horizon") is None:
            lg.append(f"{label}{name}: C7 break_derivation.horizon_years missing")
        fc = inv.get("forecast_5y")
        good = [x for x in fc if isinstance(x, dict) and num(x.get("cash_flow_total")) is not None
                and num(x.get("cash_flow_per_share")) is not None and x.get("period_end")] if isinstance(fc, list) else []
        if len(good) < 5:
            lg.append(f"{label}{name}: C8 forecast_5y has {len(good)} complete period(s) of 5")
    rb = num(inv.get("buy"))
    if not irr:
        if buy is not None and (rb is None or abs(rb - buy) > max(0.01, 1e-4 * abs(buy))):
            lg.append(f"{label}{name}: reported buy {rb} corrected to {buy:.4f}")
        if buy is None and rb is not None and not rep_nobuy:
            lg.append(f"{label}{name}: reported buy {rb} but script finds NO BUY")
    if bool(inv.get("no_buy")) != no_buy:
        lg.append(f"{label}{name}: reported no_buy {inv.get('no_buy')} corrected to {no_buy}")
    if v71() and inv.get("at_cap") is not None and bool(inv.get("at_cap")) != at_cap:
        lg.append(f"{label}{name}: reported at_cap {inv.get('at_cap')} corrected to {at_cap}")
    return seat


def weights_of(summary):
    w = {}
    for k, v in ((summary.get("frame") or {}).get("weights") or {}).items():
        w[canon(k)] = num(v)
    return w


def denominator_count(frame):
    """F1: the count that divides the cash flow. v7.1 field denominator_count_m; v7 summaries: share_count_m."""
    d = num(frame.get("denominator_count_m"))
    return d if d is not None else num(frame.get("share_count_m"))


def period_weighted_count(frame):
    d = num(frame.get("period_weighted_count_m"))
    return d if d is not None else num(frame.get("share_count_m"))


PS_SEAT_FIELDS = ("fair_value", "fair_value_rf_plus_50bp", "fair_value_macro_base", "fair_value_other_acquisition_basis",
                  "fair_value_alternative_denominator")


def normalise_denominator(summary, lg, label=""):
    """F1: returns (summary_copy, ratio). Rescales every per-share value of every seat on its operating part."""
    fr = summary.get("frame") or {}
    den, ps = denominator_count(fr), num(fr.get("per_share_count_m"))
    if not den or not ps:
        lg.append(f"{label}C8 denominator_count_m or per_share_count_m missing; no normalisation possible")
        return summary, 1.0
    if abs(den / ps - 1) <= DENOM_TOL:
        return summary, 1.0
    ratio = den / ps
    bsa = num(fr.get("balance_sheet_add_per_share")) or 0.0
    S = copy.deepcopy(summary)

    def sc(v):
        x = num(v)
        return None if x is None else (x - bsa) * ratio + bsa
    for inv in S.get("investors", []):
        for f in PS_SEAT_FIELDS:
            if inv.get(f) is not None:
                inv[f] = sc(inv[f])
        for b in inv.get("tree") or []:
            if isinstance(b, dict) and b.get("value") is not None:
                b["value"] = sc(b["value"])
        nm = canon(inv.get("investor"))
        if (bool(inv.get("irr_entry")) or nm in IRR_NAMES) and inv.get("buy") is not None:
            inv["buy"] = sc(inv["buy"])
        if v8() and isinstance(inv.get("forecast_5y"), list):   # a per-share flow: x ratio, no balance-sheet add
            for x in inv["forecast_5y"]:
                if isinstance(x, dict) and num(x.get("cash_flow_per_share")) is not None:
                    x["cash_flow_per_share"] = num(x["cash_flow_per_share"]) * ratio
    frs = S.setdefault("frame", {})
    for f in ("gross_denominator_per_share", "declared_denominator_per_share", "alternative_denominator_per_share",
              "acq_spend_normalised_per_share"):
        if num(frs.get(f)) is not None:
            frs[f] = num(frs[f]) * ratio
    for a in frs.get("denominator_adjustments") or []:
        if isinstance(a, dict) and num(a.get("per_share")) is not None:
            a["per_share"] = num(a["per_share"]) * ratio
    lg.append(f"{label}C1 denominator count {den} != per-share count {ps}: every per-share value rescaled on its "
              f"operating part by {ratio:.6f} (F1)")
    return S, ratio


def recompute_run(summary, log=None, label=""):
    lg = log if log is not None else []
    if v71():
        summary, _ratio = normalise_denominator(summary, lg, label)
    fr0 = summary.get("frame") or {}
    mb = num(fr0.get("macro_base"))
    if mb is None and num(fr0.get("risk_free")) is not None and num(fr0.get("erp")) is not None:
        mb = num(fr0.get("risk_free")) + num(fr0.get("erp"))
    floor = num((summary.get("helena_floor") or {}).get("floor_per_share_or_null"))
    seats = [recompute_seat(inv, floor, lg, label, macro_base=mb) for inv in summary.get("investors", [])]
    if v10():   # descriptive fields for the T1 check and the T6 channel monitor (they move no number)
        for inv, s_ in zip(summary.get("investors", []), seats):
            s_["fv_mb_rep"] = num(inv.get("fair_value_macro_base"))
            s_["tg"] = num(inv.get("terminal_growth"))
            s_["fg"] = forecast_growth(inv.get("forecast_5y"))
            g = inv.get("management_grade")
            s_["wmult"] = walter_multiplier(g) if s_["name"] == "walter" else None
    w = weights_of(summary)
    for s in seats:
        s["w"] = w.get(s["name"])
        if s["w"] is None and not s["irr"]:
            lg.append(f"{label}{s['name']}: no Phase-0 weight; seat carries weight 0")
            s["w"] = 0.0
    return seats


def headline_of(seats, uniform=False, buy_key="buy"):
    num_, den = 0.0, 0.0
    for s in seats:
        if s["irr"] or s["no_buy"] or s.get(buy_key) is None:
            continue
        w = 1.0 if uniform else (s["w"] or 0.0)
        if w <= 0:
            continue
        num_ += w * s[buy_key]
        den += w
    return num_ / den if den > 0 else None


def wfv_of(seats, uniform=False):
    num_, den = 0.0, 0.0
    for s in seats:
        if s["irr"] or s["no_buy"] or s.get("buy") is None:
            continue
        w = 1.0 if uniform else (s["w"] or 0.0)
        if w <= 0:
            continue
        num_ += w * s["fv"]
        den += w
    return num_ / den if den > 0 else None


def wmean_field(seats, key):
    num_, den = 0.0, 0.0
    for s in seats:
        if s["irr"] or s["no_buy"] or s.get("buy") is None or s.get(key) is None:
            continue
        w = s["w"] or 0.0
        if w <= 0:
            continue
        num_ += w * s[key]
        den += w
    return num_ / den if den > 0 else None


def headline_seats(seats):
    return [s for s in seats if not s["irr"] and not s["no_buy"] and s.get("buy") is not None and (s["w"] or 0) > 0]


# ----------------------------------------------------------------------------- counterfactuals (run units)
def cf_breakp(seats, delta):
    out, at_min = [], 0
    for s in seats:
        t = dict(s)
        if not s["irr"] and not s.get("uncomputable") and s["p"] is not None:
            p = s["p"]
            if delta < 0:
                if p <= RULE4_MIN + EPS:
                    at_min += 1
                    p2 = p
                else:
                    p2 = max(RULE4_MIN, p + delta)
            else:
                p2 = min(1.0, p + delta)
            raw, req, nb, buy = seat_margin(s["base"], p2, s["L"], s["framework_nobuy"], s["fv"])
            t.update(p=p2, tail=p2 * s["L"], raw=raw, required=req, no_buy=nb, buy=buy,
                     at_cap=v71() and raw > NOBUY_BOUND + EPS and not nb)
        out.append(t)
    return out, at_min


def cf_convention(seats, frame, which, log=None, label=""):
    lg = log if log is not None else []
    vd, pd = parse_date(frame.get("valuation_date")), parse_date(frame.get("pack_as_of_date"))
    dt = 0.0
    if vd and pd:
        dt = (pd - vd).days / 365.25
    elif which in (1, 3):
        lg.append(f"{label}convention: valuation_date or pack_as_of_date missing; dt = 0")
    bsa = num(frame.get("balance_sheet_add_per_share")) or 0.0
    a, b = num(frame.get("per_share_count_m")), num(frame.get("latest_share_count_m"))
    ratio = (a / b) if (a and b) else 1.0
    if which in (2, 3) and not (a and b):
        lg.append(f"{label}convention: per_share_count_m or latest_share_count_m missing; ratio = 1")
    out = []
    for s in seats:
        t = dict(s)
        if not s["irr"] and not s["no_buy"] and s.get("buy") is not None:
            fv = s["fv"]
            if which in (1, 3) and dt != 0.0:
                r = s["rate"]
                if r is None:
                    lg.append(f"{label}{s['name']}: no numeric discount_rate; valuation date not rolled")
                else:
                    fv = (fv - bsa) * (1 + r / 100.0) ** dt + bsa
            if which in (2, 3):
                fv = fv * ratio
            t["fv"] = fv
            t["buy"] = fv * (1 - s["required"])
        out.append(t)
    return out, dt, ratio


def cf_denominator(seats, frame, log=None, label=""):
    """F1 convention row 4: cash flow divided by the period-weighted count instead of the per-share count."""
    lg = log if log is not None else []
    ps, pw = num(frame.get("per_share_count_m")), period_weighted_count(frame)
    if not ps or not pw:
        lg.append(f"{label}denominator row: no period-weighted count; figure kept")
        return [dict(s) for s in seats], 1.0
    ratio = ps / pw
    bsa = num(frame.get("balance_sheet_add_per_share")) or 0.0
    out = []
    for s in seats:
        t = dict(s)
        if not s["irr"] and not s["no_buy"] and s.get("buy") is not None:
            fv = (s["fv"] - bsa) * ratio + bsa
            t["fv"], t["buy"] = fv, fv * (1 - s["required"])
        out.append(t)
    return out, ratio


def zero_acq_spend(frame):
    """v9 N5: the pack shows no acquisition cash (acq_cash_by_year empty or summing to 0) and the run's normalised
    acquisition spend is 0, so the deduction is 0 on either basis. A run that excluded a deal from non-zero
    acquisition cash does not qualify (review: an F4 mismatch must not be hidden)."""
    fr = frame or {}
    v = num(fr.get("acq_spend_normalised_per_share"))
    cash = fr.get("acq_cash_by_year")
    if not (v9() and v is not None and abs(v) < 1e-12 and isinstance(cash, list)):
        return False
    tot = 0.0
    for c in cash:
        a = num(c.get("amount")) if isinstance(c, dict) else num(c)
        if a is None:
            return False
        tot += abs(a)
    return tot < 1e-12


def cf_acquisitions(seats, target, log=None, label="", frame=None):
    """F4 rows: every headline seat on `target` basis ('organic' or 'including_acquisitions'), margin held.
    v9 N5: with zero normalised acquisition spend both bases are the same valuation, so the row is the headline."""
    lg = log if log is not None else []
    if zero_acq_spend(frame):
        lg.append(f"{label}acquisition row ({target}): normalised acquisition spend is 0; every seat kept (N5)")
        return [dict(s) for s in seats], 0
    out, missing = [], 0
    for s in seats:
        t = dict(s)
        if not s["irr"] and not s["no_buy"] and s.get("buy") is not None:
            gb = str(s.get("growth_basis") or "").strip().lower()
            dd = s.get("acq_deducted")
            mismatched = (gb == "organic" and dd is True) or (gb == "including_acquisitions" and dd is False)
            if mismatched:
                if s.get("fv_oth") is not None:
                    t["fv"] = s["fv_oth"]
                    t["buy"] = s["fv_oth"] * (1 - s["required"])
                    lg.append(f"{label}{s['name']}: mismatched seat; acquisition row uses its matched value "
                              f"(fair_value_other_acquisition_basis)")
                else:
                    missing += 1
            elif gb and gb != target:
                if s.get("fv_oth") is not None:
                    t["fv"] = s["fv_oth"]
                    t["buy"] = s["fv_oth"] * (1 - s["required"])
                else:
                    missing += 1
            elif not gb:
                missing += 1
        out.append(t)
    if missing:
        lg.append(f"{label}acquisition row ({target}): {missing} headline seat(s) without growth_basis or "
                  f"fair_value_other_acquisition_basis kept at their fair value")
    return out, missing


def acq_mismatches(seats, frame=None):
    """F4: (n_organic_with_deduction, n_including_without_deduction, n_undeclared) over non-IRR seats.
    v9 N5: with zero normalised acquisition spend, declared pairs are never mismatches."""
    a = b = u = 0
    zero = zero_acq_spend(frame)
    for s in seats:
        if s["irr"]:
            continue
        gb = str(s.get("growth_basis") or "").strip().lower()
        dd = s.get("acq_deducted")
        if gb not in ("organic", "including_acquisitions") or not isinstance(dd, bool):
            u += 1
        elif zero:
            continue
        elif gb == "organic" and dd:
            a += 1
        elif gb == "including_acquisitions" and not dd:
            b += 1
    return a, b, u


def cf_rate(seats, log=None, label=""):
    lg = log if log is not None else []
    out = []
    for s in seats:
        t = dict(s)
        if not s["irr"] and not s["no_buy"] and s.get("buy") is not None:
            f50 = s["fv50"]
            if f50 is None:
                lg.append(f"{label}{s['name']}: no fair_value_rf_plus_50bp; rate lever uses fair_value")
                f50 = s["fv"]
            t["fv"] = f50
            t["buy"] = f50 * (1 - s["required"])
        out.append(t)
    return out


def cf_altdenom(seats, log=None, label=""):
    """v9 N2: every headline seat on fair_value_alternative_denominator, required margin held fixed.
    A seat without the field keeps its fair value; the count is returned and logged (C8)."""
    lg = log if log is not None else []
    out, missing = [], 0
    for s in seats:
        t = dict(s)
        if not s["irr"] and not s["no_buy"] and s.get("buy") is not None:
            if s.get("fv_alt") is not None and s["fv_alt"] <= 0:
                t["fv"], t["buy"], t["no_buy"] = s["fv_alt"], None, True
                lg.append(f"{label}{s['name']}: fair_value_alternative_denominator {s['fv_alt']:.4f} <= 0; NO BUY in the "
                          f"alternative-denominator row, weight dropped (C8)")
            elif s.get("fv_alt") is not None:
                t["fv"] = s["fv_alt"]
                t["buy"] = s["fv_alt"] * (1 - s["required"])
            else:
                missing += 1
        out.append(t)
    if missing:
        lg.append(f"{label}alternative-denominator row: {missing} headline seat(s) without "
                  f"fair_value_alternative_denominator kept at their fair value (C8)")
    return out, missing


ALT_BASES = ("period", "margin", "none")


def alt_denom_checks(seats, frame, log=None, label=""):
    """v9 N2 checks (logged, never corrected): basis enum; "none" equalities; ratio range; per-seat scaling.
    Returns dict(direction=up|down|none, ratio, valued, n)."""
    lg = log if log is not None else []
    fr = frame or {}
    basis = str(fr.get("alternative_denominator_basis") or "").strip().lower()
    dec, alt = num(fr.get("declared_denominator_per_share")), num(fr.get("alternative_denominator_per_share"))
    bsa = num(fr.get("balance_sheet_add_per_share")) or 0.0
    hs = headline_seats(seats)
    valued = sum(1 for s in hs if s.get("fv_alt") is not None)
    if basis not in ALT_BASES:
        lg.append(f"{label}C8 alternative_denominator_basis {str(fr.get('alternative_denominator_basis'))[:40]!r} is not "
                  f"period, margin or none")
    ratio = (alt / dec) if (alt is not None and dec not in (None, 0)) else None
    if basis == "none":
        if ratio is None or abs(ratio - 1) > 1e-3:
            lg.append(f"{label}C1 alternative_denominator_basis none, but alternative_denominator_per_share {alt} != "
                      f"declared_denominator_per_share {dec}")
        bad = [s["name"] for s in hs if s.get("fv_alt") is not None and s["fv"] and abs(s["fv_alt"] / s["fv"] - 1) > 1e-3]
        if bad:
            lg.append(f"{label}C1 alternative_denominator_basis none, but fair_value_alternative_denominator differs from "
                      f"fair_value for {', '.join(bad)}")
    if ratio is not None and basis != "none" and (ratio <= 0 or ratio < 0.5 or ratio > 2.0):
        lg.append(f"{label}alternative / declared denominator ratio {ratio:.4f} outside 0.5-2.0 or of opposite sign "
                  f"(listed in Stage 6)")
    spend = num(fr.get("acq_spend_normalised_per_share"))
    if ratio is not None and ratio > 0:
        for s in hs:
            fa, fv = s.get("fv_alt"), s["fv"]
            if fa is None or fv is None or abs(fv - bsa) < 1e-9 or abs(fa / fv - 1) < 1e-9:
                continue
            if s.get("acq_deducted") is True and spend not in (None, 0.0):   # the deduction is not scaled: not checkable
                continue
            r_s = (fa - bsa) / (fv - bsa)
            if abs(r_s / ratio - 1) > 0.01:
                lg.append(f"{label}C4 {s['name']}: alternative fair value scales operating value by {r_s:.4f}; the "
                          f"denominators' ratio is {ratio:.4f}")
    neutral = valued > 0 and all(s.get("fv_alt") is not None and s["fv"] and abs(s["fv_alt"] / s["fv"] - 1) <= 1e-6
                                 for s in hs)
    if neutral and basis != "none" and ratio is not None and abs(ratio - 1) > 1e-9:
        lg.append(f"{label}C1 every seat's alternative fair value equals its fair value although the basis is "
                  f"{basis or 'missing'} and the ratio {ratio:.4f}: the run counts as none")
    if basis == "none" or neutral or ratio is None or abs(ratio - 1) <= 1e-9:
        direction = "none"
    else:
        direction = "up" if ratio > 1 else "down"
    return dict(direction=direction, ratio=ratio, valued=valued, n=len(hs), basis=basis or None)


# ----------------------------------------------------------------------------- v10 (T1-T4, T6)
def forecast_growth(fc):
    """T6 monitor: compound annual growth (percent) of cash_flow_total from the first to the fifth forecast_5y period,
    by period_end; years = months of periods 2-5 / 12 when every one is given, else 4. None unless both are positive."""
    if not isinstance(fc, list):
        return None
    xs = [x for x in fc if isinstance(x, dict) and num(x.get("cash_flow_total")) is not None and x.get("period_end")]
    xs = sorted(xs, key=lambda x: str(x.get("period_end")))[:5]
    if len(xs) < 5:
        return None
    a, b = num(xs[0]["cash_flow_total"]), num(xs[4]["cash_flow_total"])
    if not (a and b and a > 0 and b > 0):
        return None
    mo = [num(x.get("months")) for x in xs[1:]]
    yrs = sum(mo) / 12.0 if all(m is not None and m > 0 for m in mo) else 4.0
    return ((b / a) ** (1.0 / yrs) - 1.0) * 100.0 if yrs > 0 else None


def walter_components_valid(g):
    comps = g.get("components") if isinstance(g, dict) and isinstance(g.get("components"), dict) else {}
    vals = [num(comps.get(c)) for c in GRADE_COMPONENTS]
    if all(v is not None and abs(v - round(v)) < 1e-9 and -2 - EPS <= v <= 2 + EPS for v in vals):
        return vals
    return None


def walter_multiplier(g):
    """T4: 1 + WALTER_K x the components' sum where they are valid; else the reported multiplier, else from the score."""
    if not isinstance(g, dict):
        return None
    vals = walter_components_valid(g)
    if vals is not None:
        return 1 + WALTER_K * sum(vals)
    m = num(g.get("multiplier"))
    if m is not None:
        return m
    sc = num(g.get("score"))
    return (1 + WALTER_K * sc) if sc is not None else None


def walter_fails(g):
    gates = g.get("gates") if isinstance(g, dict) and isinstance(g.get("gates"), dict) else {}
    return sum(1 for v in gates.values() if str(v or "").strip().upper() == "FAIL")


def off_base(seat, mb):
    """T1: a seated investor whose rate is missing or not the macro base, or whose reported fair_value_macro_base differs
    from its fair_value (0.1% or 0.01, whichever is larger). mb is MARKET_INPUTS' risk-free + ERP where known."""
    if seat["irr"]:
        return False
    if mb is not None and (seat.get("rate") is None or abs(seat["rate"] - mb) > RATE_TOL + EPS):
        return True
    return fv_off_base(seat)


def fv_off_base(seat):
    f, m = seat.get("fv"), seat.get("fv_mb_rep")
    return f is not None and m is not None and abs(f - m) > max(0.001 * abs(f), 0.01) + EPS


def run_macro_base(frame):
    fr = frame or {}
    mb = num(fr.get("macro_base"))
    if mb is None and num(fr.get("risk_free")) is not None and num(fr.get("erp")) is not None:
        mb = num(fr.get("risk_free")) + num(fr.get("erp"))
    return mb


def market_base(mi, frame=None):
    """T1: the macro base every seat must use: MARKET_INPUTS' risk-free + rebased ERP (configuration), else the run's."""
    mi = mi or {}
    if num(mi.get("risk_free")) is not None and num(mi.get("erp")) is not None:
        return num(mi["risk_free"]) + num(mi["erp"])
    return run_macro_base(frame)


def buy_effect(entry, seat):
    """T6 monitor: the BUY effect (unit) of one register entry, derived from its channel and signed size (descriptive)."""
    ch = str(entry.get("channel") or "").strip().lower()
    size = num(entry.get("size"))
    if size is None or seat is None or seat.get("fv") is None or seat.get("required") is None:
        return None
    fv, req = seat["fv"], seat["required"]
    if ch == "base_cash_flows":
        return size * (1 - req)
    if ch == "break_branch":
        return -size / 100.0 * fv
    if ch == "quality_score":
        sc = seat.get("score")
        return fv * (premium(sc - size) - premium(sc)) if sc is not None else None
    if ch == "fv_mapping":
        return size / 100.0 * fv * (1 - req)
    if ch == "non_break_branch":
        return 0.0
    return None


def v10_checks(S, seats, mi=None, log=None, label=""):
    """T1-T4 checks: logged, never corrected; they move no number. Returns the run's monitor fields."""
    lg = log if log is not None else []
    fr = S.get("frame") or {}
    out = dict(off_base=0, off_seats=[], debt_deducted=False, risk_class=None, walter_multiplier=None, walter_score=None,
               register=dict(present=False, n=0, issues=0, by_channel={}), issues=0)
    rf, erp, mb_rep = num(fr.get("risk_free")), num(fr.get("erp")), num(fr.get("macro_base"))
    mb = market_base(mi, fr)

    def bad(msg):
        out["issues"] += 1
        lg.append(f"{label}{msg}")
    if mb_rep is not None and rf is not None and erp is not None and abs(mb_rep - (rf + erp)) > RATE_TOL + EPS:
        bad(f"C2 macro_base {mb_rep} is not risk_free + erp ({rf} + {erp})")
    mi = mi or {}
    for f in ("risk_free", "erp"):
        if num(mi.get(f)) is not None and num(fr.get(f)) is not None and abs(num(fr.get(f)) - num(mi[f])) > RATE_TOL + EPS:
            bad(f"C2 {f} {fr.get(f)} differs from MARKET_INPUTS {mi[f]}")
    if mb_rep is not None and mb is not None and abs(mb_rep - mb) > RATE_TOL + EPS:
        bad(f"C2 the run's macro_base {mb_rep} is not MARKET_INPUTS' {mb:.4f}")
    seated = [s_ for s_ in seats if not s_["irr"]]
    by_name = {s_["name"]: s_ for s_ in seated}
    for s_ in seated:
        if s_.get("rate") is None:
            bad(f"{s_['name']}: C2 no discount_rate reported")
        if s_.get("fv_mb_rep") is None:
            bad(f"{s_['name']}: C2 no fair_value_macro_base reported")
        if off_base(s_, mb):
            out["off_base"] += 1
            out["off_seats"].append(s_["name"])
            bad(f"{s_['name']}: C2 off the macro base (discount_rate {s_.get('rate')} vs MARKET_INPUTS macro base {mb}; "
                f"fair_value {s_.get('fv')} vs fair_value_macro_base {s_.get('fv_mb_rep')}); a route-(d) finding, patched by rebase")
    # T2 debt: cash flow to equity, no claim deducted
    dd, nc, bsa = num(fr.get("debt_deducted_per_share")), num(fr.get("net_claims_per_share")), num(fr.get("balance_sheet_add_per_share"))
    if dd is None:
        bad("C8 debt_deducted_per_share missing")
    elif abs(dd) > 1e-9:
        out["debt_deducted"] = True
        bad(f"C1 a claim of {dd} per share deducted from cash flow to equity: debt counted twice (patched by undebt)")
    if nc is None:
        bad("C8 net_claims_per_share missing (the debt row cannot be measured)")
    if bsa is not None and bsa < -1e-9:
        lg.append(f"{label}note: balance_sheet_add_per_share {bsa} is negative; the critic checks that it holds no debt, "
                  f"preferred, minority or lease claim")
    rc = str(fr.get("systematic_risk_class") or "").strip().lower()
    out["risk_class"] = rc if rc in RISK_CLASSES else None
    if rc not in RISK_CLASSES:
        bad(f"C8 systematic_risk_class {fr.get('systematic_risk_class')!r} is not defensive, average or cyclical")
    # T3 risk register
    risks = S.get("risks")
    names = set(by_name)
    reg = out["register"]
    if not isinstance(risks, list):
        reg["issues"] += 1
        bad("C6 no risk register (risks)")
    else:
        reg["present"] = True
        seen, covered = {}, set()
        for i, e in enumerate(risks):
            reg["n"] += 1
            if not isinstance(e, dict):
                reg["issues"] += 1
                bad(f"C6 risk entry {i} is not an object")
                continue
            seat = canon(e.get("seat"))
            ch = str(e.get("channel") or "").strip().lower()
            size = num(e.get("size"))
            rk = re.sub(r"\s+", " ", str(e.get("risk") or "").strip().lower())
            covered.add(seat)
            if seat not in names:
                reg["issues"] += 1
                bad(f"C6 risk entry {i} ({rk[:40]!r}) names no seated investor ({e.get('seat')!r})")
            if ch not in CHANNELS:
                reg["issues"] += 1
                bad(f"C6 risk entry {i} ({rk[:40]!r}): channel {e.get('channel')!r} is not on the closed list")
            elif ch == "not_priced":
                if not str(e.get("reason_or_null") or "").strip():
                    reg["issues"] += 1
                    bad(f"C6 risk entry {i} ({rk[:40]!r}): not_priced without a reason")
            elif size is None:
                reg["issues"] += 1
                bad(f"C6 risk entry {i} ({rk[:40]!r}): no numeric size")
            if ch == "fv_mapping" and seat not in ("walter", "alexander"):
                reg["issues"] += 1
                bad(f"C6 risk entry {i} ({rk[:40]!r}): fv_mapping for {seat}, which has no fair-value mapping")
            if ch in CHANNELS:
                bc = reg["by_channel"].setdefault(ch, dict(n=0, size=0.0, buy_effect=0.0))
                bc["n"] += 1
                bc["size"] += size or 0.0
                be = buy_effect(e, by_name.get(seat))
                bc["buy_effect"] += be or 0.0
            seen.setdefault((seat, rk), set()).add(ch)
        for (seat, rk), chs in seen.items():
            if len(chs) > 1:
                reg["issues"] += 1
                bad(f"C6 {seat}: risk {rk[:60]!r} entered in {len(chs)} channels ({', '.join(sorted(chs))}): double count")
        for nm in sorted(names - covered):
            reg["issues"] += 1
            bad(f"{nm}: C6 no entry in the risk register")
    # T4 seat mappings
    for inv in S.get("investors", []):
        nm = canon(inv.get("investor"))
        if nm == "walter" and nm in names:
            g = inv.get("management_grade")
            if not isinstance(g, dict):
                bad("walter: C5 no management_grade")
                continue
            comps = g.get("components") if isinstance(g.get("components"), dict) else {}
            vals = []
            for c in GRADE_COMPONENTS:
                v = num(comps.get(c))
                if v is None or abs(v - round(v)) > 1e-9 or v < -2 - EPS or v > 2 + EPS:
                    bad(f"walter: C5 grade component {c} {comps.get(c)!r} is not an integer from -2 to +2")
                else:
                    vals.append(v)
            sc_rep, mult = num(g.get("score")), num(g.get("multiplier"))
            sc = sum(vals) if len(vals) == len(GRADE_COMPONENTS) else sc_rep
            if sc_rep is not None and len(vals) == len(GRADE_COMPONENTS) and abs(sc_rep - sum(vals)) > 1e-9:
                bad(f"walter: C5 grade score {sc_rep} is not the sum of its components ({sum(vals):g})")
            if mult is None:
                bad("walter: C5 no grade multiplier")
            elif sc is not None and abs(mult - (1 + WALTER_K * sc)) > 0.0005 + EPS:
                bad(f"walter: C5 multiplier {mult} is not 1 + {WALTER_K} x {sc:g} = {1 + WALTER_K * sc:.4f}")
            gates = g.get("gates") if isinstance(g.get("gates"), dict) else {}
            fails = 0
            for gate, comp in GATE_COMPONENT.items():
                st = str(gates.get(gate) or "").strip().upper()
                if st not in ("PASS", "CAUTION", "FAIL"):
                    bad(f"walter: C5 gate {gate} {gates.get(gate)!r} is not PASS, CAUTION or FAIL")
                    continue
                cap = -1 if st == "CAUTION" else -2 if st == "FAIL" else None
                v = num(comps.get(comp))
                if cap is not None and v is not None and v > cap + EPS:
                    bad(f"walter: C5 gate {gate} {st} but component {comp} is {v:g} (cap {cap})")
                fails += st == "FAIL"
            if fails >= 2 and not bool(inv.get("no_buy")):
                bad(f"walter: C5 {fails} FAILs but the seat is not NO BUY")
            out["walter_multiplier"], out["walter_score"] = walter_multiplier(g), sc
        if nm == "alexander" and nm in names:
            e = inv.get("earnings_quality")
            if not isinstance(e, dict) or num(e.get("score")) is None or num(e.get("adjustment")) is None:
                bad("alexander: C5 no earnings_quality score and adjustment")
                continue
            q, a = num(e.get("score")), num(e.get("adjustment"))
            want = 0.10 if q > 80 + EPS else (0.0 if q >= 60 - EPS else -0.15)
            if q < 0 - EPS or q > 100 + EPS or abs(a - want) > 1e-6:
                bad(f"alexander: C5 earnings_quality score {q:g} maps to {want:+.2f}, reported {a:+.4f}")
    return out


def seat_mapping_row(S):
    """T4 table for statistics.md: Walter's components, gates, score and multiplier; Alexander's score and adjustment."""
    row = {}
    for inv in S.get("investors", []):
        nm = canon(inv.get("investor"))
        if nm == "walter" and isinstance(inv.get("management_grade"), dict):
            g = inv["management_grade"]
            comps = g.get("components") if isinstance(g.get("components"), dict) else {}
            gates = g.get("gates") if isinstance(g.get("gates"), dict) else {}
            row["walter"] = dict(components=[comps.get(c) for c in GRADE_COMPONENTS],
                                 gates=[gates.get(x) for x in GATE_COMPONENT], score=g.get("score"),
                                 multiplier=walter_multiplier(g), no_buy=bool(inv.get("no_buy")))
        if nm == "alexander" and isinstance(inv.get("earnings_quality"), dict):
            row["alexander"] = dict(score=inv["earnings_quality"].get("score"),
                                    adjustment=inv["earnings_quality"].get("adjustment"))
    return row


def cf_debt(seats, frame, log=None, label=""):
    """T2 debt row: the v9 count reapplied. Every headline seat's fair value (and so every branch) less the run's
    net_claims_per_share, its required margin held fixed. Returns (seats, measured); a run with no or zero net claims
    keeps its seats."""
    lg = log if log is not None else []
    nc = num((frame or {}).get("net_claims_per_share"))
    if nc is None or abs(nc) < 1e-12:
        return [dict(s_) for s_ in seats], False
    out = []
    for s_ in seats:
        t = dict(s_)
        if not s_["irr"] and not s_["no_buy"] and s_.get("buy") is not None and s_.get("fv") is not None:
            f = s_["fv"] - nc
            if f <= 0:
                t["fv"], t["buy"], t["no_buy"] = f, None, True
                lg.append(f"{label}{s_['name']}: fair value {f:.4f} <= 0 in the debt row; NO BUY there, weight dropped")
            else:
                t["fv"], t["buy"] = f, f * (1 - s_["required"])
        out.append(t)
    return out, True


def rebase_patches(summary, investor):
    """T1: the route-(d) patch set for a seat off the macro base: fair_value -> fair_value_macro_base, every non-break
    branch scaled by the same ratio, the break value held (approximation). Returns (patches, None) or (None, reason)."""
    inv = find_inv(summary, investor)
    if inv is None:
        return None, f"no investor {investor!r} in the summary"
    fv, fmb = num(inv.get("fair_value")), num(inv.get("fair_value_macro_base"))
    if fv is None or fmb is None or fv <= 0 or fmb <= 0:
        return None, "fair_value or fair_value_macro_base missing or not positive: CONFIRMED-unquantified"
    if abs(fmb - fv) <= max(0.001 * abs(fv), 0.01):
        return None, "fair_value_macro_base equals fair_value: nothing to rebase (CONFIRMED-unquantified if the rate is off)"
    nm, ratio = str(inv.get("investor")), fmb / fv
    P = [{"path": f"investors.{nm}.fair_value", "from": fv, "to": fmb},
         {"path": f"investors.{nm}.fair_value_macro_base", "from": fmb, "to": fmb}]
    for b in inv.get("tree") or []:
        if isinstance(b, dict) and num(b.get("value")) is not None and str(b.get("branch")).strip().lower() != "break":
            P.append({"path": f"investors.{nm}.tree.{str(b.get('branch')).strip()}.value",
                      "from": num(b["value"]), "to": num(b["value"]) * ratio})
    return P, None


def undebt_patches(summary):
    """T2: the patch set for a run that deducted claims from cash flow to equity: debt_deducted_per_share added back to
    every seat's fair value, fair_value_macro_base, tree values and companion fair values, and to the balance-sheet add.
    Returns (patches, None) or (None, reason)."""
    fr = summary.get("frame") or {}
    d = num(fr.get("debt_deducted_per_share"))
    if d is None or abs(d) < 1e-12:
        return None, "debt_deducted_per_share is 0 or missing: nothing to add back (CONFIRMED-unquantified)"
    P = []
    bsa = num(fr.get("balance_sheet_add_per_share"))
    if bsa is not None:
        P.append({"path": "frame.balance_sheet_add_per_share", "from": bsa, "to": bsa + d})
    for inv in summary.get("investors", []):
        nm = str(inv.get("investor"))
        if canon(nm) in IRR_NAMES or (v10() and canon(nm) in V10_UNSEATED) or num(inv.get("fair_value")) is None:
            continue
        for f in ("fair_value", "fair_value_macro_base", "fair_value_rf_plus_50bp", "fair_value_other_acquisition_basis",
                  "fair_value_alternative_denominator"):
            if num(inv.get(f)) is not None:
                P.append({"path": f"investors.{nm}.{f}", "from": num(inv[f]), "to": num(inv[f]) + d})
        for b in inv.get("tree") or []:
            if isinstance(b, dict) and num(b.get("value")) is not None:
                P.append({"path": f"investors.{nm}.tree.{str(b.get('branch')).strip()}.value",
                          "from": num(b["value"]), "to": num(b["value"]) + d})
    return P, None


def is_rebase(summary, patches):
    """True if a finding's patches are exactly one seat's rebase set (fold-log label: approximate)."""
    try:
        seats = {p["path"].split(".")[1] for p in patches if isinstance(p, dict) and str(p.get("path", "")).startswith("investors.")}
        if len(seats) != 1:
            return False
        P, _ = rebase_patches(summary, seats.pop())
        if not P or len(P) != len(patches):
            return False
        want = {p["path"]: p["to"] for p in P}
        return all(p["path"] in want and num(p.get("to")) is not None and
                   abs(num(p["to"]) - want[p["path"]]) <= max(1e-6, 1e-6 * abs(want[p["path"]])) for p in patches)
    except Exception:
        return False


def v6_bridge_run(summary, seats, log=None, label=""):
    """v6-rule bridge (own trees, no inheritance)."""
    lg = log if log is not None else []
    fvs = [s["fv"] for s in seats if s["fv"] is not None]
    M = statistics.median(fvs) if fvs else None
    rep_M = num(summary.get("committee_median_fv"))
    if M is not None and rep_M is not None and abs(rep_M - M) > max(0.01, 1e-4 * M):
        lg.append(f"{label}committee_median_fv reported {rep_M} vs script {M:.4f}")
    out = []
    for s in seats:
        t = dict(s)
        asym = 0.0
        if s.get("uncomputable") or s["fv"] is None:
            out.append(t)
            continue
        if s["tree_ok"] and M is not None:
            ED = sum(b["p"] * max(0.0, M - b["value"]) for b in s["tree_f"])
            EU = sum(b["p"] * max(0.0, b["value"] - M) for b in s["tree_f"])
            R = (ED / EU) if EU > 0 else 3.0
            asym = clamp(0.10 * (R - 1), -0.10, 0.15)
        else:
            lg.append(f"{label}{s['name']}: v6 bridge without a valid tree; asym = 0")
        req, nb = v6_required(TIERS.index(s["tier"]), s["p"], s.get("L_own", s["L"]), asym)
        nb = nb or s["framework_nobuy"]
        t.update(v6_asym=asym, v6_required=req, no_buy=nb, buy=None if nb else s["fv"] * (1 - req))
        out.append(t)
    return out, M


def v6_required(tier_idx, p, L, asym):
    gate = (p >= 0.15 - EPS) and (L >= 0.40 - EPS)
    if not gate:
        pre = TIER_BASE[TIERS[tier_idx]] + asym
        req = clamp(pre, CLAMP_LO, CLAMP_HI)
    else:
        below = TIERS[min(tier_idx + 1, 3)]
        pre = TIER_BASE[below] + asym
        req = clamp(max(0.40, pre), CLAMP_LO, CLAMP_HI)
    return req, pre > NOBUY_BOUND + EPS


# ----------------------------------------------------------------------------- patches
COMPANION_INV = {"fair_value_rf_plus_50bp", "fair_value_other_acquisition_basis"}
COMPANION_FRAME = {"valuation_date", "per_share_count_m", "per_share_count_date", "balance_sheet_add_per_share"}
COMPANION_FRAME_V71 = {"valuation_date", "per_share_count_date", "balance_sheet_add_per_share"}


def companion_frame():
    """v7.1: share counts are never patched (the script normalises them, spec Appendix F)."""
    return COMPANION_FRAME_V71 if v71() else COMPANION_FRAME


def parse_path(path):
    parts = str(path).split(".")
    if len(parts) >= 3 and parts[0] == "investors":
        inv = parts[1]
        if len(parts) >= 5 and parts[2] == "tree":
            return ("tree", inv, ".".join(parts[3:-1]), parts[-1])
        if len(parts) == 3:
            return ("inv", inv, parts[2], None)
    if len(parts) == 3 and parts[0] == "frame" and parts[1] == "weights":
        return ("weight", parts[2], None, None)
    if len(parts) == 2 and parts[0] == "frame" and parts[1] in companion_frame():
        return ("frame", None, parts[1], None)
    if path == "helena_floor.floor_per_share_or_null":
        return ("floor", None, None, None)
    return None


def _dec_tol(x):
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        return 1e-6
    r = repr(float(x))
    d = len(r.split(".")[1]) if "." in r and "e" not in r else 6
    d = max(d, 2)
    return max(1e-6, 0.5 * 10 ** (-d) + 1e-12)


def same(cur, frm):
    if frm is None or cur is None:
        return frm is None and cur is None
    if isinstance(frm, bool) or isinstance(cur, bool):
        return bool(frm) == bool(cur) and isinstance(frm, bool) == isinstance(cur, bool)
    a, b = num(cur), num(frm)
    if a is not None and b is not None and not isinstance(frm, str):
        return abs(a - b) <= _dec_tol(frm)
    return str(cur).strip() == str(frm).strip()


def find_inv(summary, name):
    c = canon(name)
    for inv in summary.get("investors", []):
        if canon(inv.get("investor")) == c:
            return inv
    return None


def apply_patches(summary, patches):
    """Validate and apply. Returns (new_summary, ok, reasons, notes)."""
    S = copy.deepcopy(summary)
    reasons, notes = [], []
    if not isinstance(patches, list):
        return S, False, ["patch set is not a list"], notes
    touched_seats, has_value_patch, new_branches = set(), False, {}
    fv_patched, fv50_patched = set(), set()
    seat_fields = {}
    for pt in patches:
        if not isinstance(pt, dict) or "path" not in pt:
            reasons.append(f"malformed patch {pt}")
            continue
        path, frm, to = pt.get("path"), pt.get("from"), pt.get("to")
        pp = parse_path(path)
        if pp is None:
            reasons.append(f"path not on the closed list: {path}")
            continue
        kind, a, b, c = pp
        if v8() and kind in ("tree", "inv", "weight"):
            inv_x = find_inv(S, a)
            if canon(a) in IRR_NAMES or (inv_x is not None and bool(inv_x.get("irr_entry"))):
                notes.append(f"patch {path} to a seat outside the roster (G2): dropped, no effect")
                continue
        if kind == "tree":
            inv = find_inv(S, a)
            if inv is None:
                reasons.append(f"unknown investor in {path}")
                continue
            if c not in ("p", "value"):
                reasons.append(f"path not on the closed list: {path}")
                continue
            tree = inv.get("tree")
            if not isinstance(tree, list):
                tree = inv["tree"] = []
            br = [x for x in tree if str(x.get("branch", "")).strip().lower() == b.strip().lower()]
            if br:
                cur = br[0].get(c)
                if not same(cur, frm):
                    reasons.append(f"from mismatch at {path}: current {cur}, from {frm}")
                    continue
                if to is None:
                    tree.remove(br[0])
                else:
                    br[0][c] = to
            else:
                if frm is not None:
                    reasons.append(f"from mismatch at {path}: branch absent, from {frm}")
                    continue
                if to is None:
                    reasons.append(f"cannot remove absent branch {path}")
                    continue
                key = (canon(a), b)
                nb = new_branches.setdefault(key, {"branch": b})
                nb[c] = to
            touched_seats.add(canon(a))
            has_value_patch = True
        elif kind == "inv":
            inv = find_inv(S, a)
            if inv is None:
                reasons.append(f"unknown investor in {path}")
                continue
            allowed_inv = ("fair_value", "quality_score", "quality_tier", "no_buy", "break_p", "break_loss",
                           "fair_value_rf_plus_50bp")
            if v71():
                allowed_inv = allowed_inv + ("fair_value_macro_base", "fair_value_other_acquisition_basis",
                                             "growth_basis", "acq_spend_deducted")
            if v9():
                allowed_inv = allowed_inv + ("fair_value_alternative_denominator",)
            if b not in allowed_inv:
                reasons.append(f"path not on the closed list: {path}")
                continue
            cur = inv.get(b)
            if not same(cur, frm):
                reasons.append(f"from mismatch at {path}: current {cur}, from {frm}")
                continue
            if b == "quality_score" and v8() and (num(to) is None or num(to) < 0 or num(to) > 100):
                reasons.append(f"quality_score patch outside 0-100: {path}")
                continue
            if b == "no_buy" and not isinstance(to, bool):
                reasons.append(f"no_buy patch must be boolean: {path}")
                continue
            if b == "acq_spend_deducted" and not isinstance(to, bool):
                reasons.append(f"acq_spend_deducted patch must be boolean: {path}")
                continue
            if b == "growth_basis" and to not in ("organic", "including_acquisitions"):
                reasons.append(f"growth_basis patch must be organic or including_acquisitions: {path}")
                continue
            inv[b] = to
            if b == "no_buy" and to is True:
                inv["_no_buy_patched"] = "verifier patch"
            seat_fields.setdefault(canon(a), set()).add(b)
            touched_seats.add(canon(a))
            if b == "fair_value":
                fv_patched.add(canon(a))
                has_value_patch = True
            if b == "fair_value_rf_plus_50bp":
                fv50_patched.add(canon(a))
            if b == "fair_value_alternative_denominator":
                seat_fields.setdefault("__alt__", set()).add(canon(a))
            if b == "fair_value_other_acquisition_basis":
                oth_patched = seat_fields.setdefault("__oth__", set())
                oth_patched.add(canon(a))
        elif kind == "weight":
            w = S.setdefault("frame", {}).setdefault("weights", {})
            keyname = None
            for k in w:
                if canon(k) == canon(a):
                    keyname = k
            cur = w.get(keyname) if keyname else None
            if not same(cur, frm):
                reasons.append(f"from mismatch at {path}: current {cur}, from {frm}")
                continue
            tv = num(to)
            if tv is None or tv < -EPS or tv > 2.0 + EPS:
                reasons.append(f"weight outside 0-2.0 at {path}")
                continue
            w[keyname or a] = to
        elif kind == "frame":
            cur = S.setdefault("frame", {}).get(b)
            if not same(cur, frm):
                reasons.append(f"from mismatch at {path}: current {cur}, from {frm}")
                continue
            S["frame"][b] = to
            notes.append(f"companion {b}")
        elif kind == "floor":
            hf = S.setdefault("helena_floor", {})
            cur = hf.get("floor_per_share_or_null")
            if not same(cur, frm):
                reasons.append(f"from mismatch at {path}: current {cur}, from {frm}")
                continue
            hf["floor_per_share_or_null"] = to
    for (inv_c, bname), nb in new_branches.items():
        if "p" not in nb or "value" not in nb:
            reasons.append(f"new branch {bname} for {inv_c} needs both p and value")
            continue
        inv_t = find_inv(S, inv_c)
        if not isinstance(inv_t.get("tree"), list):
            inv_t["tree"] = []
        inv_t["tree"].append(nb)
    # companion rules
    for n in fv50_patched:
        if n not in fv_patched and not any(k[0] == n for k in new_branches) and n not in {
                canon(x.split(".")[1]) for x in [p.get("path", "") for p in patches if isinstance(p, dict)]
                if x.startswith("investors.") and ".tree." in x}:
            reasons.append(f"companion fair_value_rf_plus_50bp for {n} without a fair-value or tree patch")
    if any(nm.startswith("companion") for nm in notes) and not has_value_patch:
        reasons.append("frame companion patch without any fair-value or tree patch")
    # quality_tier must match score; break_p/break_loss only for seats without a valid tree
    oth_set = seat_fields.pop("__oth__", set())
    alt_set = seat_fields.pop("__alt__", set())
    tree_seats = {canon(x.split(".")[1]) for x in [p.get("path", "") for p in patches if isinstance(p, dict)]
                  if x.startswith("investors.") and ".tree." in x}
    alone_alt = False
    for n in alt_set:   # v9 N2: a companion, only with a fair-value or tree patch to the same seat, or alone only
        if n not in fv_patched and n not in tree_seats:   # to set it equal to the seat's fair value (definition broken)
            inv_n, inv_0 = find_inv(S, n), find_inv(summary, n)
            fa_n = num((inv_n or {}).get("fair_value_alternative_denominator"))
            fv_0 = num((inv_0 or {}).get("fair_value"))
            if not (fa_n is not None and fv_0 is not None and abs(fa_n - fv_0) <= max(1e-6, 1e-4 * abs(fv_0))):
                reasons.append(f"companion fair_value_alternative_denominator for {n} without a fair-value or tree patch "
                               f"(alone it may only be set equal to the seat's fair_value)")
            else:
                alone_alt = True
    if alone_alt:   # the neutralising patch covers every seat of the run that reports the field (spec Appendix F)
        left = [i_.get("investor") for i_ in S.get("investors", [])
                if num(i_.get("fair_value_alternative_denominator")) is not None and num(i_.get("fair_value"))
                and abs(num(i_["fair_value_alternative_denominator"]) / num(i_["fair_value"]) - 1) > 1e-4]
        if left:
            reasons.append(f"fair_value_alternative_denominator patched alone must set every seat's value to its "
                           f"fair_value; not done for {', '.join(map(str, left))}")
    if v71():
        for nme in touched_seats | oth_set:
            f = seat_fields.get(nme, set())
            inv0 = find_inv(summary, nme)
            tree_p = nme in {canon(x.split(".")[1]) for x in [p.get("path", "") for p in patches if isinstance(p, dict)]
                             if x.startswith("investors.") and ".tree." in x}
            if "fair_value" in f and inv0 is not None and inv0.get("fair_value_macro_base") is not None \
                    and "fair_value_macro_base" not in f:
                reasons.append(f"fair_value patched for {nme} without a fair_value_macro_base patch "
                               f"(patch it, from = to if the fix leaves it unchanged)")
            if f & {"growth_basis", "acq_spend_deducted"} and nme not in oth_set:
                reasons.append(f"acquisition declaration patched for {nme} without a fair_value_other_acquisition_basis patch")
            if nme in oth_set and not (f & {"fair_value", "growth_basis", "acq_spend_deducted"} or tree_p):
                reasons.append(f"companion fair_value_other_acquisition_basis for {nme} without a fair-value, tree "
                               f"or acquisition-declaration patch")
    for n in touched_seats:
        inv = find_inv(S, n)
        f = seat_fields.get(n, set())
        if "quality_tier" in f:
            t_new = norm_tier(inv.get("quality_tier"))
            t_score = tier_of(num(inv.get("quality_score")))
            if t_new != t_score:
                reasons.append(f"quality_tier patch for {n} does not match quality_score")
        ok, why = check_tree(inv.get("tree"), num(inv.get("fair_value")))
        if f & {"break_p", "break_loss"}:
            if ok:
                reasons.append(f"break_p/break_loss patched for {n}, whose tree is valid")
            continue
        only_meta = f and f <= {"quality_score", "quality_tier", "no_buy", "fair_value_rf_plus_50bp",
                                "fair_value_macro_base", "fair_value_other_acquisition_basis",
                                "fair_value_alternative_denominator"}
        orig = find_inv(summary, n)
        orig_ok, _ = check_tree(orig.get("tree"), num(orig.get("fair_value")))
        if not ok and not (only_meta and not orig_ok):
            reasons.append(f"seat {n} fails tree checks after patches: {'; '.join(why)}")
    # companion: fv patched without fv50 patch -> scale fv50
    for n in fv_patched - fv50_patched:
        inv = find_inv(S, n)
        orig = find_inv(summary, n)
        f0, f1, f50 = num(orig.get("fair_value")), num(inv.get("fair_value")), num(orig.get("fair_value_rf_plus_50bp"))
        if f0 and f1 is not None and f50 is not None:
            inv["fair_value_rf_plus_50bp"] = f50 * (f1 / f0)
            notes.append(f"{n}: fair_value_rf_plus_50bp scaled to {inv['fair_value_rf_plus_50bp']:.4f}")
    if v71():   # companion: fair_value_other_acquisition_basis scales with a fair-value patch unless patched itself
        for n in fv_patched - oth_set:
            if seat_fields.get(n, set()) & {"growth_basis", "acq_spend_deducted"}:
                continue
            inv, orig = find_inv(S, n), find_inv(summary, n)
            f0, f1, fo = num(orig.get("fair_value")), num(inv.get("fair_value")), num(orig.get("fair_value_other_acquisition_basis"))
            if f0 and f1 is not None and fo is not None:
                inv["fair_value_other_acquisition_basis"] = fo * (f1 / f0)
                notes.append(f"{n}: fair_value_other_acquisition_basis scaled to {inv['fair_value_other_acquisition_basis']:.4f}")
    if v9():   # companion: fair_value_alternative_denominator scales with a fair-value patch unless patched itself
        for n in fv_patched - alt_set:
            inv, orig = find_inv(S, n), find_inv(summary, n)
            f0, f1, fa = num(orig.get("fair_value")), num(inv.get("fair_value")), num(orig.get("fair_value_alternative_denominator"))
            if f0 and f1 is not None and fa is not None:
                inv["fair_value_alternative_denominator"] = fa * (f1 / f0)
                notes.append(f"{n}: fair_value_alternative_denominator scaled to {inv['fair_value_alternative_denominator']:.4f}")
    return S, (not reasons), reasons, notes


def run_headline_from_summary(summary, log=None):
    seats = recompute_run(summary, log)
    return headline_of(seats), seats


def mech_flag(v):
    """The verifier's "mechanism" flag. v9: true only for JSON true or the string "true" (any case); compatibility
    modes keep bool(v)."""
    if v9():
        return v is True or (isinstance(v, str) and v.strip().lower() == "true")
    return bool(v)


def is_quantified_confirmed(r):
    rul = str(r.get("ruling", "")).upper()
    return rul.startswith("CONFIRMED") and bool(r.get("quantified")) and not mech_flag(r.get("mechanism")) \
        and isinstance(r.get("changed_inputs"), list) and len(r.get("changed_inputs")) > 0


def fold_run(summary, ver, log=None, label=""):
    """Stage-5b fold for one run, in run units."""
    lg = log if log is not None else []
    h0, _ = run_headline_from_summary(summary, [])
    findings = []
    valid = []
    for r in ver.get("rulings", []) or []:
        fid = str(r.get("finding"))
        rec = dict(finding=fid, ruling=r.get("ruling"), quantified=bool(r.get("quantified")),
                   mechanism=mech_flag(r.get("mechanism")), tag1=r.get("tag1"), tag2=r.get("tag2"),
                   verifier_delta=num(r.get("script_delta")), status=None, standalone_delta=None,
                   reasons=[], paths=[])
        rul = str(r.get("ruling", "")).upper()
        if v9() and "mechanism" in r and not isinstance(r.get("mechanism"), bool):
            lg.append(f"{label}finding {fid}: C8 mechanism flag {r.get('mechanism')!r} is not a boolean; read as "
                      f"{rec['mechanism']}")
        if rec["mechanism"] and rul.startswith("CONFIRMED"):
            rec["status"] = "CONFIRMED-unquantified (MECHANISM)"
        elif is_quantified_confirmed(r):
            S1, ok, why, notes = apply_patches(summary, r["changed_inputs"])
            rec["paths"] = sorted({p.get("path") for p in r["changed_inputs"] if isinstance(p, dict)})
            if ok:
                h1, _ = run_headline_from_summary(S1, [])
                rec["standalone_delta"] = (h1 - h0) if (h1 is not None and h0 is not None) else None
                rec["status"] = "CONFIRMED-quantified (patches accepted)"
                if v10() and is_rebase(summary, r["changed_inputs"]):
                    rec["status"] = "CONFIRMED-quantified (patches accepted; rebase to the macro base, approximate: non-break branches scaled, break held)"
                rec["notes"] = notes
                valid.append(rec)
            else:
                rec["status"] = "CONFIRMED-unquantified (PATCH-INVALID)"
                rec["reasons"] = why
        elif rul.startswith("CONFIRMED"):
            rec["status"] = "CONFIRMED-unquantified"
        else:
            rec["status"] = str(r.get("ruling"))
        if rec["verifier_delta"] is not None and rec["standalone_delta"] is not None and h0:
            if abs(rec["verifier_delta"] - rec["standalone_delta"]) > 0.001 * abs(h0):
                lg.append(f"{label}finding {fid}: verifier delta {rec['verifier_delta']} vs script {rec['standalone_delta']:.4f}")
        findings.append(rec)
    joint = ver.get("joint_changed_inputs") or []
    allowed = set()
    for rec in valid:
        allowed |= set(rec["paths"])
    applied, mode, jreasons = None, None, []
    if joint:
        jpaths = {p.get("path") for p in joint if isinstance(p, dict)}
        if not jpaths <= allowed:
            jreasons.append("joint list contains paths outside the CONFIRMED-quantified findings: " +
                            ", ".join(sorted(str(x) for x in jpaths - allowed)))
        else:
            S1, ok, why, notes = apply_patches(summary, joint)
            if ok:
                applied, mode = S1, "joint_changed_inputs"
                applied_findings = [r["finding"] for r in valid if set(r["paths"]) & jpaths]
            else:
                jreasons += why
    if applied is None:
        # union of valid findings with disjoint paths
        disjoint = []
        for rec in valid:
            others = set()
            for o in valid:
                if o is not rec:
                    others |= set(o["paths"])
            if set(rec["paths"]) & others:
                rec["status"] = "CONFIRMED-unquantified (overlapping paths in fallback union)"
            else:
                disjoint.append(rec)
        allp = []
        src = {r["finding"]: r for r in ver.get("rulings", [])}
        for rec in disjoint:
            allp += src[rec["finding"]]["changed_inputs"] if rec["finding"] in src else []
        if allp:
            S1, ok, why, notes = apply_patches(summary, allp)
            if ok:
                applied, mode = S1, "union of disjoint valid findings" + (" (joint list rejected)" if joint else "")
                applied_findings = [r["finding"] for r in disjoint]
            else:
                jreasons += why
        if applied is None:
            applied, mode, applied_findings = copy.deepcopy(summary), "no patches applied", []
    h1, seats1 = run_headline_from_summary(applied, [])
    jd = (h1 - h0) if (h1 is not None and h0 is not None) else None
    vj = num(ver.get("script_joint_delta"))
    if vj is not None and jd is not None and h0 and abs(vj - jd) > 0.001 * abs(h0):
        lg.append(f"{label}joint: verifier {vj} vs script {jd:.4f}")
    return dict(blind=h0, adjusted=h1, joint_delta=jd, mode=mode, joint_reasons=jreasons, findings=findings,
                applied_findings=applied_findings, summary=applied,
                verifier_joint_delta=vj, verifier_adjusted=num(ver.get("script_adjusted_headline")))


# ----------------------------------------------------------------------------- statistics
def trimmed_point(vals):
    n = len(vals)
    if n >= 6:
        order = sorted(range(n), key=lambda i: (vals[i], i))
        keep = order[1:-1]
        return sum(vals[i] for i in keep) / len(keep), sorted(keep)
    return sum(vals) / n, list(range(n))


def line_point(vals):
    """Trimmed point of a margin-rule line over the runs where it is defined; None if fewer than 3 runs remain."""
    v = [x for x in vals if x is not None]
    return trimmed_point(v)[0] if len(v) >= 3 else None


def pooled_sd(vals, dossiers):
    groups = {}
    for v, d in zip(vals, dossiers):
        groups.setdefault(d, []).append(v)
    N, D = len(vals), len(groups)
    ss = 0.0
    for g in groups.values():
        m = sum(g) / len(g)
        ss += sum((x - m) ** 2 for x in g)
    df = N - D
    return (math.sqrt(ss / df) if df > 0 else None), df


def pooled_cov(x, y, dossiers):
    gx, gy = {}, {}
    for a, b, d in zip(x, y, dossiers):
        gx.setdefault(d, []).append(a)
        gy.setdefault(d, []).append(b)
    N, D = len(x), len(gx)
    s = 0.0
    for d in gx:
        mx, my = sum(gx[d]) / len(gx[d]), sum(gy[d]) / len(gy[d])
        s += sum((a - mx) * (b - my) for a, b in zip(gx[d], gy[d]))
    return s / (N - D) if N - D > 0 else None


def chi2_interval(s, df):
    from scipy import stats
    return s * math.sqrt(df / stats.chi2.ppf(0.95, df)), s * math.sqrt(df / stats.chi2.ppf(0.05, df))


def tq(p, df):
    from scipy import stats
    return float(stats.t.ppf(p, df))


def contrast(vals, dossiers, s_w, df):
    from scipy import stats
    labels = sorted(set(dossiers))
    if len(labels) != 2 or not s_w:
        return None
    a = [v for v, d in zip(vals, dossiers) if d == labels[0]]
    b = [v for v, d in zip(vals, dossiers) if d == labels[1]]
    t = (mean(a) - mean(b)) / (s_w * math.sqrt(1 / len(a) + 1 / len(b)))
    p = 2 * (1 - stats.t.cdf(abs(t), df))
    return dict(t=t, p=p, df=df, camp_means={labels[0]: mean(a), labels[1]: mean(b)},
                n={labels[0]: len(a), labels[1]: len(b)})


def ols_scale(y, lnk, lnj, groups):
    import numpy as np
    labels = sorted(set(groups))
    N = len(y)
    Xd = np.array([[1.0 if g == l else 0.0 for l in labels] for g in groups])
    X = np.column_stack([np.array(lnk), np.array(lnj), Xd])
    Y = np.array(y)
    beta, *_ = np.linalg.lstsq(X, Y, rcond=None)
    res = Y - X @ beta
    rss_u = float(res @ res)
    br, *_ = np.linalg.lstsq(Xd, Y, rcond=None)
    rr = Y - Xd @ br
    rss_r = float(rr @ rr)
    dfr = N - X.shape[1]
    out = dict(beta_k=float(beta[0]), beta_j=float(beta[1]), df=dfr, rss_u=rss_u, rss_r=rss_r)
    if dfr > 0:
        s2 = rss_u / dfr
        cov = s2 * np.linalg.pinv(X.T @ X)
        se_k, se_j = math.sqrt(max(cov[0, 0], 0)), math.sqrt(max(cov[1, 1], 0))
        tc = tq(0.95, dfr)
        out.update(se_k=se_k, se_j=se_j, ci_k=(beta[0] - tc * se_k, beta[0] + tc * se_k),
                   ci_j=(beta[1] - tc * se_j, beta[1] + tc * se_j))
        out["F"] = ((rss_r - rss_u) / 2) / (rss_u / dfr) if rss_u > 1e-300 else float("inf")
    else:
        out["F"] = None
    return out


def perm_test(y, lnk, lnj, groups, max_enum=200000, mc=20000):
    import random
    obs = ols_scale(y, lnk, lnj, groups)
    if obs.get("F") is None:
        return obs, None, 0
    idx = {}
    for i, g in enumerate(groups):
        idx.setdefault(g, []).append(i)
    total = 1
    for g in idx.values():
        total *= math.factorial(len(g))
    pairs = list(zip(lnk, lnj))

    def F_for(perm_map):
        k2, j2 = [None] * len(y), [None] * len(y)
        for i, src in perm_map.items():
            k2[i], j2[i] = pairs[src]
        return ols_scale(y, k2, j2, groups)["F"]
    count, n = 0, 0
    if total <= max_enum:
        lists = [list(itertools.permutations(v)) for v in idx.values()]
        keys = list(idx.values())
        for combo in itertools.product(*lists):
            pm = {}
            for orig, perm in zip(keys, combo):
                for a, b in zip(orig, perm):
                    pm[a] = b
            F = F_for(pm)
            n += 1
            if F >= obs["F"] - 1e-9 * max(1.0, abs(obs["F"])):
                count += 1
    else:
        rng = random.Random(20260930)
        for _ in range(mc):
            pm = {}
            for v in idx.values():
                sh = v[:]
                rng.shuffle(sh)
                for a, b in zip(v, sh):
                    pm[a] = b
            F = F_for(pm)
            n += 1
            if F >= obs["F"] - 1e-9 * max(1.0, abs(obs["F"])):
                count += 1
    return obs, count / n, n


def spearman(x, y):
    from scipy import stats
    pts = [(a, b) for a, b in zip(x, y) if a is not None and b is not None]
    if len(pts) < 3 or len({a for a, _ in pts}) < 2:
        return None
    r = stats.spearmanr([a for a, _ in pts], [b for _, b in pts])
    return float(r.correlation if hasattr(r, "correlation") else r[0])


def classify_adj(item):
    s = str(item).lower()
    for name, rx in ADJ_CLASSES:
        if re.search(rx, s):
            return name
    return "other"


# ----------------------------------------------------------------------------- stage 3
PS_FIELDS = {"balance_sheet_add_per_share", "gross_denominator_per_share", "declared_denominator_per_share",
             "alternative_denominator_per_share", "acq_spend_normalised_per_share",
             "net_claims_per_share", "debt_deducted_per_share"}   # the last two: v10 T2 (balance-sheet amounts)
SH_FIELDS = {"share_count_m", "per_share_count_m", "latest_share_count_m", "denominator_count_m", "period_weighted_count_m"}


def run_mi(run):
    return run.get("mi") or {}


def build_runs(cfg, log):
    runs = []
    for r in cfg["runs"]:
        S = load_summary(r["run_file"])
        lab = f"[{r['token']}] "
        seats = recompute_run(S, log, lab)
        runs.append(dict(token=r["token"], dossier=r["dossier"], k=float(r.get("k", 1.0)), j=float(r.get("j", 1.0)),
                         summary=S, seats=seats, bridge=False, mi=cfg.get("market_inputs") or {}))
    for r in cfg.get("bridge_runs", []):
        S = load_summary(r["run_file"])
        lab = f"[{r['token']} BRIDGE] "
        seats = recompute_run(S, log, lab)
        runs.append(dict(token=r["token"], dossier=r["dossier"], k=1.0, j=1.0, summary=S, seats=seats, bridge=True))
    return runs


def run_metrics(run, log, label):
    k = run["k"]
    seats, S = run["seats"], run["summary"]
    fr = S.get("frame") or {}
    m = {}
    h = headline_of(seats)
    m["headline_run_units"] = h
    m["headline"] = h * k if h is not None else None
    m["headline_reported"] = (num(S.get("headline_buy")) * k) if num(S.get("headline_buy")) is not None else None
    hu = headline_of(seats, uniform=True)
    m["headline_uniform"] = hu * k if hu is not None else None
    w = wfv_of(seats)
    m["wfv"] = w * k if w is not None else None
    m["w_base"] = wmean_field(seats, "base")
    m["w_tail"] = wmean_field(seats, "tail")
    m["w_required"] = wmean_field(seats, "required")
    m["eff_margin"] = (1 - h / w) if (h is not None and w) else None
    hs = headline_seats(seats)
    m["n_headline_seats"] = len(hs)
    m["tiers"] = [s["tier"] for s in hs]
    m["median_seat_fv"] = statistics.median([s["fv"] for s in seats if s["fv"] is not None
                                            and not (v8() and s["irr"])]) * k
    fl = num((S.get("helena_floor") or {}).get("floor_per_share_or_null"))
    m["helena_floor"] = fl * k if fl is not None else None
    # elasticity
    for d, key in ((-0.05, "bp_dn"), (0.05, "bp_up")):
        cs, at_min = cf_breakp(seats, d)
        hh = headline_of(cs)
        m[key] = hh * k if hh is not None else None
        if d < 0:
            m["bp_at_min"] = at_min
    for which, key in ((1, "conv_vdate"), (2, "conv_sdate"), (3, "conv_both")):
        cs, dt, ratio = cf_convention(seats, fr, which, log if which == 1 else [], label)
        hh = headline_of(cs)
        m[key] = hh * k if hh is not None else None
        m["dt_years"], m["count_ratio"] = dt, ratio
    if v71():
        cs, m["denom_alt_ratio"] = cf_denominator(seats, fr, log, label)
        hh = headline_of(cs)
        m["conv_denom"] = hh * k if hh is not None else None
        for tgt, key in (("organic", "acq_org"), ("including_acquisitions", "acq_inc")):
            cs, miss = cf_acquisitions(seats, tgt, log, label, fr)
            hh = headline_of(cs)
            m[key] = hh * k if hh is not None else None
            m[key + "_missing"] = miss
        m["acq_mismatch"] = acq_mismatches(seats, fr)
        m["at_cap"] = sum(1 for s in headline_seats(seats) if s.get("at_cap"))
        fr_raw = S.get("frame") or {}
        den, ps = denominator_count(fr_raw), num(fr_raw.get("per_share_count_m"))
        m["denom_ratio"] = (den / ps) if (den and ps) else None
        m["denom_normalised"] = bool(den and ps and abs(den / ps - 1) > DENOM_TOL)
    if v8():   # G3: margin-rule alternatives on the same seats and trees (never averaged into the headline)
        hs_ = headline_seats(seats)
        for key, _name in LINES_ALL:
            hh = headline_of(seats, buy_key=key)
            m["line_" + key] = hh * k if hh is not None else None
        m["n_tuned_missing"] = sum(1 for s_ in hs_ if s_.get("buy_victor") is None)
        if m["n_tuned_missing"]:
            log.append(f"{label}{m['n_tuned_missing']} headline seat(s) without a valid tree: left out of the tuned "
                       f"Victor and tuned Max lines, weight dropped")
        m["near_cut"] = sum(1 for s_ in hs_ if s_.get("near_cut"))
        m["w_base_step"] = wmean_field(seats, "base_step")
    if v9():   # N2 alternative-denominator row; N6 modal tier is a tier name
        cs, m["alt_denom_missing"] = cf_altdenom(seats, log, label)
        hh = headline_of(cs)
        m["alt_denom"] = hh * k if hh is not None else None
        m["alt_check"] = alt_denom_checks(seats, S.get("frame"), log, label)
        modal = S.get("quality_tier_modal")
        if norm_tier(modal) is None or str(modal).strip() not in TIERS:
            log.append(f"{label}C8 quality_tier_modal is not a tier name: {str(modal)[:80]!r}")
    if v10():   # T2 debt row; T1-T4 checks; T6 monitor fields (descriptive)
        cs, m["debt_measured"] = cf_debt(seats, fr, log, label)
        hh = headline_of(cs)
        m["debt"] = hh * k if hh is not None else None
        m["v10"] = v10_checks(S, seats, run_mi(run), log, label)
        m["monitor"] = dict(
            off_base=m["v10"]["off_base"], terminal_growth=wmean_field(seats, "tg"), forecast_growth=wmean_field(seats, "fg"),
            quality_score=wmean_field(seats, "score"), break_p=wmean_field(seats, "p"), tail=wmean_field(seats, "tail"),
            walter_multiplier=m["v10"]["walter_multiplier"], walter_score=m["v10"]["walter_score"],
            debt_deducted=m["v10"]["debt_deducted"], risk_class=m["v10"]["risk_class"],
            mappings=seat_mapping_row(S),
            register=m["v10"]["register"], debt_change=(m["debt"] - m["headline"]) if (m["debt_measured"] and m["debt"] is not None
                                                                                   and m["headline"] is not None) else None)
    cs = cf_rate(seats, log, label)
    hh = headline_of(cs)
    m["rf50"] = hh * k if hh is not None else None
    rep50 = num(S.get("headline_buy_rf_plus_50bp"))
    if rep50 is not None and hh is not None and abs(rep50 - hh) > 0.05:
        log.append(f"{label}headline_buy_rf_plus_50bp reported {rep50} vs script {hh:.4f} (run units)")
    vs, M = v6_bridge_run(S, seats, log, label)
    hv = headline_of(vs)
    m["v6_bridge"] = hv * k if hv is not None else None
    m["v6_M"] = M * k if M is not None else None
    m["v6_seats"] = [dict(investor=s["name"], asym=s.get("v6_asym"), required=s.get("v6_required"),
                          no_buy=s["no_buy"]) for s in vs]
    return m


def seat_rows(run):
    k = run["k"]
    rows = []
    for s in run["seats"]:
        r = dict(investor=s["name"], irr=s["irr"], fv=s["fv"] * k if s["fv"] is not None else None, score=s["score"],
                 tier=s["tier"], base=s["base"], p=s["p"], L=s["L"], tail=s["tail"], required=s["required"],
                 no_buy=s["no_buy"], buy=s["buy"] * k if s.get("buy") is not None else None, w=s["w"],
                 tree_ok=s["tree_ok"], rate=s["rate"])
        if s["irr"]:
            r["entry"] = s["entry"] * k if s.get("entry") is not None else None
        if v8():
            r.update(base_step=s.get("base_step"), near_cut=s.get("near_cut"), break_horizon_years=s.get("horizon"),
                     **{key: (s[key] * k if s.get(key) is not None else None) for key, _n in LINES_ALL})
            fc = s.get("forecast")
            if isinstance(fc, list):   # back-scaled: company totals / j, per-share figures x k (Stage 1c)
                j = run["j"]
                r["forecast_5y"] = [dict(period_end=x.get("period_end"), months=num(x.get("months")),
                                         cash_flow_total=(num(x.get("cash_flow_total")) / j
                                                          if num(x.get("cash_flow_total")) is not None else None),
                                         cash_flow_per_share=(num(x.get("cash_flow_per_share")) * k
                                                              if num(x.get("cash_flow_per_share")) is not None else None))
                                    for x in fc if isinstance(x, dict)]
                r["forecast_definition"] = s.get("forecast_def")
        if s["tree_ok"] and s["fv"]:
            fv = s["fv"]
            ev = sum(b["p"] * b["value"] for b in s["tree_f"])
            brk = sum(b["p"] * (fv - b["value"]) for b in s["tree_f"] if b["branch"].lower() == "break") / fv
            dn = sum(b["p"] * (fv - b["value"]) for b in s["tree_f"]
                     if b["branch"].lower() != "break" and b["value"] < fv) / fv
            up = sum(b["p"] * (b["value"] - fv) for b in s["tree_f"] if b["value"] > fv) / fv
            r.update(tail_cost=1 - ev / fv, tc_break=brk, tc_down=dn, tc_up=up)
        rows.append(r)
    return rows


def frame_value(run, field):
    fr = run["summary"].get("frame") or {}
    k, j = run["k"], run["j"]
    v = fr.get(field)
    if field in PS_FIELDS:
        x = num(v)
        return x * k if x is not None else None
    if field in SH_FIELDS:
        x = num(v)
        return x / (k * j) if x is not None else None
    if field in ("risk_free", "erp", "macro_base"):
        return num(v)
    return v


def stage3(cfg, out_dir):
    log = []
    runs = build_runs(cfg, log)
    masked = [r for r in runs if not r["bridge"]]
    bridges = [r for r in runs if r["bridge"]]
    for r in runs:
        r["m"] = run_metrics(r, log, f"[{r['token']}{' BRIDGE' if r['bridge'] else ''}] ")
        r["rows"] = seat_rows(r)
    H = [r["m"]["headline"] for r in masked]
    D = [r["dossier"] for r in masked]
    N, nd = len(H), len(set(D))
    res = dict(ticker=cfg["ticker"], unit=cfg["unit"], as_of=cfg["as_of"], N=N, D=nd, log=log, spec=SPEC)
    res["runs"] = [dict(token=r["token"], dossier=r["dossier"], ln_k=math.log(r["k"]), ln_j=math.log(r["j"]),
                        **{k: v for k, v in r["m"].items() if k not in ("v6_seats", "v10", "monitor")}) for r in masked]
    res["bridge"] = [dict(token=r["token"], dossier=r["dossier"], **{k: v for k, v in r["m"].items() if k != "v6_seats"})
                     for r in bridges]
    res["seats"] = {r["token"]: r["rows"] for r in runs}
    res["v6_seats"] = {r["token"]: r["m"]["v6_seats"] for r in runs}
    # basic
    res["basic"] = dict(min=min(H), max=max(H), median=statistics.median(H), mean=mean(H), sd=sd(H),
                        cov=(sd(H) / mean(H)) if mean(H) else None)
    res["basic_uniform"] = dict(mean=mean([r["m"]["headline_uniform"] for r in masked]))
    tiers_all = [t for r in masked for t in r["m"]["tiers"]]
    res["tiers"] = {t: tiers_all.count(t) for t in TIERS}
    res["irr"] = [dict(token=r["token"], investor=s["investor"], entry=s.get("entry"), fv=s["fv"],
                       ref=(s["buy"] if s["buy"] is not None else None))
                  for r in masked for s in r["rows"] if s["irr"]]
    # run noise
    s_w, df = pooled_sd(H, D)
    res["s_w"], res["df"] = s_w, df
    res["s_w_ci90"] = chi2_interval(s_w, df) if s_w and df > 0 else None
    lnH = [math.log(h) for h in H]
    lnF = [math.log(r["m"]["wfv"]) for r in masked]
    lnM = [a - b for a, b in zip(lnH, lnF)]
    sH, _ = pooled_sd(lnH, D)
    sF, _ = pooled_sd(lnF, D)
    sM, _ = pooled_sd(lnM, D)
    cFM = pooled_cov(lnF, lnM, D)
    vH = sH ** 2 if sH else None
    res["log_noise"] = dict(s_lnH=sH, s_lnFV=sF, s_lnMargin=sM, cov=cFM,
                            share_fv=(sF ** 2 / vH) if vH else None, share_margin=(sM ** 2 / vH) if vH else None,
                            share_cov=(2 * cFM / vH) if vH else None)
    sFV_lvl, _ = pooled_sd([r["m"]["wfv"] for r in masked], D)
    res["fv_noise_frac"] = sFV_lvl / mean([r["m"]["wfv"] for r in masked]) if sFV_lvl else None
    res["buy_noise_frac"] = s_w / mean(H) if s_w else None
    # drift floor
    pairs = []
    for d in sorted(set(D)):
        idx = [i for i, x in enumerate(D) if x == d]
        for a, b in itertools.combinations(idx, 2):
            pairs.append(dict(dossier=d, a=masked[a]["token"], b=masked[b]["token"], gap=abs(H[a] - H[b])))
            ga, gb = masked[a]["m"], masked[b]["m"]
            g = math.log(ga["headline"] / gb["headline"])
            f = math.log(ga["wfv"] / gb["wfv"])
            da = frame_value(masked[a], "declared_denominator_per_share")
            db = frame_value(masked[b], "declared_denominator_per_share")
            dpart = math.log(da / db) if (da and db and da > 0 and db > 0) else None
            pairs[-1].update(ln_gap=g, ln_fv=f, ln_margin=g - f, fv_share=(f / g) if abs(g) > 1e-12 else None,
                             ln_denominator=dpart, ln_multiple=(f - dpart) if dpart is not None else None)
    res["pairs"] = pairs
    res["drift_floor"] = mean([p["gap"] for p in pairs])
    res["contrast"] = contrast(H, D, s_w, df)
    # frame decomposition
    fields = []
    for r in masked:
        for kf in (r["summary"].get("frame") or {}).keys():
            if kf not in fields and kf not in ("weights", "denominator_adjustments"):
                fields.append(kf)
    cat, cont = {}, {}
    for f in fields:
        vals = [frame_value(r, f) for r in masked]
        isnum = f in PS_FIELDS or f in SH_FIELDS or f in ("risk_free", "erp", "macro_base")
        if isnum:
            cont[f] = dict(values={r["token"]: v for r, v in zip(masked, vals)}, rho=spearman(vals, H))
        else:
            tab = {}
            for r, v in zip(masked, vals):
                key = json.dumps(v, ensure_ascii=False) if not isinstance(v, str) else v
                tab.setdefault(key, []).append(r)
            cat[f] = {key: dict(runs=[x["token"] for x in rs], mean_headline=mean([x["m"]["headline"] for x in rs]))
                      for key, rs in tab.items()}
    for extra in ("floor_type",):
        tab = {}
        for r in masked:
            v = str((r["summary"].get("helena_floor") or {}).get(extra))
            tab.setdefault(v, []).append(r)
        cat["helena_floor." + extra] = {key: dict(runs=[x["token"] for x in rs],
                                                  mean_headline=mean([x["m"]["headline"] for x in rs]))
                                        for key, rs in tab.items()}
    sumadj = []
    for r in masked:
        adj = (r["summary"].get("frame") or {}).get("denominator_adjustments") or []
        sumadj.append(sum((num(a.get("per_share")) or 0.0) for a in adj if isinstance(a, dict)) * r["k"])
    derived = {"sum_adjustments_per_share": sumadj,
               "median_seat_fv": [r["m"]["median_seat_fv"] for r in masked],
               "helena_floor_per_share": [r["m"]["helena_floor"] for r in masked],
               "weighted_mean_tail_term": [r["m"]["w_tail"] for r in masked],
               "weighted_fv": [r["m"]["wfv"] for r in masked]}
    for f, vals in derived.items():
        cont[f] = dict(values={r["token"]: v for r, v in zip(masked, vals)}, rho=spearman(vals, H))
    for inv in committee():
        vals = [weights_of(r["summary"]).get(inv) for r in masked]
        cont["weights." + inv] = dict(values={r["token"]: v for r, v in zip(masked, vals)}, rho=spearman(vals, H))
    res["frame_categorical"], res["frame_continuous"] = cat, cont
    # adjustment ledger
    led = {}
    for r in masked:
        for a in (r["summary"].get("frame") or {}).get("denominator_adjustments") or []:
            if not isinstance(a, dict):
                continue
            item = str(a.get("item", "")).strip()
            v = num(a.get("per_share"))
            key = re.sub(r"\s+", " ", item.lower())
            e = led.setdefault(key, dict(item=item, cls=classify_adj(item), runs=[], vals=[]))
            e["runs"].append(r["token"])
            e["vals"].append(v * r["k"] if v is not None else None)
    res["adj_ledger"] = [dict(item=e["item"], cls=e["cls"], n_runs=len(set(e["runs"])), runs=e["runs"],
                              mean=mean(e["vals"]), min=min([v for v in e["vals"] if v is not None], default=None),
                              max=max([v for v in e["vals"] if v is not None], default=None))
                         for e in led.values()]
    cls_runs = {}
    for r in masked:
        for a in (r["summary"].get("frame") or {}).get("denominator_adjustments") or []:
            if isinstance(a, dict):
                cls_runs.setdefault(classify_adj(a.get("item", "")), set()).add(r["token"])
    res["adj_classes"] = {c: sorted(v) for c, v in cls_runs.items()}
    res["gross_vs_declared"] = [dict(token=r["token"], gross=frame_value(r, "gross_denominator_per_share"),
                                     declared=frame_value(r, "declared_denominator_per_share")) for r in masked]
    # elasticity, convention, rate, bridge (blind)
    def point_of(key):
        return trimmed_point([r["m"][key] for r in masked])[0]
    P0 = trimmed_point(H)[0]
    res["blind_point"] = P0
    res["blind_rows"] = {}
    rowkeys = [("bp_dn", ROW_BP_DN), ("bp_up", ROW_BP_UP), ("conv_vdate", ROW_VDATE),
               ("conv_sdate", ROW_SDATE), ("conv_both", ROW_BOTH), ("rf50", ROW_RF),
               ("v6_bridge", "v6-rule bridge (own trees, no inheritance)")]
    if v71():
        rowkeys[5:5] = [("conv_denom", ROW_DENOM), ("acq_org", ROW_ACQ_ORG), ("acq_inc", ROW_ACQ_INC)]
        if v9():
            rowkeys.insert(rowkeys.index(("acq_inc", ROW_ACQ_INC)) + 1, ("alt_denom", ROW_ALTDEN))
            res["v9"] = dict(alt_denom_missing={r["token"]: r["m"]["alt_denom_missing"] for r in masked},
                             alt={r["token"]: dict(r["m"]["alt_check"], headline=r["m"]["alt_denom"]) for r in masked},
                             zero_acq_spend={r["token"]: zero_acq_spend(r["summary"].get("frame")) for r in masked})
        if v10():
            rowkeys.insert(rowkeys.index(("alt_denom", ROW_ALTDEN)) + 1, ("debt", ROW_DEBT))
        res["v71"] = dict(
            denom={r["token"]: dict(ratio=r["m"]["denom_ratio"], normalised=r["m"]["denom_normalised"],
                                    alt_ratio=r["m"]["denom_alt_ratio"]) for r in masked},
            acq_mismatch={r["token"]: dict(organic_with_deduction=r["m"]["acq_mismatch"][0],
                                           including_without_deduction=r["m"]["acq_mismatch"][1],
                                           undeclared=r["m"]["acq_mismatch"][2]) for r in masked},
            acq_rows_missing={r["token"]: dict(organic=r["m"]["acq_org_missing"], including=r["m"]["acq_inc_missing"])
                              for r in masked},
            at_cap={r["token"]: r["m"]["at_cap"] for r in masked},
            recent_acquisitions={r["token"]: (r["summary"].get("frame") or {}).get("recent_acquisitions") for r in masked})
    for key, name in rowkeys:
        pv = point_of(key)
        res["blind_rows"][name] = dict(point=pv, change=pv - P0, change_sw=(pv - P0) / s_w if s_w else None,
                                       per_run={r["token"]: r["m"][key] for r in masked})
    if v8():
        lines3 = {}
        for key, name in LINES_ALL:
            vals = [r["m"]["line_" + key] for r in masked]
            pt = line_point(vals)
            if any(v is None for v in vals):
                log.append(f"margin-rule line '{name}': run(s) with no eligible seat left out of its trimmed point "
                           f"({sum(v is None for v in vals)} of {len(vals)})")
            lines3[name] = dict(point=pt, change=(pt - P0) if pt is not None else None,
                                per_run={r["token"]: r["m"]["line_" + key] for r in masked})
        res["v8"] = dict(
            lines=lines3,
            near_cut={r["token"]: r["m"]["near_cut"] for r in masked},
            near_cut_total=sum(r["m"]["near_cut"] for r in masked),
            tuned_missing={r["token"]: r["m"]["n_tuned_missing"] for r in masked},
            premium_vs_step={r["token"]: dict(premium=r["m"]["w_base"], step=r["m"]["w_base_step"]) for r in masked},
            constants=dict(premium_points=PREMIUM_POINTS, tuned_k=TUNED_K, tuned_c=TUNED_C))
    if v10():   # T6 channel monitor (descriptive), per run and over the runs the blind point retains
        keep3 = trimmed_point(H)[1]
        per = {r["token"]: r["m"]["monitor"] for r in masked}
        kept = [masked[i]["m"]["monitor"] for i in keep3]

        def avg(key):
            vals = [x[key] for x in kept if x.get(key) is not None]
            return mean(vals) if vals else None
        chan = {}
        for x in kept:
            for ch, v in (x["register"].get("by_channel") or {}).items():
                c = chan.setdefault(ch, dict(n=0, size=0.0, buy_effect=0.0))
                c["n"] += v["n"]
                c["size"] += v["size"]
                c["buy_effect"] += v.get("buy_effect", 0.0)
        res["v10"] = dict(
            per_run=per, retained=[masked[i]["token"] for i in keep3],
            committee=dict(off_base=sum(x["off_base"] for x in kept), terminal_growth=avg("terminal_growth"),
                           forecast_growth=avg("forecast_growth"), quality_score=avg("quality_score"),
                           break_p=avg("break_p"), tail=avg("tail"), walter_multiplier=avg("walter_multiplier"),
                           walter_score=avg("walter_score"), debt_change=avg("debt_change"),
                           debt_deducted=sum(1 for x in kept if x["debt_deducted"]),
                           risk_class={c: sum(1 for x in kept if x["risk_class"] == c) for c in RISK_CLASSES},
                           register_by_channel=chan,
                           register_issues=sum(x["register"]["issues"] for x in kept)),
            checks={r["token"]: dict(issues=r["m"]["v10"]["issues"], off_seats=r["m"]["v10"]["off_seats"])
                    for r in masked},
            debt_measured={r["token"]: r["m"]["debt_measured"] for r in masked})
    res["bp_at_min_total"] = sum(r["m"]["bp_at_min"] for r in masked)
    res["bp_headline_seats_total"] = sum(r["m"]["n_headline_seats"] for r in masked)
    bps = [s["p"] for r in masked for s in headline_seats(r["seats"]) if s["p"] is not None]
    res["bp_hist"] = dict(n=len(bps), share_at_010=sum(1 for p in bps if abs(p - 0.10) < 1e-9) / len(bps) if bps else None,
                          share_near_005_multiple=sum(1 for p in bps if abs(p - 0.05 * round(p / 0.05)) <= 0.01 + 1e-9) / len(bps) if bps else None,
                          values=sorted(bps))
    # induced-field check
    mi = cfg.get("market_inputs", {})
    meth = cfg.get("methodology_note_fields", [])
    induced = {}
    allfields = fields + ["helena_floor.floor_type"] + ["weights." + c for c in committee()]
    for f in allfields:
        if f.startswith("weights."):
            vals = [weights_of(r["summary"]).get(f.split(".", 1)[1]) for r in masked]
        elif f == "helena_floor.floor_type":
            vals = [str((r["summary"].get("helena_floor") or {}).get("floor_type")) for r in masked]
        else:
            vals = [frame_value(r, f) for r in masked]
        if all(isinstance(v, (int, float)) and v is not None for v in vals):
            agree = max(vals) - min(vals) <= 1e-4 * max(1.0, abs(max(vals)))
            if f in SH_FIELDS:
                agree = max(vals) - min(vals) <= 2e-3 * max(1.0, abs(max(vals)))
        else:
            agree = len({json.dumps(v, sort_keys=True, ensure_ascii=False) if not isinstance(v, str) else v.strip().lower()
                         for v in vals}) == 1
        if not agree:
            continue
        v0 = vals[0]
        label, src = "UNANIMOUS", None
        if f == "risk_free" and num(mi.get("risk_free")) is not None and abs(num(v0) - num(mi["risk_free"])) < 1e-9:
            label, src = "INDUCED", "MARKET_INPUTS"
        if f == "erp" and num(mi.get("erp")) is not None and abs(num(v0) - num(mi["erp"])) < 1e-9:
            label, src = "INDUCED", "MARKET_INPUTS"
        if f == "macro_base" and num(mi.get("risk_free")) is not None and num(mi.get("erp")) is not None and \
                abs(num(v0) - (num(mi["risk_free"]) + num(mi["erp"]))) < 1e-6:
            label, src = "INDUCED", "MARKET_INPUTS (risk-free + ERP)"
        if f == "market_inputs_as_of" and str(v0)[:10] == str(cfg.get("as_of")):
            label, src = "INDUCED", "MARKET_INPUTS (its AS_OF)"
        if v71() and f in ("per_share_count_m", "per_share_count_date"):
            label, src = "INDUCED", "Appendix B share-count rule (F1)"
        if v71() and f == "acq_spend_window":
            yrs = re.search(r"(\d+(?:\.\d+)?)\s*(?:years?|yrs?)\b", str(v0), re.I)
            if yrs and float(yrs.group(1)) <= 5 + 1e-9:
                label, src = "INDUCED", "Appendix B acquisition rule (F4)"
        if v9() and f == "alternative_denominator_type" and all(
                str((r["summary"].get("frame") or {}).get("alternative_denominator_type", "")).strip().lower() ==
                str((r["summary"].get("frame") or {}).get("denominator_type", "")).strip().lower() for r in masked):
            label, src = "INDUCED", "Appendix B alternative-denominator rule (N2: the declared definition)"
        if f == "guidance_stance" and str(v0).strip().lower() == "skeptical":
            label, src = "INDUCED", "FRAMEWORK Overview default"
        for mf in meth:
            if mf.get("field") == f and str(mf.get("value")).strip().lower() == str(v0).strip().lower():
                label, src = "INDUCED", "the pack (Stage-1 methodology-note log)"
        induced[f] = dict(value=v0, label=label, source=src)
    if v71():
        all_matched = all(sum(acq_mismatches(r["seats"], r["summary"].get("frame"))) == 0 for r in masked)
        induced["every seat's growth_basis and acq_spend_deducted matched"] = dict(
            value=all_matched, label=("INDUCED" if all_matched else "VARIES"),
            source=("Appendix B acquisition rule (F4)" if all_matched else None))
        res["v71"]["period_count_runs"] = [r["token"] for r in masked
                                           if str((r["summary"].get("frame") or {}).get("per_share_count_basis", "")).lower() == "period"]
        dc_eq = []
        for r in masked:
            fr_ = r["summary"].get("frame") or {}
            a_, b_ = denominator_count(fr_), num(fr_.get("per_share_count_m"))
            dc_eq.append(bool(a_ and b_ and abs(a_ / b_ - 1) <= DENOM_TOL))
        induced["denominator_count_m = per_share_count_m"] = dict(
            value=all(dc_eq), runs_equal=sum(dc_eq), label=("INDUCED" if all(dc_eq) else "VARIES"),
            source=("Appendix B share-count rule (F1)" if all(dc_eq) else None))
    vd_eq = [str((r["summary"].get("frame") or {}).get("valuation_date"))[:10] ==
             str((r["summary"].get("frame") or {}).get("pack_as_of_date"))[:10] for r in masked]
    induced["valuation_date = pack_as_of_date"] = dict(value=all(vd_eq), runs_equal=sum(vd_eq),
                                                       label=("INDUCED" if all(vd_eq) else "VARIES"),
                                                       source=("Appendix B default" if all(vd_eq) else None))
    sbc_all = all(r["token"] in res["adj_classes"].get("SBC", []) for r in masked)
    induced["SBC adjustment in denominator_adjustments"] = dict(value=sbc_all, runs=len(res["adj_classes"].get("SBC", [])),
                                                                label=("INDUCED" if sbc_all else "VARIES"),
                                                                source=("FRAMEWORK Phase 0.A (SBC is a cost)" if sbc_all else None))
    if v10():   # T1: every seat at MARKET_INPUTS' macro base is template-induced (Appendix B rate rule)
        mbv = market_base(cfg.get("market_inputs"), None)
        on = [not off_base(s_, mbv if mbv is not None else run_macro_base(r["summary"].get("frame")))
              for r in masked for s_ in r["seats"] if not s_["irr"]]
        induced["every seat's discount_rate = macro_base and fair_value_macro_base = fair_value"] = dict(
            value=all(on), seats_on=sum(on), label=("INDUCED" if (on and all(on)) else "VARIES"),
            source=("Appendix B rate rule (v10, T1)" if (on and all(on)) else None))
    if v10():   # T2: Appendix B fixes the debt deduction at 0 and keeps lease payments in the flow
        for fld in ("debt_deducted_per_share", "lease_treatment"):
            if fld in induced:
                v0 = induced[fld]["value"]
                if fld == "lease_treatment" or (num(v0) is not None and abs(num(v0)) < 1e-12):
                    induced[fld].update(label="INDUCED", source="Appendix B debt rule (v10, T2)")
    res["induced"] = induced
    # memory control (v8 and earlier; not run in v9, which has no rescaling: N1)
    med = statistics.median(H)
    if v9():
        res["memory"], res["season_memory"] = None, None
    else:
        lnk = [math.log(r["k"]) for r in masked]
        lnj = [math.log(r["j"]) for r in masked]
        obs, p_perm, nperm = perm_test(lnH, lnk, lnj, D)
        min_per = min(D.count(d) for d in set(D))
        probe = cfg.get("probe", {})
        identified = any(str(v.get("result", "")).upper() == "IDENTIFIED" for v in probe.values())
        flag = None
        if min_per >= 4 and p_perm is not None and p_perm <= 0.02 + 1e-12:
            flag = "PRICE-MEMORY SUSPECTED" if identified else "SCALE-DEPENDENCE (possible price memory)"
        res["memory"] = dict(beta_k=obs["beta_k"], beta_j=obs["beta_j"], ci_k=obs.get("ci_k"), ci_j=obs.get("ci_j"),
                             F=obs.get("F"), df=obs.get("df"), p_perm=p_perm, n_perm=nperm,
                             available=(min_per >= 4), flag=flag, probe=probe,
                             note=None if min_per >= 4 else "per-ticker test not available (design below 4 runs per dossier)")
        prior = cfg.get("season_prior_v7_rows", [])
        med = statistics.median(H)
        py = [r["y"] for r in prior] + [math.log(h / med) for h in H]
        pk = [r["ln_k"] for r in prior] + lnk
        pj = [r["ln_j"] for r in prior] + lnj
        if v8():   # execution-specific cells: two executions of one ticker under different versions are not merged
            pg = [f"{r['ticker']}|{r.get('version', '')}|{r['dossier']}" for r in prior] + \
                 [f"{cfg['ticker']}|{MECH_VERSION[SPEC]}|{d}" for d in D]
        else:
            pg = [f"{r['ticker']}|{r['dossier']}" for r in prior] + [f"{cfg['ticker']}|{d}" for d in D]
        pobs, pp, pn = perm_test(py, pk, pj, pg)
        sflag = None
        season_identified = identified or any(str(r.get("probe", "")).upper() == "IDENTIFIED" for r in prior)
        if pp is not None and pp <= 0.05 + 1e-12:
            sflag = "PRICE-MEMORY SUSPECTED" if season_identified else "SCALE-DEPENDENCE (possible price memory)"
        res["season_memory"] = dict(beta_k=pobs["beta_k"], beta_j=pobs["beta_j"], ci_k=pobs.get("ci_k"), ci_j=pobs.get("ci_j"),
                                    F=pobs.get("F"), p_perm=pp, n_perm=pn, n_rows=len(py), flag=sflag,
                                    tickers=sorted({g.split("|")[0] for g in pg}))
    res["log_rel_headline"] = {r["token"]: math.log(r["m"]["headline"] / med) for r in masked}
    res["median_headline"] = med
    # bridge camp means
    res["bridge_vs_camp"] = []
    for b in bridges:
        camp = [r["m"]["headline"] for r in masked if r["dossier"] == b["dossier"]]
        res["bridge_vs_camp"].append(dict(token=b["token"], dossier=b["dossier"], bridge=b["m"]["headline"],
                                          camp_mean=mean(camp), diff=b["m"]["headline"] - mean(camp)))
    os.makedirs(out_dir, exist_ok=True)
    json.dump(res, open(os.path.join(out_dir, "stage3.json"), "w"), indent=1, default=str)
    open(os.path.join(out_dir, "stage3_tables.md"), "w").write(stage3_md(res))
    return res


def stage3_md(res):
    u = res["unit"]
    L = []
    A = L.append
    v9t = res.get("spec") in ("v9", "v10")
    A(f"## Per-run headlines ({'' if v9t else 'back-scaled, '}{u})\n")
    if v9t:
        A("| run | dossier | headline (script) | reported | uniform-weight | weighted FV | effective margin | base (w) | tail (w) | headline seats |")
        A("|---|---|---|---|---|---|---|---|---|---|")
    else:
        A("| run | dossier | ln k | ln j | headline (script) | reported (back-scaled) | uniform-weight | weighted FV | effective margin | base (w) | tail (w) | headline seats |")
        A("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in res["runs"]:
        lk = "" if v9t else f"{r['ln_k']:+.4f} | {r['ln_j']:+.4f} | "
        A(f"| {r['token']} | {r['dossier']} | {lk}{fmt(r['headline'])} | {fmt(r['headline_reported'])} | "
          f"{fmt(r['headline_uniform'])} | {fmt(r['wfv'])} | {fmt(r['eff_margin'] * 100 if r['eff_margin'] is not None else None, 1)}% | "
          f"{fmt(r['w_base'] * 100 if r['w_base'] is not None else None, 1)}% | {fmt(r['w_tail'] * 100 if r['w_tail'] is not None else None, 2)}% | {r['n_headline_seats']} |")
    b = res["basic"]
    A(f"\nRange {fmt(b['min'])}–{fmt(b['max'])}; median {fmt(b['median'])}; mean {fmt(b['mean'])}; SD {fmt(b['sd'])}; "
      f"CoV {fmt(b['cov'] * 100 if b['cov'] else None, 1)}%. Uniform-weight mean {fmt(res['basic_uniform']['mean'])}.")
    A(f"\nTier distribution (headline seats, {sum(res['tiers'].values())}): " +
      "; ".join(f"{t} {n}" for t, n in res["tiers"].items()) + ".")
    if v9t and (res.get("v9") or {}).get("alt"):
        A("\n## Alternative denominator by run (v9, N2; descriptive)\n")
        A("| run | basis | alternative ÷ declared | direction | seats valued | headline on the alternative | change |")
        A("|---|---|---|---|---|---|---|")
        hd = {r["token"]: r["headline"] for r in res["runs"]}
        for t, a in res["v9"]["alt"].items():
            ch = (a["headline"] - hd[t]) if (a.get("headline") is not None and hd.get(t) is not None) else None
            A(f"| {t} | {a.get('basis')} | {fmt(a.get('ratio'), 4)} | {a.get('direction')} | {a.get('valued')} of {a.get('n')} | "
              f"{fmt(a.get('headline'))} | {fmt(ch)} |")
    if res.get("v10"):
        v = res["v10"]
        A("\n## Channel monitor (v10, T6; descriptive, moves no number)\n")
        A("| run | seats off the macro base | terminal growth (w, %) | 5-year forecast growth (w, %) | quality score (w) | break_p (w) | "
          "tail term (w) | Walter multiplier | debt deducted | risk class | register entries / issues | debt row change |")
        A("|---|---|---|---|---|---|---|---|---|---|---|---|")
        for t, x in v["per_run"].items():
            A(f"| {t} | {x['off_base']} | {fmt(x['terminal_growth'])} | {fmt(x['forecast_growth'])} | {fmt(x['quality_score'], 1)} | "
              f"{fmt(x['break_p'], 3)} | {fmt(x['tail'], 4)} | {fmt(x['walter_multiplier'], 3)} | {'yes' if x['debt_deducted'] else 'no'} | "
              f"{x['risk_class'] or 'n/a'} | {x['register']['n']} / {x['register']['issues']} | {sfmt(x['debt_change'])} |")
        c = v["committee"]
        A(f"\nOver the runs the blind point retains ({', '.join(v['retained'])}): seats off the macro base {c['off_base']}; "
          f"terminal growth {fmt(c['terminal_growth'])}%; 5-year forecast growth {fmt(c['forecast_growth'])}%; quality score "
          f"{fmt(c['quality_score'], 1)}; break_p {fmt(c['break_p'], 3)}; tail term {fmt(c['tail'], 4)}; Walter's multiplier "
          f"{fmt(c['walter_multiplier'], 3)} (score {fmt(c['walter_score'], 2)}); mean per-run debt-row change {sfmt(c['debt_change'])}; "
          + f"runs with debt deducted {c['debt_deducted']}; risk class "
          + ", ".join(f"{b} {n}" for b, n in c["risk_class"].items()) + "; register by channel "
          + (", ".join(f"{ch} {x['n']} (Σ size {x['size']:.4g}; BUY effect {x['buy_effect']:+.2f})" for ch, x in c["register_by_channel"].items()) or "none")
          + f"; register issues {c['register_issues']}.")
        A("\n## Seat mappings (v10, T4)\n")
        A("| run | Walter: " + " / ".join(GRADE_COMPONENTS) + " | gates (" + " / ".join(GATE_COMPONENT) + ") | score | multiplier | NO BUY | Alexander score | adjustment |")
        A("|---|---|---|---|---|---|---|---|")
        for t, x in v["per_run"].items():
            w_, a_ = (x.get("mappings") or {}).get("walter") or {}, (x.get("mappings") or {}).get("alexander") or {}
            A(f"| {t} | {' / '.join(str(c) for c in w_.get('components', [])) or 'n/a'} | "
              f"{' / '.join(str(g) for g in w_.get('gates', [])) or 'n/a'} | {w_.get('score', 'n/a')} | "
              f"{fmt(w_.get('multiplier'), 3)} | {w_.get('no_buy', 'n/a')} | {a_.get('score', 'n/a')} | {a_.get('adjustment', 'n/a')} |")
    A("\n## Run noise\n")
    ci = res["s_w_ci90"]
    A(f"s_w = {fmt(res['s_w'], 4)} {u}, df = {res['df']}; 90% χ² interval for σ_w: {fmt(ci[0], 4)} to {fmt(ci[1], 4)}.")
    ln = res["log_noise"]
    A(f"\nLog scale: s(ln headline) = {fmt(ln['s_lnH'], 5)}; s(ln weighted FV) = {fmt(ln['s_lnFV'], 5)}; "
      f"s(ln headline ÷ weighted FV) = {fmt(ln['s_lnMargin'], 5)}. Share of within-dossier log variance: fair value "
      f"{fmt(ln['share_fv'] * 100 if ln['share_fv'] is not None else None, 1)}%, margin {fmt(ln['share_margin'] * 100 if ln['share_margin'] is not None else None, 1)}%, "
      f"covariance {fmt(ln['share_cov'] * 100 if ln['share_cov'] is not None else None, 1)}%.")
    A(f"\nDrift floor (display only): {fmt(res['drift_floor'], 4)} {u} (mean absolute same-dossier pairwise gap).\n")
    A("| dossier | pair | gap | ln gap | FV share | ln denominator | ln multiple | ln margin |")
    A("|---|---|---|---|---|---|---|---|")
    for p in res["pairs"]:
        A(f"| {p['dossier']} | {p['a']}–{p['b']} | {fmt(p['gap'])} | {p['ln_gap']:+.4f} | "
          f"{fmt(p['fv_share'] * 100 if p['fv_share'] is not None else None, 0)}% | "
          f"{('%+.4f' % p['ln_denominator']) if p['ln_denominator'] is not None else 'n/a'} | "
          f"{('%+.4f' % p['ln_multiple']) if p['ln_multiple'] is not None else 'n/a'} | {p['ln_margin']:+.4f} |")
    if res.get("v8"):
        v = res["v8"]
        A("\n## Margin-rule alternatives (v8; policy, not in the interval; never averaged)\n")
        A("| run | headline (quality premium) | " + " | ".join(n for _k, n in LINES_ALL) + " | premium (w) | step base (w) | seats within 3 points of a cut-off |")
        A("|---|---|" + "---|" * len(LINES_ALL) + "---|---|---|")
        for r in res["runs"]:
            t = r["token"]
            A(f"| {t} | {fmt(r['headline'])} | " + " | ".join(fmt(v['lines'][n]['per_run'][t]) for _k, n in LINES_ALL) +
              f" | {fmt(v['premium_vs_step'][t]['premium'] * 100 if v['premium_vs_step'][t]['premium'] is not None else None, 1)}% | "
              f"{fmt(v['premium_vs_step'][t]['step'] * 100 if v['premium_vs_step'][t]['step'] is not None else None, 1)}% | {v['near_cut'][t]} |")
        A("\nTrimmed points (blind): " + "; ".join(f"{n} {fmt(x['point'])} ({sfmt(x['change'])} against the blind intermediate)"
                                                  for n, x in v["lines"].items()) + ".")
    c = res["contrast"]
    if c:
        A(f"\n**Dossier contrast.** t = {c['t']:+.4f}, df = {c['df']}, two-sided p = {c['p']:.4f}; camp means " +
          "; ".join(f"{k} {fmt(v)} (n={c['n'][k]})" for k, v in c["camp_means"].items()) +
          ". With two dossiers the between-dossier variance has 1 df and is not estimated.")
    return "\n".join(L) + "\n"


# ----------------------------------------------------------------------------- stage 5
def stage5(cfg, out_dir):
    s3 = json.load(open(os.path.join(out_dir, "stage3.json")))
    if s3.get("spec", SPEC) != SPEC:
        raise SystemExit(f"stage3.json was computed under spec {s3.get('spec')}, not {SPEC}: re-run Stage 3 in the same mode")
    log = []
    runs = build_runs(dict(cfg, bridge_runs=[]), [])
    folds = {}
    for r in runs:
        vpath = cfg.get("verifications", {}).get(r["token"])
        ver = load_verification(vpath) if vpath else {"rulings": []}
        fo = fold_run(r["summary"], ver, log, f"[{r['token']}] ")
        folds[r["token"]] = fo
        r["adj_summary"] = fo["summary"]
        r["adj_seats"] = recompute_run(fo["summary"], [], "")
    toks = [r["token"] for r in runs]
    D = [r["dossier"] for r in runs]
    blind = [folds[t]["blind"] * r["k"] for t, r in zip(toks, runs)]
    adj = [folds[t]["adjusted"] * r["k"] for t, r in zip(toks, runs)]
    N, nd = len(adj), len(set(D))
    P_blind, keep_b = trimmed_point(blind)
    P, keep = trimmed_point(adj)
    s_b, df = pooled_sd(blind, D)
    s, _ = pooled_sd(adj, D)
    tc = tq(0.90, df)
    hw_b, hw = tc * s_b / math.sqrt(N), tc * s / math.sqrt(N)
    wfv_adj = [wfv_of(r["adj_seats"]) * r["k"] for r in runs]
    wfv_bl = [wfv_of(r["seats"]) * r["k"] for r in runs]
    FV = mean([wfv_adj[i] for i in keep])
    FV_b = mean([wfv_bl[i] for i in keep_b])
    res = dict(ticker=cfg["ticker"], unit=cfg["unit"], as_of=cfg["as_of"], N=N, D=nd, df=df, t90=tc, spec=SPEC,
               blind_point=P_blind, blind_hw=hw_b, blind_s=s_b, blind_fv=FV_b,
               point=P, hw=hw, s=s, fv=FV, ci=(P - hw, P + hw), rep=(P - math.sqrt(2) * hw, P + math.sqrt(2) * hw),
               blind_ci=(P_blind - hw_b, P_blind + hw_b), retained=[toks[i] for i in keep],
               retained_blind=[toks[i] for i in keep_b], log=log, label=INTERVAL_LABEL)
    res["s_ci90"] = chi2_interval(s, df)
    res["runs"] = [dict(token=t, dossier=d, k=r["k"], blind=b, adjusted=a, joint_delta=a - b, wfv_blind=fb, wfv_adj=fa,
                        mode=folds[t]["mode"], joint_reasons=folds[t]["joint_reasons"],
                        applied_findings=folds[t]["applied_findings"],
                        verifier_joint_delta=folds[t]["verifier_joint_delta"],
                        verifier_adjusted=folds[t]["verifier_adjusted"],
                        findings=[dict(f, standalone_delta_backscaled=(f["standalone_delta"] * r["k"]
                                                                       if f["standalone_delta"] is not None else None))
                                  for f in folds[t]["findings"]])
                   for t, d, r, b, a, fb, fa in zip(toks, D, runs, blind, adj, wfv_bl, wfv_adj)]
    res["equal_mean"], res["median"] = mean(adj), statistics.median(adj)
    loo = []
    for i in range(N):
        sub = adj[:i] + adj[i + 1:]
        loo.append(dict(token=toks[i], point=trimmed_point(sub)[0]))
    res["loo"] = loo
    res["most_influential_run"] = max(loo, key=lambda x: abs(x["point"] - P))["token"]
    # ledger on patched summaries
    def cf_point(fn):
        vals = []
        for r in runs:
            hh = fn(r)
            vals.append(hh * r["k"])
        return trimmed_point(vals)[0], vals
    rows = []

    def row(name, newp, extra=None):
        rows.append(dict(row=name, point=newp, change=newp - P, change_sw=(newp - P) / s if s else None,
                         extra=extra))
    bp_dn, v_dn = cf_point(lambda r: headline_of(cf_breakp(r["adj_seats"], -0.05)[0]))
    bp_up, v_up = cf_point(lambda r: headline_of(cf_breakp(r["adj_seats"], +0.05)[0]))
    row(ROW_BP_DN, bp_dn)
    row(ROW_BP_UP, bp_up)
    for which, name in ((1, ROW_VDATE), (2, ROW_SDATE), (3, ROW_BOTH)):
        pv, _ = cf_point(lambda r, w=which: headline_of(cf_convention(r["adj_seats"], r["adj_summary"].get("frame") or {}, w)[0]))
        row(name, pv)
    if v71():
        pv, _ = cf_point(lambda r: headline_of(cf_denominator(r["adj_seats"], r["adj_summary"].get("frame") or {})[0]))
        row(ROW_DENOM, pv)
        pv, _ = cf_point(lambda r: headline_of(cf_acquisitions(r["adj_seats"], "organic", None, "",
                                                               r["adj_summary"].get("frame"))[0]))
        row(ROW_ACQ_ORG, pv)
        pv, _ = cf_point(lambda r: headline_of(cf_acquisitions(r["adj_seats"], "including_acquisitions", None, "",
                                                               r["adj_summary"].get("frame"))[0]))
        row(ROW_ACQ_INC, pv)
        if v9():
            pv, va = cf_point(lambda r: headline_of(cf_altdenom(r["adj_seats"])[0]))
            mac = mean([abs(va[i] - adj[i]) for i in keep])   # over the runs retained for the BUY
            chk = [alt_denom_checks(r["adj_seats"], r["adj_summary"].get("frame")) for r in runs]
            kk = [chk[i] for i in keep]
            res["alt_card"] = dict(up=sum(1 for c in kk if c["direction"] == "up"),
                                   down=sum(1 for c in kk if c["direction"] == "down"),
                                   none=sum(1 for c in kk if c["direction"] == "none"),
                                   valued=sum(c["valued"] for c in kk), n=sum(c["n"] for c in kk),
                                   per_run={r["token"]: dict(c, headline=v_) for r, c, v_ in zip(runs, chk, va)},
                                   mean_abs_run_change=mac)
            row(ROW_ALTDEN, pv, f"mean absolute per-run change {mac:.4f}; runs above / below / none "
                                f"{res['alt_card']['up']} / {res['alt_card']['down']} / {res['alt_card']['none']} "
                                f"(retained); seats valued {res['alt_card']['valued']} of {res['alt_card']['n']}")
        if v10():
            meas = [cf_debt(r["adj_seats"], r["adj_summary"].get("frame"))[1] for r in runs]
            pv, _vd = cf_point(lambda r: headline_of(cf_debt(r["adj_seats"], r["adj_summary"].get("frame"))[0]))
            res["debt_card"] = dict(measured=sum(1 for i in keep if meas[i]),
                                    per_run={r["token"]: m_ for r, m_ in zip(runs, meas)})
            row(ROW_DEBT, pv, f"runs with net claims (retained) {res['debt_card']['measured']} of {len(keep)}; "
                              f"the v9 count, exact for the claims as reported")
    rf, _ = cf_point(lambda r: headline_of(cf_rate(r["adj_seats"])))
    row(ROW_RF, rf)
    # without most influential finding
    best = None
    for i, r in enumerate(runs):
        fo = folds[r["token"]]
        for f in fo["findings"]:
            if f["finding"] in fo["applied_findings"] and f["standalone_delta"] is not None:
                alt = adj[:]
                alt[i] = adj[i] - f["standalone_delta"] * r["k"]
                pv = trimmed_point(alt)[0]
                if best is None or abs(pv - P) > abs(best[0] - P):
                    best = (pv, r["token"], f["finding"])
    if best:
        row(ROW_INFL, best[0], extra=f"run {best[1]}, finding {best[2]}")
    else:
        row(ROW_INFL, P, extra="no folded finding")
    row(ROW_MEAN, res["equal_mean"])
    row(ROW_MEDIAN, res["median"])
    res["ledger"] = rows
    res["contrast_adj"] = contrast(adj, D, s, df)
    res["contrast_blind"] = s3.get("contrast")
    res["memory"] = s3.get("memory")
    res["season_memory"] = s3.get("season_memory")
    # card components on retained runs
    comp = dict(M=[], base=[], tail=[])
    for i in keep:
        sts = runs[i]["adj_seats"]
        h, w = headline_of(sts), wfv_of(sts)
        comp["M"].append(1 - h / w)
        comp["base"].append(wmean_field(sts, "base"))
        comp["tail"].append(wmean_field(sts, "tail"))
    res["card_M"], res["card_base"], res["card_tail"] = mean(comp["M"]), mean(comp["base"]), mean(comp["tail"])
    res["card_resid"] = res["card_M"] - res["card_base"] - res["card_tail"]
    tiers = [s_["tier"] for i in keep for s_ in headline_seats(runs[i]["adj_seats"])]
    tcount = {t: tiers.count(t) for t in TIERS}
    modal = max(TIERS, key=lambda t: (tcount[t], -TIERS.index(t)))
    res["tier_counts"], res["modal_tier"], res["n_seats"] = tcount, modal, len(tiers)
    if v8():
        def hk(seats_, key):
            h_ = headline_of(seats_, buy_key=key)
            return h_
        lines = {}
        for key, name in LINES_ALL:
            vals_a = [(hk(r["adj_seats"], key) * r["k"]) if hk(r["adj_seats"], key) is not None else None for r in runs]
            vals_b = [(hk(r["seats"], key) * r["k"]) if hk(r["seats"], key) is not None else None for r in runs]
            pa, pb = line_point(vals_a), line_point(vals_b)
            rat = [implied_ratio(runs[i]["adj_seats"], hk(runs[i]["adj_seats"], key), key) for i in keep]
            rat = [x for x in rat if x is not None]
            lines[name] = dict(point=pa, change=(pa - P) if pa is not None else None,
                               change_sw=((pa - P) / s) if (pa is not None and s) else None, blind_point=pb,
                               implied_ratio=statistics.median(rat) if (rat and pa is not None) else None,
                               per_run={t: v for t, v in zip(toks, vals_a)})
        res["lines"] = lines
        rat0 = [implied_ratio(runs[i]["adj_seats"], headline_of(runs[i]["adj_seats"])) for i in keep]
        rat0 = [x for x in rat0 if x is not None]
        res["implied_ratio_published"] = statistics.median(rat0) if rat0 else None
        res["card_near"] = sum(1 for i in keep for s_ in headline_seats(runs[i]["adj_seats"]) if s_.get("near_cut"))
        res["card_notree"] = sum(1 for i in keep for s_ in headline_seats(runs[i]["adj_seats"]) if s_.get("buy_victor") is None)
        res["ledger_seats"] = [dict(token=runs[i]["token"], investor=s_["name"], score=s_["score"], p=s_["p"],
                                    near_cut=s_.get("near_cut"), horizon=s_.get("horizon"))
                               for i in keep for s_ in headline_seats(runs[i]["adj_seats"])]
    sfv, _ = pooled_sd(wfv_adj, D)
    res["fv_noise_frac"] = sfv / mean(wfv_adj) if sfv else None
    res["buy_noise_frac"] = s / mean(adj) if s else None
    res["fv_range"] = (min(wfv_adj), max(wfv_adj))
    res["vdates"] = sorted({str((r["adj_summary"].get("frame") or {}).get("valuation_date")) for r in runs})
    res["sdates"] = sorted({str((r["adj_summary"].get("frame") or {}).get("per_share_count_date")) for r in runs})
    if v10():   # T1, T2, T4 card counts over the runs retained for the BUY
        res["card_offbase"], res["card_offbase_fold"] = 0, 0
        for i in keep:
            mbi = market_base(runs[i].get("mi"), runs[i]["summary"].get("frame"))
            blind = {s_["name"]: s_ for s_ in headline_seats(runs[i]["seats"])}
            res["card_offbase"] += sum(1 for s_ in blind.values() if off_base(s_, mbi))
            for s_ in headline_seats(runs[i]["adj_seats"]):
                b_ = blind.get(s_["name"])
                rate_off = mbi is not None and (s_.get("rate") is None or abs(s_["rate"] - mbi) > RATE_TOL + EPS)
                unpatched = b_ is not None and b_.get("fv") is not None and s_.get("fv") is not None and \
                    abs(b_["fv"] - s_["fv"]) <= 1e-9
                res["card_offbase_fold"] += bool(fv_off_base(s_) or (rate_off and unpatched))
        dd = [num((runs[i]["summary"].get("frame") or {}).get("debt_deducted_per_share")) for i in keep]
        res["card_debtded"] = sum(1 for x in dd if x is not None and abs(x) > 1e-9)
        rc = [str((runs[i]["adj_summary"].get("frame") or {}).get("systematic_risk_class") or "").strip().lower() for i in keep]
        res["card_src"] = {c: rc.count(c) for c in RISK_CLASSES}
        for i, c in zip(keep, rc):
            if c not in RISK_CLASSES:
                log.append(f"[{toks[i]}] card: risk class {c!r} not a listed value; counted in none")
        wm = [s_.get("wmult") for i in keep for s_ in runs[i]["adj_seats"]
              if s_["name"] == "walter" and not s_["irr"] and s_.get("wmult") is not None]
        res["card_wmult"] = mean(wm) if wm else None
    if v71():
        res["card_cap"] = sum(1 for i in keep for s_ in headline_seats(runs[i]["adj_seats"]) if s_.get("at_cap"))
        res["card_acq"] = sum(sum(acq_mismatches(runs[i]["adj_seats"], runs[i]["adj_summary"].get("frame"))[:2])
                              for i in keep)
        res["card_acq_undeclared"] = sum(acq_mismatches(runs[i]["adj_seats"], runs[i]["adj_summary"].get("frame"))[2]
                                         for i in keep)
        res["card_denom"] = 0
        for i in keep:
            fr_ = runs[i]["adj_summary"].get("frame") or {}
            a_, b_ = denominator_count(fr_), num(fr_.get("per_share_count_m"))
            res["card_denom"] += int(bool(a_ and b_ and abs(a_ / b_ - 1) > DENOM_TOL))
    os.makedirs(out_dir, exist_ok=True)
    card, headline = decision_card(res, s3, cfg)
    res["card"], res["headline_sentence"] = card, headline
    json.dump(res, open(os.path.join(out_dir, "stage5.json"), "w"), indent=1, default=str)
    open(os.path.join(out_dir, "decision_card.md"), "w").write(card + "\n\n" + headline + "\n")
    open(os.path.join(out_dir, "fold_log.md"), "w").write(fold_log_md(res, folds))
    open(os.path.join(out_dir, "stage5_tables.md"), "w").write(stage5_md(res))
    return res


def rnd(x, whole, how="near"):
    if x is None:
        return "n/a"
    if whole:
        v = math.floor(x) if how == "down" else math.ceil(x) if how == "up" else round(x)
        return f"{v:,.0f}"
    q = 10.0
    v = math.floor(x * q) / q if how == "down" else math.ceil(x * q) / q if how == "up" else round(x * q) / q
    return f"{v:,.1f}"


def decision_card(res, s3, cfg):
    whole = res["point"] >= 20
    P, s = res["point"], res["s"]
    led = {r["row"]: r for r in res["ledger"]}

    def lever(name):
        r = led[name]
        return f"{sfmt(r['change'])} / {sfmt(r['change_sw'])}"
    mem = res["memory"] or {}
    probe = cfg.get("probe", {})
    flag = mem.get("flag") or (res.get("season_memory") or {}).get("flag") or "NONE"
    bridge_v6 = (s3.get("blind_rows") or {}).get("v6-rule bridge (own trees, no inheritance)", {}).get("point")
    bv = "; ".join(f"{b['dossier']} {fmt(b['bridge'])}" for b in s3.get("bridge_vs_camp", [])) or "n/a"
    cand_names = [ROW_BP_DN, ROW_BP_UP, ROW_VDATE, ROW_SDATE, ROW_BOTH, ROW_RF, ROW_INFL, ROW_MEAN, ROW_MEDIAN]
    if v71():
        cand_names += [ROW_DENOM, ROW_ACQ_ORG, ROW_ACQ_INC]
    alt_card = res.get("alt_card") or {}
    if v9() and alt_card.get("valued"):   # an unmeasured row (no seat valued) is n/a and never the largest
        cand_names += [ROW_ALTDEN]
    debt_card = res.get("debt_card") or {}
    # v10 T2: the debt row restates the error v10 removes; it is never the card's largest sensitivity
    cands = [led[n] for n in cand_names]
    big = max(cands, key=lambda r: abs(r["change"]))
    ci_k, ci_j = mem.get("ci_k"), mem.get("ci_j")
    slots = {
        "TICKER": cfg["ticker"], "UNIT": cfg["unit"], "AS_OF": cfg["as_of"],
        "CARD_FV": rnd(res["fv"], whole), "CARD_FV_LO": rnd(res["fv_range"][0], whole, "down"),
        "CARD_FV_HI": rnd(res["fv_range"][1], whole, "up"),
        "CARD_M": f"{res['card_M'] * 100:.1f}%", "CARD_BASE": f"{res['card_base'] * 100:.1f}%",
        "CARD_TAIL": f"{res['card_tail'] * 100:.1f}%", "CARD_RESID": f"{res['card_resid'] * 100:+.1f}%",
        "CARD_BUY": rnd(P, whole), "CARD_LO": rnd(res["ci"][0], whole, "down"), "CARD_HI": rnd(res["ci"][1], whole, "up"),
        "CARD_REP_LO": rnd(res["rep"][0], whole, "down"), "CARD_REP_HI": rnd(res["rep"][1], whole, "up"),
        "CARD_B1": rnd(res["fv"] * (1 - 0.125), whole), "CARD_B2": rnd(res["fv"] * (1 - 0.225), whole),
        "CARD_B3": rnd(res["fv"] * (1 - 0.325), whole), "CARD_B4": rnd(res["fv"] * (1 - 0.40), whole),
        "CARD_TIER": res["modal_tier"], "CARD_TIER_N": str(res["tier_counts"][res["modal_tier"]]),
        "CARD_SEATS": str(res["n_seats"]),
        "CARD_L1": lever(ROW_BP_DN), "CARD_L2": lever(ROW_BP_UP), "CARD_L3": lever(ROW_VDATE),
        "CARD_L4": lever(ROW_SDATE), "CARD_L5": lever(ROW_BOTH), "CARD_L6": lever(ROW_RF), "CARD_L7": lever(ROW_INFL),
        "CARD_T": f"{res['contrast_adj']['t']:+.2f}" if res.get("contrast_adj") else "n/a",
        "CARD_DF": str(res["df"]),
        "CARD_SW": fmt(s), "CARD_SW_LO": fmt(res["s_ci90"][0]), "CARD_SW_HI": fmt(res["s_ci90"][1]),
        "CARD_FV_NOISE": f"{res['fv_noise_frac'] * 100:.1f}%", "CARD_BUY_NOISE": f"{res['buy_noise_frac'] * 100:.1f}%",
        "CARD_RUNS": str(res["N"]), "CARD_VDATE": ", ".join(res["vdates"]), "CARD_SDATE": ", ".join(res["sdates"]),
        "CARD_MI": f"{cfg['as_of']} {cfg.get('market_inputs', {}).get('currency', '')} {cfg.get('market_inputs', {}).get('sha256', '')}",
        "CARD_PROBE": "; ".join(f"{d} {v.get('result')}" for d, v in sorted(probe.items())) or "n/a",
        "CARD_BK": (f"{mem['beta_k']:+.4f} (90% CI {ci_k[0]:+.4f} to {ci_k[1]:+.4f})" if ci_k else "n/a"),
        "CARD_BJ": (f"{mem['beta_j']:+.4f} (90% CI {ci_j[0]:+.4f} to {ci_j[1]:+.4f})" if ci_j else "n/a"),
        "CARD_MFLAG": flag,
        "CARD_BRIDGE_V6": (fmt(bridge_v6) if (cfg.get("first_v7_ticker") and bridge_v6 is not None) else "n/a"),
        "CARD_BRIDGE_RUNS": (bv if cfg.get("first_v7_ticker") else "n/a"),
        "CARD_S7": cfg.get("stage7", "not run"), "CARD_MANDATE": cfg.get("mandate", "NONE"),
        "CARD_THIN": "; ".join(cfg.get("thin_metrics", [])) or "n/a",
        "CARD_BIGROW": big["row"], "CARD_BIGSIZE": sfmt(big["change"]),
    }
    if v71():
        slots.update({"CARD_L8": lever(ROW_DENOM), "CARD_L9": lever(ROW_ACQ_ORG), "CARD_L10": lever(ROW_ACQ_INC),
                      "CARD_CAP": str(res["card_cap"]), "CARD_ACQ": str(res["card_acq"]),
                      "CARD_ACQ_U": str(res["card_acq_undeclared"]),
                      "CARD_DENOM": str(res["card_denom"])})
    if v8():
        def kr(x):
            return f"{x:.1f}:1" if x is not None else "n/a"
        slots.update({"CARD_R1": rnd(res["lines"][LINE_STEP]["point"], whole),
                      "CARD_R2": rnd(res["lines"][LINE_VICTOR]["point"], whole),
                      "CARD_R3": rnd(res["lines"][LINE_MAX]["point"], whole),
                      "CARD_K0": kr(res.get("implied_ratio_published")),
                      "CARD_K1": kr(res["lines"][LINE_STEP]["implied_ratio"]),
                      "CARD_K2": kr(res["lines"][LINE_VICTOR]["implied_ratio"]),
                      "CARD_K3": kr(res["lines"][LINE_MAX]["implied_ratio"]),
                      "CARD_NOTREE": str(res["card_notree"]),
                      "CARD_NEAR": str(res["card_near"])})
    if v9():
        slots.update({"CARD_L11": lever(ROW_ALTDEN) if alt_card.get("valued") else "n/a",
                      "CARD_ALT_UP": str(alt_card.get("up", 0)), "CARD_ALT_DN": str(alt_card.get("down", 0)),
                      "CARD_ALT_NONE": str(alt_card.get("none", 0)), "CARD_ALT_K": str(alt_card.get("valued", 0))})
    if v10():
        slots.update({"CARD_L12": lever(ROW_DEBT) if debt_card.get("measured") else "n/a",
                      "CARD_OFFBASE": str(res["card_offbase"]), "CARD_OFFBASE_FOLD": str(res["card_offbase_fold"]),
                      "CARD_DEBTDED": str(res["card_debtded"]),
                      "CARD_SRC_D": str(res["card_src"]["defensive"]), "CARD_SRC_A": str(res["card_src"]["average"]),
                      "CARD_SRC_C": str(res["card_src"]["cyclical"]),
                      "CARD_WMULT": f"{res['card_wmult']:.3f}" if res.get("card_wmult") is not None else "n/a"})
    card = (CARD_TEMPLATE_V10 if v10() else CARD_TEMPLATE_V9 if v9() else CARD_TEMPLATE_V8 if v8()
            else CARD_TEMPLATE_V71 if v71() else CARD_TEMPLATE)
    for k, v in slots.items():
        card = card.replace("⟨" + k + "⟩", v)
    h = HEADLINE_TEMPLATE_V10 if v10() else HEADLINE_TEMPLATE_V9 if v9() else HEADLINE_TEMPLATE
    if slots["CARD_MANDATE"] == "NONE":
        h = h.replace("⟨IF CARD_MANDATE ≠ NONE:⟩ The figure is conditional on the user mandate.", "")
    else:
        h = h.replace("⟨IF CARD_MANDATE ≠ NONE:⟩ ", "")
    if slots["CARD_MFLAG"] == "NONE":
        h = h.replace("⟨IF CARD_MFLAG ≠ NONE:⟩ ⟨CARD_MFLAG⟩.", "")
    else:
        h = h.replace("⟨IF CARD_MFLAG ≠ NONE:⟩ ", "")
    for k, v in slots.items():
        h = h.replace("⟨" + k + "⟩", v)
    res["card_slots"] = slots
    return card, h


def fold_log_md(res, folds):
    L = ["# Stage-5b fold log (frozen_arith.py)\n"]
    for r in res["runs"]:
        L.append(f"## Run {r['token']} (dossier {r['dossier']})\n")
        L.append(f"Blind {r['blind']:.6f}; adjusted {r['adjusted']:.6f}; joint delta {r['joint_delta']:+.6f} (back-scaled). "
                 f"Mode: {r['mode']}. Verifier joint delta (run units): {r['verifier_joint_delta']}; verifier adjusted (run units): {r['verifier_adjusted']}.")
        if r["joint_reasons"]:
            L.append("Joint-list problems: " + "; ".join(r["joint_reasons"]))
        L.append("\n| finding | ruling | tags | status | standalone delta (run units) | standalone delta (back-scaled) | verifier delta | reasons |")
        L.append("|---|---|---|---|---|---|---|---|")
        for f in r["findings"]:
            L.append(f"| {f['finding']} | {f['ruling']} | {f['tag1']} / {f['tag2']} | {f['status']} | "
                     f"{fmt(f['standalone_delta'], 4)} | {fmt(f['standalone_delta_backscaled'], 4)} | {f['verifier_delta']} | "
                     f"{'; '.join(f['reasons']) if f['reasons'] else ''} |")
        L.append("")
    if res["log"]:
        L.append("## Verifier-versus-script differences and other log lines\n")
        L += ["- " + x for x in res["log"]]
    return "\n".join(L) + "\n"


def stage5_md(res):
    u = res["unit"]
    L = []
    A = L.append
    A(f"**Published BUY (trimmed mean of adjusted headlines): {res['point']:.6f} {u}.** Blind intermediate: {res['blind_point']:.6f}.")
    A(f"\nInterval: {res['ci'][0]:.6f} to {res['ci'][1]:.6f} (half-width {res['hw']:.6f} = t(0.90,{res['df']}) {res['t90']:.6f} × s {res['s']:.6f} ÷ √{res['N']}). "
      f"*{res['label']}* Replication range: {res['rep'][0]:.6f} to {res['rep'][1]:.6f}.")
    A(f"\nBlind intermediate interval: {res['blind_ci'][0]:.6f} to {res['blind_ci'][1]:.6f} (s {res['blind_s']:.6f}).")
    A(f"\nCommittee fair value (equal-weighted mean of weighted FV of headline seats, retained runs): {res['fv']:.6f} (blind: {res['blind_fv']:.6f}).")
    A(f"\nRetained runs (published): {', '.join(res['retained'])}. Retained runs (blind): {', '.join(res['retained_blind'])}.")
    A(f"\nDescriptive: equal-weighted mean {res['equal_mean']:.6f}; median {res['median']:.6f}.\n")
    A("| run | dossier | blind | adjusted | joint delta | weighted FV (blind) | weighted FV (adjusted) | fold mode |")
    A("|---|---|---|---|---|---|---|---|")
    for r in res["runs"]:
        A(f"| {r['token']} | {r['dossier']} | {r['blind']:.4f} | {r['adjusted']:.4f} | {r['joint_delta']:+.4f} | {r['wfv_blind']:.4f} | {r['wfv_adj']:.4f} | {r['mode']} |")
    A("\n**Leave-one-out point estimates** (descriptive):\n")
    A("| run left out | point | change |")
    A("|---|---|---|")
    for x in res["loo"]:
        A(f"| {x['token']} | {x['point']:.4f} | {x['point'] - res['point']:+.4f} |")
    A(f"\nMost influential run: {res['most_influential_run']}.")
    A(f"\n**Sensitivity ledger (not in the interval).** Each row: change in the published BUY, {u} and in s_w units (s_w = {res['s']:.4f}, adjusted headlines).\n")
    A("| row | counterfactual point | change | change (s_w) | note |")
    A("|---|---|---|---|---|")
    for r in res["ledger"]:
        if r["row"] == ROW_ALTDEN and not (res.get("alt_card") or {}).get("valued"):
            A(f"| {r['row']} | n/a | n/a | n/a | no headline seat reports fair_value_alternative_denominator; {r['extra'] or ''} |")
            continue
        if r["row"] == ROW_DEBT and not (res.get("debt_card") or {}).get("measured"):
            A(f"| {r['row']} | n/a | n/a | n/a | no retained run reports net claims; {r['extra'] or ''} |")
            continue
        A(f"| {r['row']} | {r['point']:.4f} | {r['change']:+.4f} | {r['change_sw']:+.3f} | {r['extra'] or ''} |")
    m = res["memory"] or {}
    if m:
        A(f"| {ROW_MEM} | — | β̂ₖ {m['beta_k']:+.4f} (90% CI {m['ci_k'][0]:+.4f} to {m['ci_k'][1]:+.4f}); β̂ⱼ {m['beta_j']:+.4f} "
          f"(90% CI {m['ci_j'][0]:+.4f} to {m['ci_j'][1]:+.4f}) | permutation p {m['p_perm']} ({m['n_perm']} permutations) | flag {m['flag'] or 'NONE'} |")
    ca = res.get("contrast_adj")
    if ca:
        A(f"| {ROW_CONTRAST} | — | t = {ca['t']:+.4f}, df {ca['df']}, p = {ca['p']:.4f} | camp means " +
          "; ".join(f"{k} {v:.4f}" for k, v in ca["camp_means"].items()) + " | adjusted headlines |")
    if res.get("lines"):
        A(f"\n**Margin-rule alternatives (policy; not ledger rows; not in the interval; never averaged).** Each is the trimmed mean "
          f"of the runs' own-weight headlines under that rule, on the Stage-5b patched summaries; constants fixed in the spec.\n")
        A("| rule | point | change against the published BUY | change (s_w) | blind point | implied expected upside ÷ downside (median over retained runs) |")
        A("|---|---|---|---|---|---|")
        A(f"| Published BUY (quality premium + p·L) | {res['point']:.4f} | — | — | {res['blind_point']:.4f} | {fmt(res.get('implied_ratio_published'))} |")
        for name, x in res["lines"].items():
            A(f"| {name} | {fmt(x['point'], 4)} | {sfmt(x['change'], 4)} | {sfmt(x['change_sw'], 3)} | {fmt(x['blind_point'], 4)} | {fmt(x['implied_ratio'])} |")
    A("\nUnmeasured: dossier-builder variance (1 df with two dossiers); orchestrator variance (Stage 7 not run); model and harness effects.")
    return "\n".join(L) + "\n"


# ----------------------------------------------------------------------------- self-test
def _seat(name, fv, score, tree, irr=False, w=1.0, nob=False):
    return {"investor": name, "fair_value": fv, "quality_score": score, "quality_tier": tier_of(score),
            "discount_rate": 9.0, "fair_value_rf_plus_50bp": fv * 0.95, "terminal_growth": 3.0,
            "tree": tree, "break_p": None, "break_loss": None, "irr_entry": irr, "no_buy": nob, "buy": fv * 0.7}


def selftest():
    """Every earlier case runs in every mode. In v10 mode the earlier cases use "Simon" as an ordinary seated name (they
    test the shared arithmetic), so the v10 roster and NO-BUY rules are switched off for them and restored for the v10 cases."""
    global V10_UNSEATED, V10_NOBUY_RULE
    saved = V10_UNSEATED
    V10_UNSEATED, V10_NOBUY_RULE = set(), False
    try:
        ok, out = _selftest_shared()
    finally:
        V10_UNSEATED, V10_NOBUY_RULE = saved, True
    if v10():
        ok10, out10 = selftest_v10()
        ok, out = ok and ok10, out + out10
    return ok, out


def _selftest_shared():
    out, ok_all = [], True

    def check(name, cond, detail=""):
        nonlocal ok_all
        ok_all &= bool(cond)
        out.append(f"{'PASS' if cond else 'FAIL'}  {name}  {detail}")
    treeA = [{"branch": "bull", "p": 0.20, "value": 60}, {"branch": "base", "p": 0.45, "value": 50},
             {"branch": "bear", "p": 0.20, "value": 42}, {"branch": "break", "p": 0.15, "value": 20}]
    ok, why = check_tree(treeA, 50.0)
    check("1a Appendix-A tree passes the five checks", ok, str(why))
    # B80: the margin base of a score-80 seat: 0.225 (High Quality step) before v8; pi(80) = 0.325 - 12.5/15 * 0.10 in v8
    B80 = (0.325 - 12.5 / 15.0 * 0.10) if v8() else 0.225
    s = recompute_seat(_seat("Simon", 50.0, 80, treeA), 12)
    check(f"1b tier High Quality, base {B80:.6f}", s["tier"] == "High Quality" and abs(s["base"] - B80) < 1e-12, f"base={s['base']}")
    check("1c floor 12: L = 0.60", abs(s["L"] - 0.60) < 1e-12, f"L={s['L']}")
    check("1d p*L = 0.090", abs(s["tail"] - 0.090) < 1e-12, f"tail={s['tail']}")
    check(f"1e required = {B80 + 0.09:.6f}", abs(s["required"] - (B80 + 0.09)) < 1e-12, f"req={s['required']}")
    check(f"1f BUY = {50 * (1 - B80 - 0.09):.6f}", abs(s["buy"] - 50 * (1 - B80 - 0.09)) < 1e-9, f"buy={s['buy']}")
    s2 = recompute_seat(_seat("Simon", 50.0, 80, treeA), 28)
    check(f"1g floor 28: L = 0.44, p*L = 0.066, required {B80 + 0.066:.6f}, BUY {50 * (1 - B80 - 0.066):.6f}",
          abs(s2["L"] - 0.44) < 1e-12 and abs(s2["tail"] - 0.066) < 1e-12 and abs(s2["required"] - (B80 + 0.066)) < 1e-12
          and abs(s2["buy"] - 50 * (1 - B80 - 0.066)) < 1e-9, f"L={s2['L']} tail={s2['tail']} req={s2['required']} buy={s2['buy']}")
    raw, req, nb, buy = seat_margin(0.40, 0.25, 0.90, False, 50.0)
    if v71():
        check("1h Below Average p=0.25 L=0.90: 0.625 > 0.60 -> AT CAP, required 0.60, BUY = 20 (v7.1)",
              not nb and abs(raw - 0.625) < 1e-12 and abs(req - 0.60) < 1e-12 and abs(buy - 20.0) < 1e-9, f"raw={raw} buy={buy}")
    else:
        check("1h Below Average p=0.25 L=0.90: 0.625 > 0.60 -> NO BUY", nb and abs(raw - 0.625) < 1e-12 and buy is None,
              f"raw={raw}")
    sBA = recompute_seat(_seat("Walter", 50.0, 55, [{"branch": "bull", "p": 0.15, "value": 60},
                                                     {"branch": "base", "p": 0.45, "value": 50},
                                                     {"branch": "bear", "p": 0.15, "value": 40},
                                                     {"branch": "break", "p": 0.25, "value": 5}]), None)
    if v71():
        check("1i Below Average seat from a tree with p=0.25, L=0.90 is AT CAP and kept (v7.1)",
              sBA["at_cap"] and not sBA["no_buy"] and abs(sBA["buy"] - 20.0) < 1e-9, f"L={sBA['L']} raw={sBA['raw']}")
        # 6a macro-base L (Appendix A, +200bp add-on): FV 45, fair_value_macro_base 50, break 20
        tr45 = [{"branch": "bull", "p": 0.20, "value": 54}, {"branch": "base", "p": 0.45, "value": 45},
                {"branch": "bear", "p": 0.20, "value": 37.8}, {"branch": "break", "p": 0.15, "value": 20}]
        inv45 = _seat("Simon", 45.0, 80, tr45)
        inv45["fair_value_macro_base"] = 50.0
        s45 = recompute_seat(inv45, None)
        check(f"6a macro-base L: FV 45, FV@macro 50, break 20 -> L 0.60, required {B80 + 0.09:.6f}, BUY {45 * (1 - B80 - 0.09):.6f}",
              abs(s45["L"] - 0.60) < 1e-12 and abs(s45["required"] - (B80 + 0.09)) < 1e-12 and abs(s45["buy"] - 45 * (1 - B80 - 0.09)) < 1e-9,
              f"L={s45['L']} req={s45['required']} buy={s45['buy']}")
        # 6b macro-base estimate when the field is missing: rate 10 vs macro 9, fv 50, fv50 47.5
        lg6 = []
        inv_e = _seat("Simon", 50.0, 80, treeA)
        inv_e["discount_rate"] = 10.0
        est, flag = fv_macro_base(inv_e, 50.0, 9.0, lg6, "", "simon")
        check("6b missing fair_value_macro_base is estimated log-linearly and logged",
              flag and abs(est - 50.0 * (50.0 / 47.5) ** 2) < 1e-9 and lg6, f"est={est}")
    # synthetic run for patch tests
    names = ["Victor", "Simon", "Marcus", "Sophie", "Claire", "Max", "Graham", "Walter", "Helena", "Alexander"]
    invs = []
    for i, n in enumerate(names):
        fv = 50.0 + i
        tr = [{"branch": "bull", "p": 0.20, "value": fv * 1.2}, {"branch": "base", "p": 0.45, "value": fv},
              {"branch": "bear", "p": 0.20, "value": fv * 0.84}, {"branch": "break", "p": 0.15, "value": fv * 0.4}]
        invs.append(_seat(n, fv, 80, tr, irr=n in ("Victor", "Max")))
    S = {"ticker": "X", "unit": "XXX per share",
         "frame": {"weights": {n: 1.0 for n in names}, "valuation_date": "2026-01-01", "pack_as_of_date": "2026-01-01",
                   "per_share_count_m": 100, "latest_share_count_m": 100, "balance_sheet_add_per_share": 0},
         "helena_floor": {"floor_type": "none", "floor_per_share_or_null": None}, "investors": invs}
    h0, seats0 = run_headline_from_summary(S)
    exp = mean([(50.0 + i) * (1 - (B80 + 0.15 * 0.6)) for i, n in enumerate(names) if n not in ("Victor", "Max")])
    check("1j headline = own-weight mean over the eight seats other than Victor and Max", abs(h0 - exp) < 1e-9, f"h={h0} exp={exp}")
    _, ok2, why2, _ = apply_patches(S, [{"path": "investors.Simon.required_margin", "from": 0.315, "to": 0.30}])
    check("2 rejects a path not on the Appendix-F list", not ok2, "; ".join(why2))
    _, ok3, why3, _ = apply_patches(S, [{"path": "investors.Simon.fair_value", "from": 99.0, "to": 49.0}])
    check("3 rejects a patch whose 'from' does not match", not ok3, "; ".join(why3))
    _, ok4, why4, _ = apply_patches(S, [{"path": "investors.Simon.fair_value", "from": 51.0, "to": 45.0}])
    check("4 rejects a patch set after which a tree fails the checks", not ok4, "; ".join(why4))
    S5, ok5, why5, notes5 = apply_patches(S, [{"path": "investors.Simon.fair_value", "from": 51.0, "to": 45.0},
                                              {"path": "investors.Simon.tree.base.value", "from": 51.0, "to": 45.0}])
    check("4b accepts a consistent fair-value + base-branch patch (companion fv50 scaled)",
          ok5 and abs(find_inv(S5, "Simon")["fair_value_rf_plus_50bp"] - 51.0 * 0.95 * 45 / 51) < 1e-9, "; ".join(why5))
    req, nb = v6_required(TIERS.index("High Quality"), 0.15, 0.60, 0.15)
    check("5 v6-rule bridge case: HQ, p=0.15, L=0.60, asym=+0.15 -> required 0.475", abs(req - 0.475) < 1e-12 and not nb,
          f"req={req}")
    # permutation count at 4+4
    y = [0.01, -0.02, 0.03, 0.0, 0.02, -0.01, 0.0, 0.015]
    lk = [0.8, -0.9, 1.2, -1.1, 0.75, -1.3, 1.0, -0.8]
    lj = [0.3, -0.25, -0.4, 0.45, 0.22, 0.35, -0.3, -0.48]
    g = ["A"] * 4 + ["B"] * 4
    o, p, n = perm_test(y, lk, lj, g)
    check("6 permutation test enumerates 576 within-dossier permutations at 4+4", n == 576 and 0 < p <= 1, f"n={n} p={p}")
    tp, keep = trimmed_point([1, 2, 3, 4, 5, 100, 6, 7])
    check("7 trimmed mean drops one highest and one lowest", abs(tp - 4.5) < 1e-12, f"tp={tp}")
    if v71():
        # 8 denominator normalisation: denominator count 103 vs per-share count 100, bsa = -2
        S8 = copy.deepcopy(S)
        S8["frame"].update({"denominator_count_m": 103.0, "per_share_count_m": 100.0, "balance_sheet_add_per_share": -2.0})
        for inv in S8["investors"]:
            inv["fair_value_macro_base"] = inv["fair_value"]
        lg8 = []
        seats8 = recompute_run(S8, lg8)
        sim0 = [x for x in recompute_run(dict(S8, frame=dict(S8["frame"], denominator_count_m=100.0)), []) if x["name"] == "simon"][0]
        sim8 = [x for x in seats8 if x["name"] == "simon"][0]
        exp_fv = (51.0 + 2.0) * 1.03 - 2.0
        check("8 denominator count 103 vs 100: operating value rescaled by 1.03, logged (v7.1)",
              abs(sim8["fv"] - exp_fv) < 1e-9 and abs(sim0["fv"] - 51.0) < 1e-12 and any("C1 denominator" in x for x in lg8),
              f"fv={sim8['fv']} exp={exp_fv}")
        # 9 acquisition mismatches: one of each kind, rest matched
        S9 = copy.deepcopy(S)
        for inv in S9["investors"]:
            inv.update(growth_basis="organic", acq_spend_deducted=False, fair_value_other_acquisition_basis=inv["fair_value"] * 0.9)
        find_inv(S9, "Simon").update(growth_basis="organic", acq_spend_deducted=True)
        find_inv(S9, "Marcus").update(growth_basis="including_acquisitions", acq_spend_deducted=False)
        seats9 = recompute_run(S9, [])
        a9, b9, u9 = acq_mismatches(seats9)
        h_inc = headline_of(cf_acquisitions(seats9, "including_acquisitions")[0])
        h_org = headline_of(cf_acquisitions(seats9, "organic")[0])
        h9 = headline_of(seats9)
        # hand computation: every seat FV f_i, required 0.315 (HQ, p 0.15, L 0.6 at macro = fv); fv_oth = 0.9 f_i.
        # organic row: Simon (mismatched) and Marcus (mismatched) take 0.9 f; others organic keep f.
        # including row: every seat takes 0.9 f (mismatched use matched value; organic seats switch).
        fv9 = {nm: 50.0 + i for i, nm in enumerate(names)}
        hp = [nm for nm in names if nm not in ("Victor", "Max")]
        m9 = 1 - (B80 + 0.09)
        exp_org = mean([fv9[nm] * (0.9 if nm in ("Simon", "Marcus") else 1.0) * m9 for nm in hp])
        exp_inc = mean([fv9[nm] * 0.9 * m9 for nm in hp])
        check("9 acquisition mismatches counted (1 organic+deducted, 1 including+not); rows match hand computation",
              (a9, b9, u9) == (1, 1, 0) and abs(h_org - exp_org) < 1e-9 and abs(h_inc - exp_inc) < 1e-9,
              f"counts={(a9, b9, u9)} org={h_org} exp={exp_org} inc={h_inc} exp={exp_inc}")
        # 10 L floored at 0: break above the macro-base FV
        trf = [{"branch": "bull", "p": 0.20, "value": 60}, {"branch": "base", "p": 0.45, "value": 50},
               {"branch": "bear", "p": 0.20, "value": 48}, {"branch": "break", "p": 0.15, "value": 46}]
        invf = _seat("Simon", 50.0, 80, trf)
        invf["fair_value_macro_base"] = 40.0
        sf = recompute_seat(invf, None)
        check("10 L floored at 0 when the break value exceeds fair_value_macro_base", sf["L"] == 0.0 and abs(sf["required"] - B80) < 1e-12,
              f"L={sf['L']}")
        # 11 convention row 4: per-share 100, period-weighted 104, bsa -2 -> operating value x 100/104
        S11 = copy.deepcopy(S)
        S11["frame"].update({"denominator_count_m": 100.0, "per_share_count_m": 100.0, "period_weighted_count_m": 104.0,
                             "balance_sheet_add_per_share": -2.0})
        seats11 = recompute_run(S11, [])
        cs11, ratio11 = cf_denominator(seats11, S11["frame"])
        sim = [x for x in cs11 if x["name"] == "simon"][0]
        check("11 convention row 4 rescales operating value by per-share / period-weighted count",
              abs(ratio11 - 100 / 104) < 1e-12 and abs(sim["fv"] - ((51.0 + 2.0) * 100 / 104 - 2.0)) < 1e-9, f"fv={sim['fv']}")
        # 12 count patch rejected (v7.1); fair_value without fair_value_macro_base rejected; fv_oth companion scaled
        S12 = copy.deepcopy(S9)
        for inv in S12["investors"]:
            inv["fair_value_macro_base"] = inv["fair_value"]
        S12["frame"].update({"denominator_count_m": 100.0, "per_share_count_m": 100.0})
        _, okc, whyc, _ = apply_patches(S12, [{"path": "frame.denominator_count_m", "from": 100.0, "to": 103.0}])
        check("12a a share-count patch is rejected (counts are normalised by the script, never patched)", not okc, "; ".join(whyc))
        _, okm, whym, _ = apply_patches(S12, [{"path": "investors.Graham.fair_value", "from": 56.0, "to": 50.0},
                                              {"path": "investors.Graham.tree.base.value", "from": 56.0, "to": 50.0}])
        check("12b a fair-value patch without fair_value_macro_base is rejected", not okm and any("fair_value_macro_base" in w for w in whym))
        S12b, okk, whyk, _ = apply_patches(S12, [{"path": "investors.Graham.fair_value", "from": 56.0, "to": 50.0},
                                                 {"path": "investors.Graham.tree.base.value", "from": 56.0, "to": 50.0},
                                                 {"path": "investors.Graham.fair_value_macro_base", "from": 56.0, "to": 56.0}])
        check("12c with fair_value_macro_base (from = to) it is accepted, and fair_value_other_acquisition_basis scales",
              okk and abs(find_inv(S12b, "Graham")["fair_value_other_acquisition_basis"] - 56.0 * 0.9 * 50 / 56) < 1e-9, "; ".join(whyk))
        # 13 a NO-BUY patch on a seat above the cap is honoured
        S13 = copy.deepcopy(S)
        b13 = find_inv(S13, "Walter")
        b13.update(quality_score=55, quality_tier="Below Average",
                   tree=[{"branch": "bull", "p": 0.15, "value": 70}, {"branch": "base", "p": 0.45, "value": 57},
                         {"branch": "bear", "p": 0.15, "value": 45}, {"branch": "break", "p": 0.25, "value": 5.7}], fair_value=57.0)
        h13a, st13 = run_headline_from_summary(S13, [])
        w13 = [x for x in st13 if x["name"] == "walter"][0]
        S13b, ok13, why13, _ = apply_patches(S13, [{"path": "investors.Walter.no_buy", "from": False, "to": True}])
        h13b, st13b = run_headline_from_summary(S13b, [])
        check("13 a seat above 0.60 is AT CAP; a verifier NO-BUY patch on it is honoured and moves the headline",
              w13["at_cap"] and ok13 and [x for x in st13b if x["name"] == "walter"][0]["no_buy"] and abs(h13a - h13b) > 1e-6,
              f"h {h13a} -> {h13b}")
    if v8():
        # 14 quality premium map (G1)
        pts = {52.5: 0.40, 67.5: 0.325, 75.0: 0.275, 82.5: 0.225, 95.0: 0.125, 40.0: 0.40, 99.0: 0.125, 60.0: 0.3625, 90.0: 0.165}
        bad = {q: premium(q) for q, v in pts.items() if abs(premium(q) - v) > 1e-12}
        check("14a quality premium: anchors 52.5/67.5/82.5/95 -> 0.40/0.325/0.225/0.125, linear between, flat outside", not bad, str(bad))
        mids = {}
        lg14 = []
        for t_, want in (("Exceptional", 0.125), ("High Quality", 0.225), ("Average", 0.325), ("Below Average", 0.40)):
            inv14 = _seat("Simon", 50.0, None, treeA)
            inv14["quality_tier"] = t_
            mids[t_] = (recompute_seat(inv14, None, lg14)["base"], want)
        check("14b no numeric score: premium at the reported tier's midpoint score (95/82.5/67.5/52.5), logged",
              all(abs(a_ - b_) < 1e-12 for a_, b_ in mids.values()) and any("midpoint" in x for x in lg14), str(mids))
        # 15 margin-rule alternatives on the Appendix-A seat (G3)
        sA = recompute_seat(_seat("Simon", 50.0, 80, treeA), None)
        ev = 0.20 * 60 + 0.45 * 50 + 0.20 * 42 + 0.15 * 20
        tau = 1 / (1 + TUNED_K)
        P = sA["buy_max"]
        foc = tau * sum(b["p"] * max(b["value"] - P, 0) for b in treeA) - (1 - tau) * sum(b["p"] * max(P - b["value"], 0) for b in treeA)
        check(f"15a tuned Victor = 0.67 x EV 45.9 = 30.753; step tiers = v7.1 BUY 34.25; EV x (1 - pi) = 45.9 x 0.758333",
              abs(sA["buy_victor"] - 30.753) < 1e-9 and abs(sA["buy_step"] - 34.25) < 1e-9
              and abs(sA["buy_evp"] - 45.9 * (1 - B80)) < 1e-9, f"victor={sA['buy_victor']} step={sA['buy_step']}")
        check("15b tuned Max = 66.15 / 2.0125 = 32.8696 (solves E[(V-P)+] = 7.75 E[(P-V)+]); implied ratio there = 7.75",
              abs(P - 66.15 / 2.0125) < 1e-9 and abs(foc) < 1e-9 and TUNED_K == 7.75 and TUNED_C == 0.670
              and abs(implied_ratio([dict(sA, w=1.0)], P, "buy_max") - 7.75) < 1e-9, f"P={P} foc={foc}")
        trs = [dict(b, p=b["p"] * 1.004) for b in treeA]
        check("15c tuned Victor uses the probability-weighted mean (probabilities summing to 1.004)",
              abs(0.67 * tree_ev(trs) - 30.753) < 1e-9)
        # 16 roster: a v8 run of eight seats; a Victor seat in a v8 summary is logged and kept out
        S16 = copy.deepcopy(S)
        S16["investors"] = [x for x in S16["investors"] if x["investor"] not in ("Victor", "Max")]
        for x in S16["investors"]:
            x.pop("irr_entry", None)
        S16["frame"]["weights"] = {n: 1.0 for n in names if n not in ("Victor", "Max")}
        h16, _ = run_headline_from_summary(S16, [])
        lg16 = []
        h16b, _ = run_headline_from_summary(S, lg16)
        S16v = copy.deepcopy(S)   # Victor and Max with a different score and break shape, so any leak would show
        for nm_ in ("Victor", "Max"):
            iv = find_inv(S16v, nm_)
            iv["quality_score"], iv["quality_tier"] = 55, "Below Average"
            for b_ in iv["tree"]:
                if b_["branch"] == "break":
                    b_["value"] = iv["fair_value"] * 0.05
        sA16, sB16 = recompute_run(S16, []), recompute_run(S16v, [])
        same16 = all(abs((f_(sA16) or 0) - (f_(sB16) or 0)) < 1e-9 for f_ in (
            lambda x: wmean_field(x, "base"), lambda x: wmean_field(x, "tail"), wfv_of,
            lambda x: headline_of(x, buy_key="buy_step"), lambda x: headline_of(x, buy_key="buy_victor"),
            lambda x: headline_of(x, buy_key="buy_max"), lambda x: headline_of(x, buy_key="buy_evp"),
            lambda x: len(headline_seats(x)), lambda x: sum(1 for z in headline_seats(x) if z.get("near_cut"))))
        check("16 eight-seat run: headline, premium, tail, FV, every line and the counts equal those of the same run "
              "with Victor and Max present (kept out, logged C5)",
              abs(h16 - exp) < 1e-9 and abs(h16b - exp) < 1e-9 and same16 and any("C5 not a seated" in x for x in lg16), f"h={h16}")
        S16p, ok16p, why16p, notes16p = apply_patches(S, [{"path": "investors.Victor.fair_value", "from": 50.0, "to": 40.0},
                                                         {"path": "investors.Simon.quality_score", "from": 80, "to": 76}])
        check("16b a patch to Victor or Max is dropped with a note; the rest of the finding applies",
              ok16p and find_inv(S16p, "Victor")["fair_value"] == 50.0 and find_inv(S16p, "Simon")["quality_score"] == 76
              and any("outside the roster" in x for x in notes16p), "; ".join(why16p))
        _, ok16c, why16c, _ = apply_patches(S, [{"path": "investors.Simon.quality_score", "from": 80, "to": 250}])
        check("16c a quality_score patch outside 0-100 is rejected", not ok16c)
        # 17 seats near a tier cut-off (card)
        check("17 near a cut-off: 72 and 77 and 57 yes; 70 and 82 no",
              near_cut(72) and near_cut(77) and near_cut(57) and not near_cut(70) and not near_cut(82))
        # 18 a seat with an invalid tree is left out of the tuned lines, weight dropped
        S18 = copy.deepcopy(S16)
        find_inv(S18, "Simon")["tree"] = []
        find_inv(S18, "Simon").update(break_p=0.15, break_loss=0.6)
        seats18 = recompute_run(S18, [])
        hv = headline_of(seats18, buy_key="buy_victor")
        expv = mean([0.67 * tree_ev([dict(b) for b in find_inv(S18, n)["tree"]]) for n in names
                     if n not in ("Victor", "Max", "Simon")])
        check("18 a seat without a valid tree is left out of the tuned lines (weight dropped)", abs(hv - expv) < 1e-9, f"hv={hv} exp={expv}")
        check("18b a line undefined in some runs: trimmed over the others; n/a below 3 runs",
              abs(line_point([1.0, 2.0, None, 3.0, 4.0]) - 2.5) < 1e-12 and line_point([1.0, None, 2.0]) is None)
        # 19 the step line repeats the v7.1 F5 decision: no_buy with no reason, step raw above 0.60, premium raw below
        tr19 = [{"branch": "bull", "p": 0.15, "value": 60}, {"branch": "base", "p": 0.45, "value": 50},
                {"branch": "bear", "p": 0.15, "value": 40}, {"branch": "break", "p": 0.25, "value": 5.5}]
        inv19 = _seat("Walter", 50.0, 59, tr19, nob=True)
        s19 = recompute_seat(inv19, None, [])
        check("19 step line repeats the v7.1 F5 decision (score 59: v7.1 AT CAP while the premium honours the NO BUY)",
              s19["no_buy"] and s19["buy_step"] is not None and abs(s19["buy_step"] - 20.0) < 1e-9,
              f"no_buy={s19['no_buy']} step={s19['buy_step']}")
        # 20 a tree patch to a seat whose tree is null builds a tree, and does not crash
        S20 = copy.deepcopy(S16)
        mk = find_inv(S20, "Marcus")
        mk["tree"] = None
        pts20 = [{"path": f"investors.Marcus.tree.{b['branch']}.{f}", "from": None, "to": (b[f] * (52 / 50) if f == "value" else b[f])}
                 for b in treeA for f in ("p", "value")]
        S20b, ok20, why20, _ = apply_patches(S20, pts20)
        check("20 tree patches to a seat whose tree is null are applied without error", ok20 and len(find_inv(S20b, "Marcus")["tree"]) == 4,
              "; ".join(why20))
        # 21 forecasts follow the F1 denominator normalisation (a per-share flow, no balance-sheet add)
        S21 = copy.deepcopy(S16)
        S21["frame"].update({"denominator_count_m": 103.0, "per_share_count_m": 100.0, "balance_sheet_add_per_share": -2.0})
        find_inv(S21, "Simon")["forecast_5y"] = [{"period_end": "2027-12-31", "months": 12, "cash_flow_total": 400.0,
                                                  "cash_flow_per_share": 4.0}]
        sim21 = [x for x in recompute_run(S21, []) if x["name"] == "simon"][0]
        check("21 forecast cash flow per share x 1.03 under F1 normalisation; totals unchanged",
              abs(sim21["forecast"][0]["cash_flow_per_share"] - 4.12) < 1e-9 and sim21["forecast"][0]["cash_flow_total"] == 400.0)
    if v9():
        # 22a alternative-denominator row: margin held, so every BUY scales with its alternative fair value
        S22 = copy.deepcopy(S16)
        for x in S22["investors"]:
            x["fair_value_alternative_denominator"] = x["fair_value"] * 1.2
        st22 = recompute_run(S22, [])
        lg22 = []
        h22 = headline_of(cf_altdenom(st22, lg22)[0])
        find_inv(S22, "Simon").pop("fair_value_alternative_denominator")
        st22b = recompute_run(S22, [])
        cs22b, miss22 = cf_altdenom(st22b, lg22)
        exp22b = mean([s_["buy"] * (1.0 if s_["name"] == "simon" else 1.2) for s_ in headline_seats(st22b)])
        check("22a alternative-denominator row = headline x 1.2 when every alternative FV is 1.2 x FV; a seat without "
              "the field keeps its FV (logged C8)", abs(h22 - 1.2 * headline_of(st22)) < 1e-9 and miss22 == 1
              and abs(headline_of(cs22b) - exp22b) < 1e-9 and any("C8" in x for x in lg22), f"h={h22}")
        # 22b zero acquisition spend: declared pairs match; both rows equal the headline; non-zero spend still counts
        S22z = copy.deepcopy(S16)
        for x in S22z["investors"]:
            x.update(growth_basis="organic", acq_spend_deducted=False, fair_value_other_acquisition_basis=x["fair_value"] * 0.9)
        find_inv(S22z, "Marcus").update(growth_basis="including_acquisitions", acq_spend_deducted=False)
        S22z["frame"]["acq_spend_normalised_per_share"] = 0.0
        S22z["frame"]["acq_cash_by_year"] = []
        st22z = recompute_run(S22z, [])
        fz = S22z["frame"]
        hz = headline_of(st22z)
        rows_eq = all(abs(headline_of(cf_acquisitions(st22z, tg, None, "", fz)[0]) - hz) < 1e-12
                      for tg in ("organic", "including_acquisitions"))
        nz = acq_mismatches(st22z, dict(fz, acq_spend_normalised_per_share=1.0))
        nx = acq_mismatches(st22z, dict(fz, acq_cash_by_year=[{"year": 2025, "amount": 900.0}]))   # a deal excluded
        check("22b zero acquisition spend: no mismatch counted, both acquisition rows equal the headline; with spend 1.0, "
              "or with acquisition cash the run excluded, the including-without-deduction seat is counted",
              acq_mismatches(st22z, fz) == (0, 0, 0) and rows_eq and nz == (0, 1, 0) and nx == (0, 1, 0),
              f"zero={acq_mismatches(st22z, fz)} nonzero={nz} excluded={nx}")
        # 22c the modal tier must be a tier name (logged C8, moves nothing)
        S22m = copy.deepcopy(S16)
        S22m["quality_tier_modal"] = "High Quality (tie 4-4 with Average, broken by the top-weighted seat)"
        lg22m = []
        run_metrics(dict(token="t", dossier="A", k=1.0, j=1.0, summary=S22m, seats=recompute_run(S22m, []), bridge=False),
                    lg22m, "")
        S22m["quality_tier_modal"] = "Average"
        lg22n = []
        run_metrics(dict(token="t", dossier="A", k=1.0, j=1.0, summary=S22m, seats=recompute_run(S22m, []), bridge=False),
                    lg22n, "")
        check("22c a modal tier that is not a tier name is logged C8; a tier name is not",
              any("quality_tier_modal" in x for x in lg22m) and not any("quality_tier_modal" in x for x in lg22n))
        # 22d the alternative FV is a companion: scaled with a fair-value patch, rejected alone
        S22p = copy.deepcopy(S16)
        for x in S22p["investors"]:
            x["fair_value_macro_base"] = x["fair_value"]
            x["fair_value_alternative_denominator"] = x["fair_value"] * 1.2
        S22q, okp, whyp, _ = apply_patches(S22p, [{"path": "investors.Simon.fair_value", "from": 51.0, "to": 45.0},
                                                  {"path": "investors.Simon.tree.base.value", "from": 51.0, "to": 45.0},
                                                  {"path": "investors.Simon.fair_value_macro_base", "from": 51.0, "to": 51.0}])
        _, oka, whya, _ = apply_patches(S22p, [{"path": "investors.Simon.fair_value_alternative_denominator",
                                                "from": 61.2, "to": 70.0}])
        _, ok1, _, _ = apply_patches(S22p, [{"path": "investors.Simon.fair_value_alternative_denominator",
                                             "from": 61.2, "to": 51.0}])
        S22r, okr, whyr, _ = apply_patches(S22p, [{"path": f"investors.{x['investor']}.fair_value_alternative_denominator",
                                                   "from": x["fair_value_alternative_denominator"], "to": x["fair_value"]}
                                                  for x in S22p["investors"]])
        check("22d fair_value_alternative_denominator scales with a fair-value patch; alone it is rejected unless every "
              "seat's value is set equal to its fair_value (an alternative that breaks the definition), and the run then "
              "counts as none",
              okp and abs(find_inv(S22q, "Simon")["fair_value_alternative_denominator"] - 61.2 * 45 / 51) < 1e-9 and not oka
              and not ok1 and okr and find_inv(S22r, "Simon")["fair_value_alternative_denominator"] == 51.0
              and alt_denom_checks(recompute_run(S22r, []), dict(S22r.get("frame") or {}, declared_denominator_per_share=4.0,
                                   alternative_denominator_per_share=5.0, alternative_denominator_basis="margin"))["direction"] == "none",
              "; ".join(whyp + whya + whyr))
        # 22f N2 checks and the row's edge cases: a non-positive alternative FV is NO BUY in the row; basis enum; "none"
        S22f = copy.deepcopy(S16)
        S22f["frame"].update(declared_denominator_per_share=4.0, alternative_denominator_per_share=5.0,
                             alternative_denominator_basis="margin", balance_sheet_add_per_share=0.0)
        for x in S22f["investors"]:
            x["fair_value_alternative_denominator"] = x["fair_value"] * 1.25
        st22f = recompute_run(S22f, [])
        lgf = []
        c22f = alt_denom_checks(st22f, S22f["frame"], lgf)
        find_inv(S22f, "Claire")["fair_value_alternative_denominator"] = -40.0
        find_inv(S22f, "Simon")["fair_value_alternative_denominator"] = find_inv(S22f, "Simon")["fair_value"] * 1.6
        st22g = recompute_run(S22f, [])
        lgg = []
        cs22g, _ = cf_altdenom(st22g, lgg)
        hs22g = [s_ for s_ in headline_seats(st22g) if s_["name"] != "claire"]
        exp22g = (sum(s_["w"] * s_["buy"] * (1.6 if s_["name"] == "simon" else 1.25) for s_ in hs22g)
                  / sum(s_["w"] for s_ in hs22g))
        lgh = []
        c22g = alt_denom_checks(st22g, S22f["frame"], lgh)
        S22n = copy.deepcopy(S16)
        S22n["frame"].update(declared_denominator_per_share=4.0, alternative_denominator_per_share=4.4,
                             alternative_denominator_basis="none")
        lgn = []
        c22n = alt_denom_checks(recompute_run(S22n, []), S22n["frame"], lgn)
        S22n["frame"]["alternative_denominator_basis"] = "both"
        lgb = []
        alt_denom_checks(recompute_run(S22n, []), S22n["frame"], lgb)
        check("22f N2 checks: direction up at ratio 1.25 with nothing logged; a negative alternative FV is NO BUY in the "
              "row (weight dropped, logged) and a seat scaling 1.6 against 1.25 is logged C4; 'none' with unequal "
              "denominators is logged C1; a basis outside the enum is logged C8",
              c22f["direction"] == "up" and not lgf and abs(headline_of(cs22g) - exp22g) < 1e-9
              and any("<= 0" in x for x in lgg) and any("C4 simon" in x for x in lgh) and c22g["valued"] == c22g["n"]
              and c22n["direction"] == "none" and any(x.startswith("C1") for x in lgn) and any("C8" in x for x in lgb),
              f"{headline_of(cs22g)} vs {exp22g}; {lgf + lgg + lgh + lgn + lgb}")
        # 22g the verifier's mechanism flag is read strictly in v9
        check("22g mechanism flag: true and 'true' are MECHANISM; 'false', false and a missing flag are not",
              mech_flag(True) and mech_flag("True") and not mech_flag("false") and not mech_flag(False) and not mech_flag(None))
        # 22e the v9 card has the alternative-denominator lever and no memory or bridge line; no memory flag sentence
        check("22e v9 Decision Card: lever L11 present; memory, bridge and memory-flag slots absent",
              "⟨CARD_L11⟩" in CARD_TEMPLATE_V9 and "CARD_MFLAG" not in CARD_TEMPLATE_V9 + HEADLINE_TEMPLATE_V9
              and "CARD_BRIDGE" not in CARD_TEMPLATE_V9 and "CARD_PROBE" not in CARD_TEMPLATE_V9)
    return ok_all, out


# ----------------------------------------------------------------------------- CLI
def _v10_run(scale=1.0):
    """A constructed v10 run: seven seats at the macro base (9.5), plus a Simon seat (outside the roster)."""
    names = ["Marcus", "Sophie", "Claire", "Graham", "Walter", "Helena", "Alexander", "Simon"]
    invs = []
    for i, n in enumerate(names):
        fv = (50.0 + i) * scale
        tr = [{"branch": "bull", "p": 0.20, "value": fv * 1.2}, {"branch": "base", "p": 0.45, "value": fv},
              {"branch": "bear", "p": 0.20, "value": fv * 0.84}, {"branch": "break", "p": 0.15, "value": fv * 0.4}]
        inv = _seat(n, fv, 80, tr)
        inv.update(discount_rate=9.5, fair_value_macro_base=fv, quality_premium=premium(80), terminal_growth=2.0 + 0.25 * i,
                   fair_value_alternative_denominator=fv, fair_value_other_acquisition_basis=fv,
                   growth_basis="organic", acq_spend_deducted=False,
                   break_derivation={"mechanism": "m", "reference": "r", "adjustment_pp": 0, "horizon_years": 5},
                   forecast_definition="d",
                   forecast_5y=[{"period_end": f"{2026 + y}-12-31", "months": 12, "cash_flow_total": 100.0 * 1.1 ** y,
                                 "cash_flow_per_share": 1.0 * 1.1 ** y} for y in range(5)])
        invs.append(inv)
    walter = [x for x in invs if x["investor"] == "Walter"][0]
    walter["management_grade"] = {"components": {"capital_allocation": 2, "trust_guidance": 1, "incentive_alignment": 0,
                                                 "insider_transactions": 1, "board_governance": 0, "returns_vs_sector": 0},
                                  "gates": {"trust": "PASS", "incentive_alignment": "PASS", "board_governance": "PASS",
                                            "capital_structure": "PASS"}, "score": 4, "multiplier": 1.06}
    alex = [x for x in invs if x["investor"] == "Alexander"][0]
    alex["earnings_quality"] = {"score": 85, "adjustment": 0.10}
    frame = {"risk_free": 5.0, "erp": 4.5, "macro_base": 9.5, "market_inputs_as_of": "2026-10-08",
             "denominator_count_m": 100.0, "per_share_count_m": 100.0, "latest_share_count_m": 100.0,
             "period_weighted_count_m": 100.0, "per_share_count_basis": "point",
             "pack_as_of_date": "2026-09-30", "valuation_date": "2026-09-30", "per_share_count_date": "2026-09-30",
             "latest_share_count_date": "2026-09-30", "balance_sheet_date": "2026-09-30",
             "balance_sheet_add_per_share": 2.0, "declared_denominator_per_share": 5.0, "gross_denominator_per_share": 5.0,
             "denominator_adjustments": [], "denominator_type": "owner FCF", "alternative_denominator_type": "owner FCF",
             "alternative_denominator_basis": "none", "alternative_denominator_per_share": 5.0,
             "debt_deducted_per_share": 0.0, "net_claims_per_share": 10.0, "debt_path": "held constant",
             "systematic_risk_class": "average", "weights": {n: 1.0 for n in names},
             "acq_cash_by_year": [], "acq_spend_normalised_per_share": 0.0, "guidance_stance": "skeptical"}
    risks = [{"risk": f"risk {n}", "seat": n, "channel": "quality_score", "size": -2, "reason_or_null": None}
             for n in names if n != "Simon"]
    return {"frame": frame, "helena_floor": {"floor_per_share_or_null": None, "floor_type": "none"}, "investors": invs,
            "risks": risks, "quality_tier_modal": "High Quality"}


def selftest_v10():
    out, ok_all = [], True

    def check(name, cond, detail=""):
        nonlocal ok_all
        ok_all &= bool(cond)
        out.append(f"{'PASS' if cond else 'FAIL'}  {name}  {detail}")
    MI = {"risk_free": 5.0, "erp": 4.5}
    S = _v10_run()
    lg = []
    seats = recompute_run(S, lg)
    simon = [x for x in seats if x["name"] == "simon"][0]
    S_no = copy.deepcopy(S)
    S_no["investors"] = [x for x in S_no["investors"] if x["investor"] != "Simon"]
    h, h_no = headline_of(seats), headline_of(recompute_run(S_no, []))
    check("V10a a seat named Simon is outside the roster (C5 logged) and leaves the headline unchanged",
          simon["irr"] and any("simon: C5 not a seated investor under v10" in x for x in lg) and abs(h - h_no) < 1e-12
          and committee() == ROSTER_V10, f"h={h} h_no={h_no}")
    c0 = v10_checks(S, seats, MI, [], "")
    check("V10b a clean run logs no v10 check", c0["issues"] == 0 and c0["off_base"] == 0, str(c0))
    # off the macro base: Graham at 10.5 with FV 45 (fair_value_macro_base 50; Appendix-A tree)
    S2 = copy.deepcopy(S)
    g = find_inv(S2, "Graham")
    tr45 = [{"branch": "bull", "p": 0.20, "value": 54}, {"branch": "base", "p": 0.45, "value": 45},
            {"branch": "bear", "p": 0.20, "value": 37.8}, {"branch": "break", "p": 0.15, "value": 20}]
    g.update(discount_rate=10.5, fair_value=45.0, fair_value_macro_base=50.0, tree=tr45, fair_value_rf_plus_50bp=43.0)
    lg2 = []
    seats2 = recompute_run(S2, lg2)
    c2 = v10_checks(S2, seats2, MI, lg2, "")
    S2w = copy.deepcopy(S)   # a run on the unrebased ERP: its own base 9.31, every seat at it
    S2w["frame"].update(erp=4.31, macro_base=9.31)
    for inv in S2w["investors"]:
        inv["discount_rate"] = 9.31
    c2w = v10_checks(S2w, recompute_run(S2w, []), MI, [], "")
    gs = [x for x in seats2 if x["name"] == "graham"][0]
    check("V10c seats off the macro base are logged against MARKET_INPUTS (by rate, by a wrong run base, and by "
          "fair_value_macro_base), and no BUY moves",
          c2["off_base"] == 1 and c2["off_seats"] == ["graham"] and c2w["off_base"] == 7
          and any("graham: C2 off the macro base" in x for x in lg2)
          and abs(gs["buy"] - 45.0 * (1 - premium(80) - 0.15 * (1 - 20 / 50.0))) < 1e-9, f"buy={gs['buy']} wrong-base={c2w['off_base']}")
    P, why = rebase_patches(S2, "Graham")
    S3, ok3, why3, notes3 = apply_patches(S2, P) if P else (None, False, [why], [])
    g3 = [x for x in recompute_run(S3, []) if x["name"] == "graham"][0] if ok3 else None
    others = [x["buy"] for x in seats2 if x["name"] not in ("graham", "simon")]
    h3 = headline_of(recompute_run(S3, [])) if ok3 else None
    brk3 = [b for b in find_inv(S3, "Graham")["tree"] if b["branch"] == "break"][0]["value"] if ok3 else None
    check("V10d the rebase patch set (break held) is accepted and gives the Appendix-A rebase case (BUY 33.417) "
          "and the hand headline",
          ok3 and abs(g3["fv"] - 50.0) < 1e-9 and brk3 == 20 and abs(g3["L"] - 0.60) < 1e-12
          and abs(g3["buy"] - 50 * (1 - premium(80) - 0.09)) < 1e-9 and abs(g3["buy"] - 33.417) < 5e-4
          and abs(h3 - (sum(others) + g3["buy"]) / 7) < 1e-9
          and abs(find_inv(S3, "Graham")["fair_value_rf_plus_50bp"] - 43.0 * 50 / 45) < 1e-9,
          f"ok={ok3} {why3} g3={g3 and (g3['fv'], g3['required'], g3['buy'])}")
    ver = {"rulings": [{"finding": "1", "ruling": "CONFIRMED", "quantified": True, "mechanism": False,
                        "changed_inputs": P}], "joint_changed_inputs": P}
    fo = fold_run(S2, ver, [])
    check("V10e a folded rebase finding is labelled approximate in the fold log",
          "rebase to the macro base, approximate" in fo["findings"][0]["status"] and abs(fo["adjusted"] - h3) < 1e-9,
          fo["findings"][0]["status"])
    P0, why0 = rebase_patches(S, "Graham")
    check("V10f no rebase for a seat already at the macro base", P0 is None and "equals" in why0, str(why0))
    # Walter (Appendix A): grade +4 -> multiplier 1.06 on every branch's operating value (balance-sheet add 0)
    trW = [{"branch": "bull", "p": 0.20, "value": 63.6}, {"branch": "base", "p": 0.45, "value": 53.0},
           {"branch": "bear", "p": 0.20, "value": 44.52}, {"branch": "break", "p": 0.15, "value": 21.2}]
    invW = _seat("Walter", 53.0, 80, trW)
    invW["fair_value_macro_base"] = 53.0
    sW = recompute_seat(invW, None)
    check("V10g Appendix-A Walter case: L 0.60 unchanged by the multiplier, required 0.33167, BUY 35.422",
          abs(sW["L"] - 0.60) < 1e-9 and abs(sW["buy"] - 53 * (1 - premium(80) - 0.09)) < 1e-9
          and abs(sW["buy"] - 35.422) < 5e-4 and abs(walter_multiplier(find_inv(S, "Walter")["management_grade"]) - 1.06) < 1e-12,
          f"buy={sW['buy']}")
    S4 = copy.deepcopy(S)
    gW = find_inv(S4, "Walter")["management_grade"]
    gW["multiplier"] = 1.07
    gW["gates"]["trust"] = "CAUTION"
    gW["gates"]["board_governance"] = "FAIL"
    gW["gates"]["capital_structure"] = "FAIL"
    lg4 = []
    v10_checks(S4, recompute_run(S4, []), MI, lg4, "")
    check("V10h Walter's wrong multiplier, an uncapped CAUTION and two FAILs without NO BUY are logged (C5); the card "
          "multiplier uses the components", any("multiplier 1.07 is not" in x for x in lg4)
          and any("gate trust CAUTION but component trust_guidance" in x for x in lg4)
          and any("gate capital_structure FAIL but component capital_allocation" in x for x in lg4)
          and any("2 FAILs but the seat is not NO BUY" in x for x in lg4) and abs(walter_multiplier(gW) - 1.06) < 1e-12,
          "; ".join(lg4))
    S4n = copy.deepcopy(S4)
    find_inv(S4n, "Walter").update(no_buy=True, no_buy_reason_or_null="two FAILs")
    find_inv(S4n, "Marcus").update(no_buy=True, no_buy_reason_or_null="bogus")
    lg4n = []
    st4n = recompute_run(S4n, lg4n)
    wn, mn = [x for x in st4n if x["name"] == "walter"][0], [x for x in st4n if x["name"] == "marcus"][0]
    check("V10i NO BUY honoured only for Walter with two FAIL gates; any other reported NO BUY is logged (C7) and kept",
          wn["no_buy"] and not mn["no_buy"] and mn["buy"] is not None and any("marcus: C7 no_buy reported, but under v10" in x for x in lg4n))
    find_inv(S4, "Alexander")["earnings_quality"] = {"score": 70, "adjustment": 0.10}
    lg4b = []
    v10_checks(S4, recompute_run(S4, []), MI, lg4b, "")
    check("V10j Alexander's adjustment off the FRAMEWORK mapping is logged", any("alexander: C5 earnings_quality" in x for x in lg4b),
          "; ".join(x for x in lg4b if "alexander" in x))
    # debt: Appendix-A debt row; an unmeasured run; a run with debt deducted and its undebt patches
    invD = _seat("Marcus", 50.0, 80, treeA_v10())
    invD["fair_value_macro_base"] = 50.0
    sD = recompute_seat(invD, 12)
    sD["w"] = 1.0
    cD, mD = cf_debt([sD], {"net_claims_per_share": 10.0})
    check("V10k Appendix-A debt row: FV 40, BUY 26.733 against 33.417",
          mD and abs(cD[0]["fv"] - 40.0) < 1e-9 and abs(cD[0]["buy"] - 40 * (1 - premium(80) - 0.09)) < 1e-9
          and abs(cD[0]["buy"] - 26.733) < 5e-4 and abs(sD["buy"] - 33.417) < 5e-4, f"fv={cD[0]['fv']} buy={cD[0]['buy']}")
    cL, mL = cf_debt([sD], {"net_claims_per_share": 0.0})
    check("V10l a run with no net claims keeps its headline in the debt row", not mL and abs(cL[0]["buy"] - sD["buy"]) < 1e-12)
    S5 = copy.deepcopy(S)
    S5["frame"].update(debt_deducted_per_share=12.0, balance_sheet_add_per_share=2.0 - 12.0)
    for inv in S5["investors"]:
        for f in ("fair_value", "fair_value_macro_base", "fair_value_rf_plus_50bp", "fair_value_other_acquisition_basis",
                  "fair_value_alternative_denominator"):
            inv[f] = inv[f] - 12.0
        for b in inv["tree"]:
            b["value"] = b["value"] - 12.0
    lg5 = []
    v10_checks(S5, recompute_run(S5, []), MI, lg5, "")
    P5, _ = undebt_patches(S5)
    S5u, ok5, why5, _ = apply_patches(S5, P5) if P5 else (None, False, ["no patches"], [])
    h5u = headline_of(recompute_run(S5u, [])) if ok5 else None
    check("V10m a run with debt deducted is logged (C1), and the undebt patches restore the undeducted headline",
          any("deducted from cash flow to equity" in x for x in lg5) and ok5 and abs(h5u - h) < 1e-9, f"{why5} {h5u} vs {h}")
    # register
    S7 = copy.deepcopy(S)
    S7["risks"] = S7["risks"][:-1] + [
        {"risk": "x", "seat": "Marcus", "channel": "rate_addon", "size": 1},
        {"risk": "y", "seat": "Marcus", "channel": "base_cash_flows", "size": None},
        {"risk": "z", "seat": "Marcus", "channel": "fv_mapping", "size": -5},
        {"risk": "Risk  Sophie", "seat": "Sophie", "channel": "break_branch", "size": 1.5},
        {"risk": "upside launch", "seat": "Claire", "channel": "non_break_branch", "size": 1.2}]
    lg7 = []
    c7 = v10_checks(S7, recompute_run(S7, []), MI, lg7, "")
    check("V10n register: unknown channel, missing size, fv_mapping without a mapping, a risk in two channels and a seat "
          "with no entry are logged (C6); a non_break_branch entry is accepted",
          any("is not on the closed list" in x for x in lg7) and any("no numeric size" in x for x in lg7)
          and any("fv_mapping for marcus" in x for x in lg7) and any("entered in 2 channels" in x for x in lg7)
          and any("alexander: C6 no entry" in x for x in lg7) and c7["register"]["issues"] == 5
          and not any("upside launch" in x for x in lg7), "; ".join(lg7))
    # monitor and BUY effects
    seatsM = recompute_run(S, [])
    tgw = wmean_field(seatsM, "tg")
    mar = [x for x in seatsM if x["name"] == "marcus"][0]
    be_q = buy_effect({"channel": "quality_score", "size": -2}, mar)
    be_b = buy_effect({"channel": "base_cash_flows", "size": -1.0}, mar)
    check("V10o channel monitor: forecast growth 10.0%, terminal growth weighted mean, Walter's multiplier; register "
          "BUY effects (score cut of 2 points; a base drag of 1)",
          abs(forecast_growth(find_inv(S, "Marcus")["forecast_5y"]) - 10.0) < 1e-9
          and abs(tgw - mean([2.0 + 0.25 * i for i in range(7)])) < 1e-12
          and abs([x for x in seatsM if x["name"] == "walter"][0]["wmult"] - 1.06) < 1e-12
          and abs(be_q - mar["fv"] * (premium(82) - premium(80))) < 1e-12 and be_q < 0
          and abs(be_b + (1 - mar["required"])) < 1e-12, f"tg={tgw} be_q={be_q}")
    # end to end: six runs through Stage 3 and Stage 5 in v10 mode
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        runs = []
        for i, sc in enumerate((1.00, 1.02, 0.98, 1.05, 0.95, 1.01)):
            p = os.path.join(td, f"r{i}.json")
            json.dump(_v10_run(sc), open(p, "w"))
            runs.append(dict(token=f"r{i}", dossier="A" if i < 3 else "B", k=1.0, j=1.0, run_file=p))
        cfg = dict(ticker="T", unit="USD per share", as_of="2026-10-08", runs=runs, bridge_runs=[], spec_version="v10",
                   market_inputs=dict(risk_free=5.0, erp=4.5, currency="USD", sha256="0" * 64), verifications={})
        r3 = stage3(cfg, os.path.join(td, "o"))
        r5 = stage5(cfg, os.path.join(td, "o"))
    ind = r3["induced"].get("every seat's discount_rate = macro_base and fair_value_macro_base = fair_value", {})
    led = {x["row"]: x for x in r5["ledger"]}
    check("V10p end to end (six runs): the rate rule is INDUCED; the debt row is on the card but never the largest "
          "sensitivity; off-base 0, debt deducted 0, risk class average 6",
          ind.get("label") == "INDUCED" and ROW_DEBT in led and r5["card_slots"]["CARD_L12"] != "n/a"
          and r5["card_slots"]["CARD_BIGROW"] != ROW_DEBT and abs(led[ROW_DEBT]["change"]) > abs(led[r5["card_slots"]["CARD_BIGROW"]]["change"])
          and r5["card_offbase"] == 0 and r5["card_debtded"] == 0 and r5["card_src"]["average"] == 4,
          f"ind={ind.get('label')} big={r5['card_slots']['CARD_BIGROW']} L12={r5['card_slots']['CARD_L12']} src={r5['card_src']}")
    check("V10q card template carries the debt lever and the v10 status line; mode labels",
          "⟨CARD_L12⟩" in CARD_TEMPLATE_V10 and "⟨CARD_DEBTDED⟩" in CARD_TEMPLATE_V10 and MECH_VERSION["v10"] == "v10"
          and v9() and v8())
    return ok_all, out


def treeA_v10():
    return [{"branch": "bull", "p": 0.20, "value": 60}, {"branch": "base", "p": 0.45, "value": 50},
            {"branch": "bear", "p": 0.20, "value": 42}, {"branch": "break", "p": 0.15, "value": 20}]


def _print_seats(seats, h, hu):
    print(f"{'investor':<10} {'irr':<4} {'fv':>12} {'score':>6} {'tier':<14} {'p':>6} {'L':>8} {'tail':>8} {'required':>9} {'no_buy':<6} {'buy':>12} {'w':>5} tree")
    for s in seats:
        print(f"{s['name']:<10} {str(s['irr'])[0]:<4} {fmt(s['fv'], 4):>12} {fmt(s['score'], 0):>6} {s['tier']:<14} "
              f"{fmt(s['p'], 4):>6} {fmt(s['L'], 5):>8} {fmt(s['tail'], 5):>8} {fmt(s['required'], 5):>9} {str(s['no_buy']):<6} "
              f"{fmt(s['buy'] if not s['irr'] else s.get('entry'), 4):>12} {fmt(s['w'], 2):>5} {'ok' if s['tree_ok'] else 'INVALID'}")
    print(f"headline (own weights): {h}")
    print(f"headline (uniform weights): {hu}")


def main(argv):
    global SPEC
    if "--spec" in argv:
        i = argv.index("--spec")
        SPEC = argv[i + 1]
        globals()["SPEC_GIVEN"] = True
        argv = argv[:i] + argv[i + 2:]
        if SPEC not in SPECS:
            print(f"unknown spec mode {SPEC}; one of {SPECS}")
            return 1
    if len(argv) < 2 or argv[1] in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    cmd = argv[1]
    if cmd == "selftest":
        ok, lines = selftest()
        print("\n".join(lines))
        print(f"SELF-TEST ({'spec ' + SPEC}) " + ("PASSED" if ok else "FAILED"))
        return 0 if ok else 1
    if cmd == "recompute":
        S = load_summary(argv[2])
        log = []
        seats = recompute_run(S, log)
        _print_seats(seats, headline_of(seats), headline_of(seats, uniform=True))
        print("log:")
        for x in log:
            print("  " + x)
        print(json.dumps({"headline": headline_of(seats), "headline_uniform": headline_of(seats, uniform=True)}))
        return 0
    if cmd == "patch":
        S = load_summary(argv[2])
        P = json.load(open(argv[3]))
        if isinstance(P, dict):
            P = P.get("changed_inputs", P.get("joint_changed_inputs", []))
        h0, _ = run_headline_from_summary(S)
        S1, ok, why, notes = apply_patches(S, P)
        if not ok:
            print(json.dumps({"accepted": False, "reasons": why}, indent=1))
            return 2
        log = []
        h1, seats = run_headline_from_summary(S1, log)
        _print_seats(seats, h1, headline_of(seats, uniform=True))
        print(json.dumps({"accepted": True, "notes": notes, "blind_headline": h0, "patched_headline": h1,
                          "delta": (h1 - h0) if (h1 is not None and h0 is not None) else None}, indent=1))
        return 0
    if cmd == "verify":
        S = load_summary(argv[2])
        V = load_verification(argv[3])
        lg = []
        fo = fold_run(S, V, lg)
        print(json.dumps({"blind_headline": fo["blind"], "adjusted_headline": fo["adjusted"], "joint_delta": fo["joint_delta"],
                          "mode": fo["mode"], "joint_reasons": fo["joint_reasons"],
                          "findings": [{k: f[k] for k in ("finding", "ruling", "status", "standalone_delta", "reasons")}
                                       for f in fo["findings"]], "log": lg}, indent=1, default=str))
        return 0
    if cmd == "rebase":
        if not v10():
            print("rebase is a v10 command (T1)")
            return 1
        S = load_summary(argv[2])
        P, why = rebase_patches(S, argv[3])
        if P is None:
            print(json.dumps({"changed_inputs": [], "reason": why}, indent=1))
            return 2
        S1, ok, why2, notes = apply_patches(S, P)
        h0, _ = run_headline_from_summary(S)
        h1, _ = run_headline_from_summary(S1, []) if ok else (None, None)
        print(json.dumps({"changed_inputs": P, "accepted": ok, "reasons": why2, "notes": notes,
                          "approximation": "every tree value scaled by fair_value_macro_base / fair_value",
                          "blind_headline": h0, "patched_headline": h1,
                          "delta": (h1 - h0) if (h0 is not None and h1 is not None) else None}, indent=1))
        return 0 if ok else 2
    if cmd == "undebt":
        if not v10():
            print("undebt is a v10 command (T2)")
            return 1
        S = load_summary(argv[2])
        P, why = undebt_patches(S)
        if P is None:
            print(json.dumps({"changed_inputs": [], "reason": why}, indent=1))
            return 2
        S1, ok, why2, notes = apply_patches(S, P)
        h0, _ = run_headline_from_summary(S)
        h1, _ = run_headline_from_summary(S1, []) if ok else (None, None)
        print(json.dumps({"changed_inputs": P, "accepted": ok, "reasons": why2, "notes": notes,
                          "blind_headline": h0, "patched_headline": h1,
                          "delta": (h1 - h0) if (h0 is not None and h1 is not None) else None}, indent=1))
        return 0 if ok else 2
    if cmd in ("stage3", "stage5"):
        cfg = json.load(open(argv[2]))
        if cfg.get("spec_version") is not None:
            if cfg["spec_version"] not in SPECS:
                print(f"config spec_version {cfg['spec_version']} unknown; one of {SPECS}")
                return 1
            if SPEC_GIVEN and cfg["spec_version"] != SPEC:
                print(f"--spec {SPEC} conflicts with the config's spec_version {cfg['spec_version']}")
                return 1
            SPEC = cfg["spec_version"]
        out = argv[3]
        r = stage3(cfg, out) if cmd == "stage3" else stage5(cfg, out)
        print(f"{cmd} written to {out}")
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
