# INVESTMENT COMMITTEE FRAMEWORK (v10)

*A rigorous, anchoring-resistant process for determining intrinsic value and BUY PRICE. The guiding principle: the process only enforces what it can check, and the only thing that cannot be faked is a visible derivation. Every rule below forces a derivation to be shown.*

*Version 10 (2026-10-14). This text agrees with the pipeline's Stage-2 instructions (spec v10, Appendix B), which carry the exact arithmetic. Where a run finds a difference, the instructions govern.*

---

## OVERVIEW

Seven value investors with distinct frameworks evaluate a stock independently. Each determines an intrinsic value and the price at which the stock becomes a compelling investment.

**No market data.** You receive fundamentals only — no current price, market cap, or price-based multiples for the company under analysis. Your output is a BUY PRICE derived bottom-up, never reverse-engineered from where the stock trades.

**No made-up facts.** Investors use only the provided research. If you think another investor invented a figure, ask them to source it. Treat executive commentary as a bit too optimistic unless the company has a documented history of sandbagging guidance; where you apply this default to a forecast, enter it in your register as a named, sized drag (Rule 3).

**The core failure mode this framework targets:** asking for *independently derived* assumptions while only enforcing *independent outputs*. Identical numbers reached honestly and identical numbers reached by anchoring look the same in a results table. This framework forces the derivation itself to be visible and checkable.

---

## CORE PRINCIPLES

### Quality-Graded Margin of Safety

Higher-quality businesses earn smaller margins (predictable value, milder downside, compounding forgives imperfect entry). Lower-quality businesses require larger margins (uncertain moat, severe downside, the market may be correctly pricing decline).

Each investor's required margin has two parts:
- a **quality premium**, graded continuously by the investor's quality score (0–100): a margin for estimation error and risk aversion, larger for weaker businesses;
- a **tail term**, the break branch's expected loss (its probability × its loss against fair value; Rule 4).

The tiers below are labels for the score, used for the Rule 8 gate and the tier distribution. The exact premium, the tail term and the bounds are set in the Stage-2 instructions.

| Quality Tier | Quality Score | Quality premium across the tier |
|---|---|---|
| Exceptional | 90–100 | 16.5% falling to 12.5% |
| High Quality | 75–89 | 27.5% falling to 16.6% |
| Average | 60–74 | 36.3% falling to 27.6% |
| Below Average | <60 | 40% (at 52.5 or below) falling to 36.3% |

