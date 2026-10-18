**Published BUY (trimmed mean of adjusted headlines): 238.946472 USD per share.** Blind intermediate: 237.515195.

Interval: 234.548415 to 243.344528 (half-width 4.398057 = t(0.90,6) 1.439756 × s 8.640064 ÷ √8). *80% confidence interval for this pipeline's expected BUY on these packs, with this model and this orchestration. A fresh execution's figure is expected within a range √2 wider. Neither range covers the items in the sensitivity ledger.* Replication range: 232.726680 to 245.166263.

Blind intermediate interval: 234.044759 to 240.985631 (s 6.817737).

Committee fair value (equal-weighted mean of weighted FV of headline seats, retained runs): 396.973452 (blind: 396.094599).

Retained runs (published): u7, g9, m4, g8, f8, n7. Retained runs (blind): w6, g9, m4, g8, f8, n7.

Descriptive: equal-weighted mean 237.522345; median 239.060623.

| run | dossier | blind | adjusted | joint delta | weighted FV (blind) | weighted FV (adjusted) | fold mode |
|---|---|---|---|---|---|---|---|
| u7 | A | 248.2477 | 242.9822 | -5.2655 | 398.6371 | 389.6452 | joint_changed_inputs |
| w6 | A | 243.4999 | 249.7279 | +6.2280 | 391.9106 | 405.4145 | joint_changed_inputs |
| g9 | A | 236.8807 | 239.0334 | +2.1526 | 403.4197 | 406.8436 | joint_changed_inputs |
| m4 | A | 240.7214 | 239.0879 | -1.6335 | 403.6368 | 400.5453 | joint_changed_inputs |
| g8 | B | 238.2469 | 242.2956 | +4.0486 | 403.6498 | 410.8560 | joint_changed_inputs |
| f8 | B | 232.4207 | 232.4207 | +0.0000 | 389.5916 | 389.5916 | no patches applied |
| d8 | B | 218.7237 | 216.7720 | -1.9516 | 369.7071 | 366.6832 | joint_changed_inputs |
| n7 | B | 233.3215 | 237.8591 | +4.5376 | 384.3590 | 384.3590 | joint_changed_inputs |

**Leave-one-out point estimates** (descriptive):

| run left out | point | change |
|---|---|---|
| u7 | 238.1393 | -0.8071 |
| w6 | 238.1393 | -0.8071 |
| g9 | 238.9291 | -0.0174 |
| m4 | 238.9182 | -0.0283 |
| g8 | 238.2767 | -0.6698 |
| f8 | 240.2516 | +1.3052 |
| d8 | 240.2516 | +1.3052 |
| n7 | 239.1639 | +0.2175 |

Most influential run: f8.

**Sensitivity ledger (not in the interval).** Each row: change in the published BUY, USD per share and in s_w units (s_w = 8.6401, adjusted headlines).

| row | counterfactual point | change | change (s_w) | note |
|---|---|---|---|---|
| Break probability −5pp on every headline seat | 251.2006 | +12.2541 | +1.418 |  |
| Break probability +5pp on every headline seat | 224.0635 | -14.8829 | -1.723 |  |
| Valuation date rolled to the pack date | 238.9465 | +0.0000 | +0.000 |  |
| Share-count date | 238.9465 | +0.0000 | +0.000 |  |
| Valuation date and share-count date (both) | 238.9465 | +0.0000 | +0.000 |  |
| Denominator on the period-weighted count instead of the per-share count | 235.5284 | -3.4180 | -0.396 |  |
| Acquisitions: every seat on the organic basis | 238.9465 | +0.0000 | +0.000 |  |
| Acquisitions: every seat including acquisitions | 238.9465 | +0.0000 | +0.000 |  |
| Risk-free +50bp | 222.3137 | -16.6327 | -1.925 |  |
| Published figure without the single finding whose removal moves it most | 238.1902 | -0.7563 | -0.088 | run n7, finding 2 |
| Point rule: equal-weighted mean | 237.5223 | -1.4241 | -0.165 |  |
| Point rule: median | 239.0606 | +0.1142 | +0.013 |  |
| Memory control: β̂ₖ and β̂ⱼ with 90% CIs, and any flag | — | β̂ₖ -0.0128 (90% CI -0.0323 to +0.0066); β̂ⱼ +0.0261 (90% CI -0.0340 to +0.0862) | permutation p 0.3888888888888889 (576 permutations) | flag NONE |
| Dossier contrast: t, p and camp means | — | t = +1.6975, df 6, p = 0.1405 | camp means A 242.7078; B 232.3369 | adjusted headlines |

Unmeasured: dossier-builder variance (1 df with two dossiers); orchestrator variance (Stage 7 not run); model and harness effects.
