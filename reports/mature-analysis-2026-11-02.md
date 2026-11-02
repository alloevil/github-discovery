# Mature recommendation analysis — 2026-11-02

This report covers **548 of 923 recommendations** (59.4%) with a 7-day reading. Unlabelled rows are excluded, not treated as failures.

## Score cohorts

| Score | Mature repos | Breakout rate | Median growth | Note |
|---|---:|---:|---:|---|
| 90–100 | 416 | 20.9% | 55.1% |  |
| 80–89 | 129 | 17.8% | 52.7% |  |
| 70–79 | 1 | 0.0% | 16.9% | thin (n<20) |
| 60–69 | 2 | 0.0% | 41.2% | thin (n<20) |
| <60 | 0 | — | — |  |

## Source cohorts

| Cohort | Mature repos | Breakout rate | Median growth | Note |
|---|---:|---:|---:|---|
| ai-trending | 19 | 21.1% | 70.6% | thin (n<20) |
| hf-papers | 8 | 25.0% | 69.5% | thin (n<20) |
| hn | 21 | 9.5% | 47.9% |  |
| hn+hf-papers | 1 | 100.0% | 290.8% | thin (n<20) |
| rising | 15 | 40.0% | 152.8% | thin (n<20) |
| search | 281 | 28.1% | 105.9% |  |
| search+ai-trending | 18 | 27.8% | 104.9% | thin (n<20) |
| search+ai-trending+hf-papers | 1 | 0.0% | 77.0% | thin (n<20) |
| search+hf-papers | 2 | 0.0% | 70.0% | thin (n<20) |
| search+hn | 2 | 0.0% | 71.5% | thin (n<20) |
| search+rising | 8 | 50.0% | 196.7% | thin (n<20) |
| trending | 171 | 4.1% | 9.2% |  |
| trending+hn | 1 | 0.0% | 5.2% | thin (n<20) |

## Recommendation-time age cohorts

| Cohort | Mature repos | Breakout rate | Median growth | Note |
|---|---:|---:|---:|---|
| 0–2d | 263 | 30.8% | 113.5% |  |
| 3–13d | 98 | 20.4% | 77.3% |  |
| 14–59d | 8 | 12.5% | 77.8% | thin (n<20) |
| 60d+ | 179 | 4.5% | 9.2% |  |

## Recommendation-time star cohorts

| Cohort | Mature repos | Breakout rate | Median growth | Note |
|---|---:|---:|---:|---|
| 0–99 | 11 | 27.3% | 102.9% | thin (n<20) |
| 100–999 | 334 | 27.5% | 97.6% |  |
| 1k–9.9k | 87 | 12.6% | 32.0% |  |
| 10k+ | 116 | 3.4% | 5.5% |  |

## Interpretation guardrails

- Mature coverage is **59.4%**; the remaining 375 recommendations are unknown, not negative labels.
- A cohort below 20 mature repos is marked thin and is not a basis for changing weights or adding a source.
- Source cohorts are descriptive associations. Age and starting-star tables reduce obvious confounding but do not establish incremental or causal source value.
