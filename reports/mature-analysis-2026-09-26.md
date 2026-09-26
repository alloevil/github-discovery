# Mature recommendation analysis — 2026-09-26

This report covers **212 of 579 recommendations** (36.6%) with a 7-day reading. Unlabelled rows are excluded, not treated as failures.

## Score cohorts

| Score | Mature repos | Breakout rate | Median growth | Note |
|---|---:|---:|---:|---|
| 90–100 | 171 | 9.9% | 32.8% |  |
| 80–89 | 41 | 22.0% | 44.4% |  |
| 70–79 | 0 | — | — |  |
| 60–69 | 0 | — | — |  |
| <60 | 0 | — | — |  |

## Source cohorts

| Source combination | Mature repos | Breakout rate | Median growth | Note |
|---|---:|---:|---:|---|
| ai-trending | 4 | 25.0% | 53.6% | thin (n<20) |
| hf-papers | 3 | 0.0% | 53.0% | thin (n<20) |
| hn | 8 | 25.0% | 40.1% | thin (n<20) |
| rising | 4 | 75.0% | 544.0% | thin (n<20) |
| search | 78 | 23.1% | 105.8% |  |
| search+ai-trending | 2 | 50.0% | 200.6% | thin (n<20) |
| search+ai-trending+hf-papers | 1 | 0.0% | 77.0% | thin (n<20) |
| search+hf-papers | 2 | 0.0% | 70.0% | thin (n<20) |
| search+rising | 4 | 25.0% | 85.8% | thin (n<20) |
| trending | 106 | 0.0% | 7.4% |  |

## Interpretation guardrails

- Mature coverage is **36.6%**; the remaining 367 recommendations are unknown, not negative labels.
- A cohort below 20 mature repos is marked thin and is not a basis for changing weights or adding a source.
- Source cohorts describe association, not incremental causal value; overlap and candidate-pool exposure are not controlled here.
