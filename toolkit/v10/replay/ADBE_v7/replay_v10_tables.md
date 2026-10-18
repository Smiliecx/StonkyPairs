**Published BUY (trimmed mean of adjusted headlines): 248.174772 USD per share.** Blind intermediate: 247.149415.

Interval: 243.178341 to 253.171202 (half-width 4.996430 = t(0.90,6) 1.439756 × s 9.815581 ÷ √8). *80% confidence interval for this pipeline's expected BUY on these packs, with this model and this orchestration. A fresh execution's figure is expected within a range √2 wider. Neither range covers the items in the sensitivity ledger.* Replication range: 241.108752 to 255.240792.

Blind intermediate interval: 243.238829 to 251.060001 (s 7.682419).

Committee fair value (equal-weighted mean of weighted FV of headline seats, retained runs): 410.208176 (blind: 410.379660).

Retained runs (published): u7, g9, m4, g8, f8, n7. Retained runs (blind): w6, g9, m4, g8, f8, n7.

Descriptive: equal-weighted mean 246.583860; median 249.291042.

| run | dossier | blind | adjusted | joint delta | weighted FV (blind) | weighted FV (adjusted) | fold mode |
|---|---|---|---|---|---|---|---|
| u7 | A | 258.1439 | 251.8173 | -6.3266 | 410.4182 | 400.0179 | joint_changed_inputs |
| w6 | A | 251.0547 | 259.1434 | +8.0886 | 410.0604 | 425.5821 | joint_changed_inputs |
| g9 | A | 249.9387 | 252.3613 | +2.4226 | 420.0286 | 424.0750 | joint_changed_inputs |
| m4 | A | 246.7327 | 244.7280 | -2.0047 | 416.0872 | 412.4970 | joint_changed_inputs |
| g8 | B | 248.9001 | 253.8718 | +4.9717 | 417.0282 | 425.5856 | joint_changed_inputs |
| f8 | B | 246.7648 | 246.7648 | +0.0000 | 403.5937 | 403.5937 | no patches applied |
| d8 | B | 227.3138 | 224.4789 | -2.8349 | 381.5915 | 377.1648 | joint_changed_inputs |
| n7 | B | 239.5054 | 239.5054 | +0.0000 | 395.4798 | 395.4798 | joint_changed_inputs |

**Leave-one-out point estimates** (descriptive):

| run left out | point | change |
|---|---|---|
| u7 | 247.4463 | -0.7285 |
| w6 | 247.0354 | -1.1394 |
| g9 | 247.3375 | -0.8373 |
| m4 | 248.8641 | +0.6894 |
| g8 | 247.0354 | -1.1394 |
| f8 | 248.4568 | +0.2820 |
| d8 | 249.9086 | +1.7339 |
| n7 | 249.9086 | +1.7339 |

Most influential run: d8.

**Sensitivity ledger (not in the interval).** Each row: change in the published BUY, USD per share and in s_w units (s_w = 9.8156, adjusted headlines).

| row | counterfactual point | change | change (s_w) | note |
|---|---|---|---|---|
| Break probability −5pp on every headline seat | 260.6099 | +12.4351 | +1.267 |  |
| Break probability +5pp on every headline seat | 232.8195 | -15.3553 | -1.564 |  |
| Valuation date rolled to the pack date | 248.1748 | +0.0000 | +0.000 |  |
| Share-count date | 248.1748 | +0.0000 | +0.000 |  |
| Valuation date and share-count date (both) | 248.1748 | +0.0000 | +0.000 |  |
| Denominator on the period-weighted count instead of the per-share count | 244.6215 | -3.5533 | -0.362 |  |
| Acquisitions: every seat on the organic basis | 248.1748 | +0.0000 | +0.000 |  |
| Acquisitions: every seat including acquisitions | 248.1748 | +0.0000 | +0.000 |  |
| Alternative denominator: every seat on its run's alternative denominator | n/a | n/a | n/a | no headline seat reports fair_value_alternative_denominator; mean absolute per-run change 0.0000; runs above / below / none 1 / 5 / 0 (retained); seats valued 0 of 42 |
| Debt: net claims deducted again (the v9 count) | n/a | n/a | n/a | no retained run reports net claims; runs with net claims (retained) 0 of 6; the v9 count, exact for the claims as reported |
| Risk-free +50bp | 230.4415 | -17.7333 | -1.807 |  |
| Published figure without the single finding whose removal moves it most | 247.4496 | -0.7252 | -0.074 | run g8, finding 2 |
| Point rule: equal-weighted mean | 246.5839 | -1.5909 | -0.162 |  |
| Point rule: median | 249.2910 | +1.1163 | +0.114 |  |
| Dossier contrast: t, p and camp means | — | t = +1.5643, df 6, p = 0.1688 | camp means A 252.0125; B 241.1552 | adjusted headlines |

**Margin-rule alternatives (policy; not ledger rows; not in the interval; never averaged).** Each is the trimmed mean of the runs' own-weight headlines under that rule, on the Stage-5b patched summaries; constants fixed in the spec.

| rule | point | change against the published BUY | change (s_w) | blind point | implied expected upside ÷ downside (median over retained runs) |
|---|---|---|---|---|---|
| Published BUY (quality premium + p·L) | 248.1748 | — | — | 247.1494 | 5.89 |
| Step tiers (SPEC v7.1 rule) | 248.6143 | +0.4395 | +0.045 | 248.6968 | 5.97 |
| EV rule, tuned Victor (0.67 × tree expected value) | 238.7895 | −9.3853 | −0.956 | 237.1739 | 6.75 |
| Expectile rule, tuned Max (expected upside 7.75 × expected downside) | 231.9404 | −16.2344 | −1.654 | 230.4216 | 7.29 |
| EV × (1 − quality premium) (ledger only) | 258.3291 | +10.1544 | +1.035 | 256.3454 | 5.20 |

Unmeasured: dossier-builder variance (1 df with two dossiers); orchestrator variance (Stage 7 not run); model and harness effects.
