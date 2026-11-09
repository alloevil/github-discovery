# Mature recommendation analysis — 2026-11-09

This report covers **611 of 989 recommendations** (61.8%) with a 7-day reading. Unlabelled rows are excluded, not treated as failures.

## Score cohorts

| Score | Mature repos | Breakout rate | Median growth | Note |
|---|---:|---:|---:|---|
| 90–100 | 474 | 20.7% | 57.1% |  |
| 80–89 | 134 | 17.9% | 53.4% |  |
| 70–79 | 1 | 0.0% | 16.9% | thin (n<20) |
| 60–69 | 2 | 0.0% | 42.5% | thin (n<20) |
| <60 | 0 | — | — |  |

## Source cohorts

| Cohort | Mature repos | Breakout rate | Median growth | Note |
|---|---:|---:|---:|---|
| ai-trending | 21 | 23.8% | 70.6% |  |
| hf-papers | 8 | 25.0% | 69.5% | thin (n<20) |
| hn | 22 | 9.1% | 51.3% |  |
| hn+hf-papers | 1 | 100.0% | 290.8% | thin (n<20) |
| rising | 16 | 37.5% | 158.6% | thin (n<20) |
| search | 323 | 27.6% | 103.3% |  |
| search+ai-trending | 19 | 26.3% | 132.5% | thin (n<20) |
| search+ai-trending+hf-papers | 1 | 0.0% | 77.0% | thin (n<20) |
| search+hf-papers | 3 | 0.0% | 77.7% | thin (n<20) |
| search+hn | 2 | 0.0% | 71.5% | thin (n<20) |
| search+rising | 9 | 55.6% | 264.4% | thin (n<20) |
| trending | 185 | 3.8% | 9.4% |  |
| trending+hn | 1 | 0.0% | 5.2% | thin (n<20) |

## Recommendation-time age cohorts

| Cohort | Mature repos | Breakout rate | Median growth | Note |
|---|---:|---:|---:|---|
| 0–2d | 300 | 30.0% | 106.4% |  |
| 3–13d | 110 | 20.9% | 78.1% |  |
| 14–59d | 8 | 12.5% | 77.8% | thin (n<20) |
| 60d+ | 193 | 4.1% | 9.4% |  |

## Recommendation-time star cohorts

| Cohort | Mature repos | Breakout rate | Median growth | Note |
|---|---:|---:|---:|---|
| 0–99 | 11 | 27.3% | 102.9% | thin (n<20) |
| 100–999 | 373 | 27.3% | 96.6% |  |
| 1k–9.9k | 100 | 13.0% | 38.0% |  |
| 10k+ | 127 | 3.1% | 6.0% |  |

## Interpretation guardrails

- Mature coverage is **61.8%**; the remaining 378 recommendations are unknown, not negative labels.
- A cohort below 20 mature repos is marked thin and is not a basis for changing weights or adding a source.
- Source cohorts are descriptive associations. Age and starting-star tables reduce obvious confounding but do not establish incremental or causal source value.
