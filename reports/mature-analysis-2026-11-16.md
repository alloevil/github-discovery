# Mature recommendation analysis — 2026-11-16

This report covers **665 of 1053 recommendations** (63.2%) with a 7-day reading. Unlabelled rows are excluded, not treated as failures.

## Score cohorts

| Score | Mature repos | Breakout rate | Median growth | Note |
|---|---:|---:|---:|---|
| 90–100 | 527 | 19.5% | 55.5% |  |
| 80–89 | 134 | 17.9% | 53.4% |  |
| 70–79 | 2 | 0.0% | 13.8% | thin (n<20) |
| 60–69 | 2 | 0.0% | 42.5% | thin (n<20) |
| <60 | 0 | — | — |  |

## Source cohorts

| Cohort | Mature repos | Breakout rate | Median growth | Note |
|---|---:|---:|---:|---|
| ai-trending | 21 | 23.8% | 70.6% |  |
| hf-papers | 8 | 25.0% | 69.5% | thin (n<20) |
| hn | 22 | 9.1% | 51.3% |  |
| hn+hf-papers | 1 | 100.0% | 290.8% | thin (n<20) |
| rising | 18 | 38.9% | 158.6% | thin (n<20) |
| search | 352 | 26.1% | 96.8% |  |
| search+ai-trending | 21 | 23.8% | 132.5% |  |
| search+ai-trending+hf-papers | 1 | 0.0% | 77.0% | thin (n<20) |
| search+hf-papers | 3 | 0.0% | 77.7% | thin (n<20) |
| search+hn | 2 | 0.0% | 71.5% | thin (n<20) |
| search+rising | 9 | 55.6% | 264.4% | thin (n<20) |
| trending | 206 | 3.9% | 10.0% |  |
| trending+hn | 1 | 0.0% | 5.2% | thin (n<20) |

## Recommendation-time age cohorts

| Cohort | Mature repos | Breakout rate | Median growth | Note |
|---|---:|---:|---:|---|
| 0–2d | 323 | 29.1% | 102.9% |  |
| 3–13d | 120 | 19.2% | 78.1% |  |
| 14–59d | 8 | 12.5% | 77.8% | thin (n<20) |
| 60d+ | 214 | 4.2% | 10.0% |  |

## Recommendation-time star cohorts

| Cohort | Mature repos | Breakout rate | Median growth | Note |
|---|---:|---:|---:|---|
| 0–99 | 11 | 27.3% | 102.9% | thin (n<20) |
| 100–999 | 398 | 26.6% | 94.2% |  |
| 1k–9.9k | 115 | 12.2% | 44.5% |  |
| 10k+ | 141 | 2.8% | 6.3% |  |

## Interpretation guardrails

- Mature coverage is **63.2%**; the remaining 388 recommendations are unknown, not negative labels.
- A cohort below 20 mature repos is marked thin and is not a basis for changing weights or adding a source.
- Source cohorts are descriptive associations. Age and starting-star tables reduce obvious confounding but do not establish incremental or causal source value.
