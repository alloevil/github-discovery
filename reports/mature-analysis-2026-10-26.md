# Mature recommendation analysis — 2026-10-26

This report covers **481 of 858 recommendations** (56.1%) with a 7-day reading. Unlabelled rows are excluded, not treated as failures.

## Score cohorts

| Score | Mature repos | Breakout rate | Median growth | Note |
|---|---:|---:|---:|---|
| 90–100 | 369 | 20.3% | 50.6% |  |
| 80–89 | 108 | 19.4% | 56.8% |  |
| 70–79 | 1 | 0.0% | 16.9% | thin (n<20) |
| 60–69 | 3 | 0.0% | 40.2% | thin (n<20) |
| <60 | 0 | — | — |  |

## Source cohorts

| Cohort | Mature repos | Breakout rate | Median growth | Note |
|---|---:|---:|---:|---|
| ai-trending | 15 | 26.7% | 89.7% | thin (n<20) |
| hf-papers | 7 | 28.6% | 59.6% | thin (n<20) |
| hn | 19 | 10.5% | 54.8% | thin (n<20) |
| hn+hf-papers | 1 | 100.0% | 290.8% | thin (n<20) |
| rising | 14 | 35.7% | 135.7% | thin (n<20) |
| search | 241 | 28.6% | 108.9% |  |
| search+ai-trending | 13 | 15.4% | 55.5% | thin (n<20) |
| search+ai-trending+hf-papers | 1 | 0.0% | 77.0% | thin (n<20) |
| search+hf-papers | 2 | 0.0% | 70.0% | thin (n<20) |
| search+hn | 1 | 0.0% | 97.9% | thin (n<20) |
| search+rising | 7 | 57.1% | 264.4% | thin (n<20) |
| trending | 159 | 4.4% | 9.2% |  |
| trending+hn | 1 | 0.0% | 5.2% | thin (n<20) |

## Recommendation-time age cohorts

| Cohort | Mature repos | Breakout rate | Median growth | Note |
|---|---:|---:|---:|---|
| 0–2d | 227 | 30.8% | 118.5% |  |
| 3–13d | 82 | 20.7% | 81.0% |  |
| 14–59d | 7 | 14.3% | 76.1% | thin (n<20) |
| 60d+ | 165 | 4.8% | 9.4% |  |

## Recommendation-time star cohorts

| Cohort | Mature repos | Breakout rate | Median growth | Note |
|---|---:|---:|---:|---|
| 0–99 | 9 | 33.3% | 164.4% | thin (n<20) |
| 100–999 | 291 | 27.8% | 99.3% |  |
| 1k–9.9k | 74 | 10.8% | 24.4% |  |
| 10k+ | 107 | 3.7% | 6.0% |  |

## Interpretation guardrails

- Mature coverage is **56.1%**; the remaining 377 recommendations are unknown, not negative labels.
- A cohort below 20 mature repos is marked thin and is not a basis for changing weights or adding a source.
- Source cohorts are descriptive associations. Age and starting-star tables reduce obvious confounding but do not establish incremental or causal source value.
