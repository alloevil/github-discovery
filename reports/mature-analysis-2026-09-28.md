# Mature recommendation analysis — 2026-09-28

This report covers **241 of 608 recommendations** (39.6%) with a 7-day reading. Unlabelled rows are excluded, not treated as failures.

## Score cohorts

| Score | Mature repos | Breakout rate | Median growth | Note |
|---|---:|---:|---:|---|
| 90–100 | 199 | 12.1% | 31.3% |  |
| 80–89 | 41 | 22.0% | 44.4% |  |
| 70–79 | 0 | — | — |  |
| 60–69 | 1 | 0.0% | 0.8% | thin (n<20) |
| <60 | 0 | — | — |  |

## Source cohorts

| Cohort | Mature repos | Breakout rate | Median growth | Note |
|---|---:|---:|---:|---|
| ai-trending | 4 | 25.0% | 53.6% | thin (n<20) |
| hf-papers | 4 | 0.0% | 48.2% | thin (n<20) |
| hn | 9 | 22.2% | 43.4% | thin (n<20) |
| rising | 6 | 50.0% | 274.4% | thin (n<20) |
| search | 92 | 26.1% | 109.2% |  |
| search+ai-trending | 3 | 33.3% | 44.4% | thin (n<20) |
| search+ai-trending+hf-papers | 1 | 0.0% | 77.0% | thin (n<20) |
| search+hf-papers | 2 | 0.0% | 70.0% | thin (n<20) |
| search+rising | 5 | 40.0% | 129.0% | thin (n<20) |
| trending | 114 | 0.0% | 7.2% |  |
| trending+hn | 1 | 0.0% | 5.2% | thin (n<20) |

## Recommendation-time age cohorts

| Cohort | Mature repos | Breakout rate | Median growth | Note |
|---|---:|---:|---:|---|
| 0–2d | 90 | 28.9% | 123.0% |  |
| 3–13d | 31 | 19.4% | 77.0% |  |
| 14–59d | 2 | 0.0% | 20.4% | thin (n<20) |
| 60d+ | 118 | 0.8% | 7.6% |  |

## Recommendation-time star cohorts

| Cohort | Mature repos | Breakout rate | Median growth | Note |
|---|---:|---:|---:|---|
| 0–99 | 5 | 40.0% | 169.0% | thin (n<20) |
| 100–999 | 114 | 26.3% | 101.8% |  |
| 1k–9.9k | 42 | 2.4% | 22.6% |  |
| 10k+ | 80 | 0.0% | 5.1% |  |

## Interpretation guardrails

- Mature coverage is **39.6%**; the remaining 367 recommendations are unknown, not negative labels.
- A cohort below 20 mature repos is marked thin and is not a basis for changing weights or adding a source.
- Source cohorts are descriptive associations. Age and starting-star tables reduce obvious confounding but do not establish incremental or causal source value.
