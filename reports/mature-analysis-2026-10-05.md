# Mature recommendation analysis — 2026-10-05

This report covers **304 of 673 recommendations** (45.2%) with a 7-day reading. Unlabelled rows are excluded, not treated as failures.

## Score cohorts

| Score | Mature repos | Breakout rate | Median growth | Note |
|---|---:|---:|---:|---|
| 90–100 | 239 | 15.1% | 32.9% |  |
| 80–89 | 63 | 19.0% | 49.0% |  |
| 70–79 | 0 | — | — |  |
| 60–69 | 2 | 0.0% | 20.5% | thin (n<20) |
| <60 | 0 | — | — |  |

## Source cohorts

| Cohort | Mature repos | Breakout rate | Median growth | Note |
|---|---:|---:|---:|---|
| ai-trending | 8 | 37.5% | 145.7% | thin (n<20) |
| hf-papers | 6 | 33.3% | 56.3% | thin (n<20) |
| hn | 11 | 18.2% | 61.7% | thin (n<20) |
| rising | 10 | 30.0% | 110.9% | thin (n<20) |
| search | 124 | 25.8% | 109.2% |  |
| search+ai-trending | 4 | 50.0% | 161.9% | thin (n<20) |
| search+ai-trending+hf-papers | 1 | 0.0% | 77.0% | thin (n<20) |
| search+hf-papers | 2 | 0.0% | 70.0% | thin (n<20) |
| search+rising | 5 | 40.0% | 129.0% | thin (n<20) |
| trending | 132 | 1.5% | 7.7% |  |
| trending+hn | 1 | 0.0% | 5.2% | thin (n<20) |

## Recommendation-time age cohorts

| Cohort | Mature repos | Breakout rate | Median growth | Note |
|---|---:|---:|---:|---|
| 0–2d | 119 | 30.3% | 120.3% |  |
| 3–13d | 46 | 19.6% | 85.2% |  |
| 14–59d | 3 | 0.0% | 26.5% | thin (n<20) |
| 60d+ | 136 | 2.2% | 8.2% |  |

## Recommendation-time star cohorts

| Cohort | Mature repos | Breakout rate | Median growth | Note |
|---|---:|---:|---:|---|
| 0–99 | 6 | 33.3% | 125.8% | thin (n<20) |
| 100–999 | 156 | 27.6% | 105.7% |  |
| 1k–9.9k | 52 | 3.8% | 21.5% |  |
| 10k+ | 90 | 1.1% | 5.1% |  |

## Interpretation guardrails

- Mature coverage is **45.2%**; the remaining 369 recommendations are unknown, not negative labels.
- A cohort below 20 mature repos is marked thin and is not a basis for changing weights or adding a source.
- Source cohorts are descriptive associations. Age and starting-star tables reduce obvious confounding but do not establish incremental or causal source value.
