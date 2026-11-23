# Mature recommendation analysis — 2026-11-23

This report covers **721 of 1119 recommendations** (64.4%) with a 7-day reading. Unlabelled rows are excluded, not treated as failures.

## Score cohorts

| Score | Mature repos | Breakout rate | Median growth | Note |
|---|---:|---:|---:|---|
| 90–100 | 582 | 19.4% | 54.8% |  |
| 80–89 | 135 | 17.8% | 54.1% |  |
| 70–79 | 2 | 0.0% | 13.8% | thin (n<20) |
| 60–69 | 2 | 0.0% | 42.5% | thin (n<20) |
| <60 | 0 | — | — |  |

## Source cohorts

| Cohort | Mature repos | Breakout rate | Median growth | Note |
|---|---:|---:|---:|---|
| ai-trending | 28 | 21.4% | 39.9% |  |
| hf-papers | 8 | 25.0% | 69.5% | thin (n<20) |
| hn | 27 | 14.8% | 51.2% |  |
| hn+hf-papers | 2 | 50.0% | 176.2% | thin (n<20) |
| rising | 19 | 36.8% | 152.8% | thin (n<20) |
| search | 377 | 25.5% | 96.2% |  |
| search+ai-trending | 23 | 26.1% | 132.5% |  |
| search+ai-trending+hf-papers | 1 | 0.0% | 77.0% | thin (n<20) |
| search+hf-papers | 3 | 0.0% | 77.7% | thin (n<20) |
| search+hn | 3 | 33.3% | 97.9% | thin (n<20) |
| search+rising | 10 | 50.0% | 196.7% | thin (n<20) |
| trending | 219 | 4.1% | 10.5% |  |
| trending+hn | 1 | 0.0% | 5.2% | thin (n<20) |

## Recommendation-time age cohorts

| Cohort | Mature repos | Breakout rate | Median growth | Note |
|---|---:|---:|---:|---|
| 0–2d | 351 | 29.1% | 97.4% |  |
| 3–13d | 131 | 17.6% | 77.7% |  |
| 14–59d | 11 | 9.1% | 61.7% | thin (n<20) |
| 60d+ | 228 | 4.8% | 10.6% |  |

## Recommendation-time star cohorts

| Cohort | Mature repos | Breakout rate | Median growth | Note |
|---|---:|---:|---:|---|
| 0–99 | 11 | 27.3% | 102.9% | thin (n<20) |
| 100–999 | 439 | 26.0% | 89.7% |  |
| 1k–9.9k | 122 | 13.1% | 47.2% |  |
| 10k+ | 149 | 2.7% | 6.3% |  |

## Interpretation guardrails

- Mature coverage is **64.4%**; the remaining 398 recommendations are unknown, not negative labels.
- A cohort below 20 mature repos is marked thin and is not a basis for changing weights or adding a source.
- Source cohorts are descriptive associations. Age and starting-star tables reduce obvious confounding but do not establish incremental or causal source value.
