# Mature recommendation analysis — 2026-10-12

This report covers **367 of 740 recommendations** (49.6%) with a 7-day reading. Unlabelled rows are excluded, not treated as failures.

## Score cohorts

| Score | Mature repos | Breakout rate | Median growth | Note |
|---|---:|---:|---:|---|
| 90–100 | 287 | 17.1% | 39.4% |  |
| 80–89 | 77 | 20.8% | 59.6% |  |
| 70–79 | 0 | — | — |  |
| 60–69 | 3 | 0.0% | 40.2% | thin (n<20) |
| <60 | 0 | — | — |  |

## Source cohorts

| Cohort | Mature repos | Breakout rate | Median growth | Note |
|---|---:|---:|---:|---|
| ai-trending | 11 | 36.4% | 94.3% | thin (n<20) |
| hf-papers | 6 | 33.3% | 56.3% | thin (n<20) |
| hn | 14 | 14.3% | 45.6% | thin (n<20) |
| rising | 11 | 27.3% | 118.5% | thin (n<20) |
| search | 164 | 28.7% | 110.1% |  |
| search+ai-trending | 9 | 22.2% | 77.3% | thin (n<20) |
| search+ai-trending+hf-papers | 1 | 0.0% | 77.0% | thin (n<20) |
| search+hf-papers | 2 | 0.0% | 70.0% | thin (n<20) |
| search+rising | 5 | 40.0% | 129.0% | thin (n<20) |
| trending | 143 | 2.1% | 8.3% |  |
| trending+hn | 1 | 0.0% | 5.2% | thin (n<20) |

## Recommendation-time age cohorts

| Cohort | Mature repos | Breakout rate | Median growth | Note |
|---|---:|---:|---:|---|
| 0–2d | 158 | 30.4% | 119.4% |  |
| 3–13d | 58 | 22.4% | 89.5% |  |
| 14–59d | 3 | 0.0% | 26.5% | thin (n<20) |
| 60d+ | 148 | 2.7% | 8.6% |  |

## Recommendation-time star cohorts

| Cohort | Mature repos | Breakout rate | Median growth | Note |
|---|---:|---:|---:|---|
| 0–99 | 7 | 28.6% | 164.4% | thin (n<20) |
| 100–999 | 204 | 28.4% | 101.2% |  |
| 1k–9.9k | 60 | 5.0% | 22.8% |  |
| 10k+ | 96 | 2.1% | 5.2% |  |

## Interpretation guardrails

- Mature coverage is **49.6%**; the remaining 373 recommendations are unknown, not negative labels.
- A cohort below 20 mature repos is marked thin and is not a basis for changing weights or adding a source.
- Source cohorts are descriptive associations. Age and starting-star tables reduce obvious confounding but do not establish incremental or causal source value.
