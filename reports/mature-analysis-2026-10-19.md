# Mature recommendation analysis — 2026-10-19

This report covers **431 of 792 recommendations** (54.4%) with a 7-day reading. Unlabelled rows are excluded, not treated as failures.

## Score cohorts

| Score | Mature repos | Breakout rate | Median growth | Note |
|---|---:|---:|---:|---|
| 90–100 | 334 | 18.9% | 47.2% |  |
| 80–89 | 94 | 19.1% | 56.2% |  |
| 70–79 | 0 | — | — |  |
| 60–69 | 3 | 0.0% | 40.2% | thin (n<20) |
| <60 | 0 | — | — |  |

## Source cohorts

| Cohort | Mature repos | Breakout rate | Median growth | Note |
|---|---:|---:|---:|---|
| ai-trending | 13 | 30.8% | 89.7% | thin (n<20) |
| hf-papers | 6 | 33.3% | 56.3% | thin (n<20) |
| hn | 14 | 14.3% | 45.6% | thin (n<20) |
| hn+hf-papers | 1 | 100.0% | 290.8% | thin (n<20) |
| rising | 13 | 30.8% | 118.5% | thin (n<20) |
| search | 209 | 27.3% | 105.9% |  |
| search+ai-trending | 10 | 20.0% | 66.4% | thin (n<20) |
| search+ai-trending+hf-papers | 1 | 0.0% | 77.0% | thin (n<20) |
| search+hf-papers | 2 | 0.0% | 70.0% | thin (n<20) |
| search+rising | 6 | 50.0% | 213.2% | thin (n<20) |
| trending | 155 | 3.9% | 8.9% |  |
| trending+hn | 1 | 0.0% | 5.2% | thin (n<20) |

## Recommendation-time age cohorts

| Cohort | Mature repos | Breakout rate | Median growth | Note |
|---|---:|---:|---:|---|
| 0–2d | 196 | 29.1% | 106.4% |  |
| 3–13d | 71 | 22.5% | 87.1% |  |
| 14–59d | 4 | 25.0% | 56.6% | thin (n<20) |
| 60d+ | 160 | 4.4% | 9.1% |  |

## Recommendation-time star cohorts

| Cohort | Mature repos | Breakout rate | Median growth | Note |
|---|---:|---:|---:|---|
| 0–99 | 8 | 37.5% | 166.7% | thin (n<20) |
| 100–999 | 250 | 26.8% | 97.0% |  |
| 1k–9.9k | 69 | 10.1% | 25.5% |  |
| 10k+ | 104 | 3.8% | 5.4% |  |

## Interpretation guardrails

- Mature coverage is **54.4%**; the remaining 361 recommendations are unknown, not negative labels.
- A cohort below 20 mature repos is marked thin and is not a basis for changing weights or adding a source.
- Source cohorts are descriptive associations. Age and starting-star tables reduce obvious confounding but do not establish incremental or causal source value.