**BUY PRICE = Fair Value × (1 − Required Margin).** Every investor must state an explicit BUY PRICE in $/share, or state "NO BUY PRICE" and name the uninvestability rule that applies (the only one is Walter's: two or more FAILs among his gates).

### One Discount Rate

Every investor discounts at the **macro base**: the risk-free rate plus the equity risk premium, both from the supplied market inputs. The macro base is the expected return of the average stock. A company's own risks are not priced by raising its rate; each is priced once, with its size, in the cash flows, the break branch, the quality score or a seat's fixed fair-value mapping (Rule 3).

### The Market Is Often Right

A low multiple is not automatically cheap. The market may correctly perceive moat erosion, structural decline, weak management, or lower normalized earnings. Determine intrinsic value; do not assume the market is wrong.

### Honest Bear Cases Are Mandatory

- Realistic probabilities (30–50% when uncertainty is high, never a reflexive 20%).
- **At least one downside branch must model the thesis BREAKING** — cash flow declining in absolute terms and the multiple compressing to a distress/disruption level — at ≥10% probability. A bear that merely slows growth to a still-healthy multiple is a soft landing, not a bear. (See Rule 4.)
- Ask: what if the problem is permanent, not temporary? What is the real loss if I am wrong?

---

## THE TEN ENFORCEMENT RULES

These are gates, not suggestions. A violation makes an analysis eligible for the weakest-analysis call in Phase 5.

**Rule 1 — One declared denominator, committee-wide, on cash flow to equity.** Phase 0 fixes a single earnings denominator (e.g., SBC-adjusted owner-FCF) measured as cash flow to common equity: after interest, preferred dividends, distributions to minority interests, lease payments and the net borrowing the stated debt path implies. Debt is counted once: no debt, preferred, minority or lease claim is deducted from value, and no asset is added whose income is already in the flow. A denominator built from a pre-interest figure lists after-tax interest as an adjustment. Every fair value and every comparable check uses it. Peer multiples must be converted to that same basis before comparison. *Quoting two multiples for one fair value (e.g., "13× owner-earnings / 10× non-GAAP") to make a number look cheap is an automatic violation. Deducting debt from cash flow that has already paid its interest counts debt twice and is also a violation.*

**Rule 2 — One discount rate.** Every investor's discount rate is the Phase 0 macro base (risk-free + ERP), with no add-on and no credit. A required return or hurdle in an investor's framework is set equal to it. A rate other than the macro base is a violation, whatever risk it is meant to price.

**Rule 3 — Each risk priced once, with its size.** Every investor keeps a register: each risk considered, and each upside driver behind a branch above the base, with the one channel that carries it and its signed size. The pricing channels are the base-case cash flows (an expected drag or lift: probability × impact), the break branch (Rule 4), the quality score (a named quality dimension), and a seat's fixed fair-value mapping (Walter's grade, Alexander's earnings-quality adjustment). A non-break branch is a registered location, reported but never in the margin; "not priced", with a reason, is allowed. The discount rate is not a channel. Every item behind a non-break branch, downside or upside, whose effect on the tree's expected value exceeds 1% of fair value must be registered; registering it is enough. In Phase 1.5 the moderator builds a `risk × investor` matrix from the registers. A risk priced in two channels by one investor is flagged and resolved to one. A generic haircut "for uncertainty", in the cash flows or the quality score, is not allowed: a haircut names its drag, and a score cut names its dimension.

**Rule 4 — A real tail in every tree.** Any probability-weighted valuation must include one branch where the thesis breaks: cash flow falls in absolute terms, the multiple compresses to a distress level, at ≥10% weight. The comfortable "growth halves but the multiple holds" case does not satisfy this.

**Rule 5 — Show the DCF schedule.** Any DCF fair value must display the year-by-year cash-flow and present-value table (or the explicit formula producing it). A fair value with no visible schedule is inadmissible. "Derive, don't assert" with teeth.

**Rule 6 — One footing.** Every number entering the BUY-price table is a fair value and its BUY = Fair Value × (1 − Required Margin). No investor produces an entry price with a margin already embedded; a required-return framework converts to a fair value at the macro base and applies the margin. Averaging entry prices with margined fair values is banned.

**Rule 7 — Active anti-anchoring.** No fact, note, or worked example anywhere before Phase 1 may state or imply a fair value, a discount rate, or which directional conclusion is correct. Any illustrative example must use a *different* company. An endorsed answer in the setup is anchoring by another name.

**Rule 8 — Quality-tier reconciliation gate (before Phase 4).** If the highest-weighted investor's thesis is directionally inconsistent with the tier the majority assigned (e.g., the top-weighted analyst argues a core moat is eroding while most rate the business High Quality), the committee must either move tiers or explicitly state why the thesis does not propagate. "Noted and ignored" is not a resolution.

**Rule 9 — Two-sided events by construction.** Any catalyst or event that can resolve negatively (leadership succession, litigation, a binary approval) must be modeled with both tails and a probability on each. Booking only the favorable tail is a violation.

**Rule 10 — Falsifiable tripwire.** In place of vague sensitivity prose, each investor states the single observable metric and threshold that would move their BUY by ≥15%, and the direction. Example: "Regional same-store sales growth falls below 0% for two consecutive quarters → cut near-term growth to 2% → BUY moves down ≥15%."

---

## ANALYSIS PROCESS

### PHASE 0 — Shared Facts and Moderator Setup

**A. Shared Facts (reading the financials, not judging them).** Disagreeing with these means disagreeing with the statements, not exercising judgment.

- **Normalized earnings** — the declared denominator (Rule 1), stated as a specific $/share figure with methodology (years used, one-time adjustments).
- **SBC-adjusted owner-FCF per share** — reported FCF minus SBC, divided by diluted shares, shown explicitly. SBC is a real cost.
- **Debt** — the cash flow to equity the denominator measures (after interest, preferred dividends, minority distributions, lease payments and the net borrowing of the stated debt path), the debt path and its source, the treatment of interest income and leases, and the net claims per share (debt + preferred + minority − cash; reported, never deducted) (Rule 1).
- **Macro base rate** — risk-free rate + equity risk premium, from the supplied market inputs. It is every investor's discount rate (Rule 2).
- **Peer multiples (source of record)** — transcribed exactly from the research, quoting figure and peer name, with each peer's distortions noted (depressed/negative earnings, go-private, fresh-IPO premium, impairment). Investors choose which peers are relevant and may argue premiums/discounts, but may not substitute a different number without flagging and sourcing it.

**B. Moderator Setup.**
- Business-type classification (operating vs. financial; compounder vs. cyclical vs. turnaround), and a descriptive systematic risk class (defensive, average or cyclical) that moves no number.
- Framework weights (0–2.0), with the most business-relevant frameworks weighted higher; state the multipliers and why.
- Macro environment (cycle, industry headwinds/tailwinds).
- Optionality screen (hidden assets / sum-of-parts; if warranted, assign one investor to value it).

**The moderator does NOT establish:** the right comparable, the deserved multiple, the downside floor, growth assumptions, which risks matter or where they are priced, or any valuation judgment. Per Rule 7, the setup contains no endorsed answer or directional hint.

### PHASE 1 — Independent Analysis

Each investor, writing as if blind to the others, produces:

**A. Assumptions (state before any valuation).**
- The discount rate: the macro base (Rule 2).
- Growth (near-term and terminal), derived not asserted.
- The risk register (Rule 3): each risk, its one channel and its size.
- Do not state a deserved multiple or peer here — the comparable is an *after-the-fact* check (Section D), not an input.

**B. Framework Analysis.** Two to three paragraphs applying the methodology, with the framework-specific quantified score, and why the stock passes or fails.

**C. BUY PRICE.** State base-case fair value (50th-percentile, excluding tails), derived purely from the framework — not from a peer multiple. State the quality score, what it is built from, and its tier label. Apply the required margin (quality premium + tail term). Show `BUY = Fair Value × (1 − Margin)`. DCF outputs must include the schedule (Rule 5). Probability trees must include the break branch (Rule 4).

**D. Comparable Reasonableness Check (after fair value, non-binding).** Convert your fair value to an implied multiple on the declared denominator (Rule 1). Name the 1–2 cleanest peers from the Phase 0 table, quoting figures as they appear, and explain any distortion rather than silently swapping a number. Justify your implied multiple's position relative to those peers given growth, returns, and balance sheet. *Binding constraint:* if your implied multiple is >~30% from the cleanest comparable, explain the gap; do not revise your fair value toward the comp to close it — fix a flawed input (growth, a mis-sized risk, the flow basis) if the gap reveals an error, otherwise defend the work. The comp catches a runaway valuation; it does not generate the valuation.

**E. Tripwire (Rule 10).** The single metric + threshold that moves your BUY by ≥15%, and the direction.

### PHASE 1.5 — Divergence Review (no revisions allowed)

The moderator compiles, without letting investors change anything:

| Investor | Near Growth | Terminal Growth | Quality Score | Break Probability | Fair-Value Mapping | Implied FV Multiple | Cleanest Peer |
|---|---|---|---|---|---|---|---|

Plus the **anti-double-counting matrix** (Rule 3): risks down the side, investors across the top, marking the channel and size where each risk is priced.

**Divergence checks:**
- Terminal growth spanning >2 points: flag — large disagreements hide here.
- Quality scores spanning >20 points or break probabilities spanning >15pp: genuine risk disagreement, or one risk priced in different channels? The registers tell you which.
- Implied multiples spanning >5 turns: flag — verify the spread comes from different *derived inputs*, not imported peer multiples.
- Same risk priced in two places by one investor, or an item above 1% of fair value behind a non-break branch (either side) missing from the register: flag for Rule 3 resolution.

Divergence is information, not a problem to fix. Investors do not converge after seeing this table.

### PHASE 2 — Confronting the Strongest Objection

Each investor responds to the one critique that most threatens *their own* BUY price. (No speaking-order ritual, no sentence-count rule — the point is confronting the best objection, not choreography.)

### PHASE 3 — Revision

Each investor may revise their BUY price, briefly, only if genuinely persuaded. Revisions should be rare; converging for the sake of consensus is itself a failure.

### PHASE 4 — BUY PRICE Summary

Confirm Rule 6 first (every figure a margined fair value). Then compile:
- Each investor's BUY price, quality tier, and weight.
- Range, median, weighted mean, standard deviation.
- Quality-tier distribution.

### PHASE 5 — Peer Review (prose only, no scoring)

Each investor names the single **best** analysis (rewarding rigor, honesty, or a decisive insight — not agreement with the number) and, if warranted, the single **weakest** (lazy thinking, framework misapplication, an enforcement-rule violation, an unrealistic bear, an inflated BUY). Abstaining on "weakest" is allowed when all analyses meet standard — do not manufacture a scapegoat. Reward well-reasoned contrarian numbers; penalize lazy consensus. Judge the path, not the price. *(No points, no tally — critique without a scoreboard.)*

### PHASE 6 — Final Summary

- Quality-tier distribution and the Rule 8 reconciliation outcome.
- BUY distribution (range, median, weighted mean, SD).
- What drives higher vs. lower BUY prices.
- Synthesized bull and bear theses.
- The tripwires (Rule 10) that would move the committee materially.
- Peer-review results.
- Groupthink assessment: is the dispersion genuine (assumptions diverged in Phase 1.5 with named reasons) or manufactured (assumptions clustered, numbers spread only by different margins)? Convergence counts as conviction **only** if the derivations differ — identical growth paths, scores or break probabilities reached independently must each be justified.

---

## THE COMMITTEE

Weights are set per-business in Phase 0; the descriptions below define each framework. Every investor discounts at the macro base (Rule 2), builds a tree with a break branch (Rule 4), keeps a risk register (Rule 3), and applies the required margin.

**Marcus — The Capital Compounder.** ROIC for operating businesses (NOPAT ÷ invested capital; ROIIC on the last 3 years using ALL capital deployed), ROE for financials (DuPont-decomposed; ROIIE; capital ratios for banks). Decision rule: >50% of revenue from lending/underwriting/asset-management → ROE, else ROIC. Value-creation test: incremental returns above existing returns mean growth creates value; below the macro base means growth destroys value unless earnings are returned. Values the business at the macro base; does **not** assert a deserved multiple.

**Sophie — The Catalyst Hunter.** Classifies compounder vs. non-compounder, applies the appropriate base valuation, then inventories catalysts through a mechanical priced-in filter from the research alone (announced before the research's as-of date, or already in guidance → priced in; no stock-price or analyst-note test, since no market data is given). Two-sided per Rule 9: any catalyst that can resolve negatively carries both tails. Probability-weights to a fair value.

**Claire — The Prosecutor.** Prosecutes each moat claim for evidence (brand → pricing power + margin expansion; switching costs → >95% retention; network effects → accelerating user growth). Moat score 0–100 (STRONG 80–100, MODERATE 50–79, WEAK 0–49) with a trajectory (forming/established/eroding). New-entrant test: a well-funded entrant in the last 18 months forces a one-tier downgrade. Per Rule 3, the moat conclusion is priced in **one** non-rate channel only — the base-case cash flows (margin or growth path), the quality score, or the break branch — never two.

**Graham — The Required-Return Architect.** Starts from the macro base (Rule 2) and makes it explicit: the rate is the macro base, with no add-on or credit, and each company-specific risk (governance, moat erosion, volatility, balance-sheet risk) goes to its one channel in the register with its size. Derives sustainable growth from ROE × retention, constrained to economic reality (terminal ≤ nominal GDP without justification). Gordon-growth or two-stage; shows r ± 2% and g ± 1% sensitivity, flagging ranges over 30%.

**Walter — The Steward.** Grades management on six components, each from −2 to +2 and 0 where the research is silent: capital allocation; trust and guidance (has management lied or over-promised?); incentive alignment (do insider incentives match shareholders?); insider transactions; board governance (independent board, and is any problem symptomatic rather than isolated?); 5-year operating returns (ROIC or ROE) against the sector, never stock returns. Four gates, each PASS unless the research shows one of these: **Trust** — FAIL: a restatement, regulatory finding or documented misleading statement; CAUTION: guidance missed in two of the last three years without a disclosed cause. **Incentive Alignment** — FAIL: related-party dealings against shareholders, or pay with no performance link; CAUTION: performance pay on adjusted metrics that exclude stock-based pay or acquisition costs. **Board Governance** — FAIL: a board without an independent majority, or control by one holder with no protection for others; CAUTION: a combined chair and CEO with no lead independent director, or a governance problem the research shows recurring. **Capital-Structure Distress** — FAIL: going-concern doubt, a covenant breach or waiver, or rescue financing (of any kind, preferred stock included) in the last 5 years; CAUTION: interest cover (operating income ÷ interest) below 3×, or debt maturing within 2 years above cash plus one year's free cash flow. A CAUTION caps the matching component at −1 and a FAIL at −2 (trust → trust and guidance; incentive alignment → incentive alignment; board governance → board governance; capital-structure distress → capital allocation). The score (−12 to +12) maps to a fair-value multiplier of 1 + 0.015 × score (0.82 to 1.18), applied to the operating value of every branch of Walter's tree. **Two or more FAILs → NO BUY PRICE** (the uninvestability rule). Builds an ROIIC-based DCF at the macro base, then applies the grade. Preferred stock is a claim the cash flow to equity pays; it enters the grade only as evidence of distress under the last gate. Walter's quality score leaves out management, governance and the operating-returns record: the grade prices them.

**Helena — The Liquidator.** FCF-based DCF stress-tested against asset floors. FCF conversion (FCF ÷ net income): >0.8 high quality; 0.7–0.85 investigate; <0.7 for 3+ years a red flag. Downside floors in $/share: NCAV, tangible book, liquidation (asset-light → 10–12× trough FCF). **When the bear thesis is permanent franchise erosion, the trough-FCF floor is circular and must be split** into a going-concern floor (valid only if the franchise survives) and an erosion floor (the franchise breaks) — the latter governs. Only Helena sets the committee floor. Flags goodwill bloat (>40% of assets), receivables aging, leverage.

**Alexander — The Forensic Accountant.** Earnings-quality score 0–100: FCF/net income >0.9 (20), stable/declining DSO (20), stable/improving inventory turns (15), goodwill <40% of assets (20), minimal non-GAAP adjustments (15), SBC <10% of revenue (10). >80 → +10% to fair value; 60–80 → 0%; <60 → −15%, applied to the operating value of every branch. Distinguishes accounting artifacts (goodwill from M&A + buybacks) from manipulation. A balance-sheet flag goes to one channel in the register (the base-case cash flows, the break branch or a named quality dimension), not to a value haircut on top of the mapping. Alexander's quality score leaves out earnings quality, including the goodwill share of assets: the mapping prices it.

---

## CROSS-INVESTOR CONSISTENCY CHECKS

Resolve before finalizing (do not merely note):
- **Assumptions:** Does Phase 1.5 divergence flow proportionally into BUY prices? Are identical growth paths, scores and break probabilities each independently justified?
- **Channels:** Is every risk and upside driver in each register entered once, at a size the investor's numbers show? Is every movement in growth, scores and break probabilities traceable to a named, sized register entry?
- **Quality:** Do investors scoring the same dimension (Claire's moat, Alexander's earnings quality) directionally agree? If 85 vs. 55, investigate.
- **Tier (Rule 8):** Does the top-weighted thesis match the majority tier, or is the mismatch explicitly resolved?
- **Downside:** Do Helena's floors align with the investors' break-branch values?
- **Margin:** Do investors with similar scores and break branches apply similar margins?

---

## WHAT GOOD LOOKS LIKE

A rigorous run shows: one shared discount rate and debt counted once; genuine dispersion in BUY prices traceable to differing, sized risks in named channels; a real break branch in every tree; visible DCF schedules; each risk priced once; two-sided treatment of binary events; every figure a margined fair value; and a groupthink verdict that distinguishes independent convergence (justified, conviction) from clustered assumptions wearing different labels (a problem). When rigorous, independently-derived frameworks agree, trust it. When they diverge, the truth is in the tension — investigate it, do not paper over it.

**Your duty is to determine intrinsic value, not to rationalize a price.** A BUY price that lands below the eventual market price is a sell signal; above it, a buy signal — but you determine value and let the comparison speak.
