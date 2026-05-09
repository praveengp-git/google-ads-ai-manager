# Acme Corp Ads Routine - Sample Report

Generated: Monday, 2026-05-11, 13:00

Data window: last 7 days

## Performance Snapshot

| Campaign | Impressions | Clicks | CTR | Avg CPC | Conversions | Spend |
|---|---:|---:|---:|---:|---:|---:|
| Acme Search - US Core | 1,840 | 126 | 6.85% | 4.18 | 5 | 526.68 |
| Acme Search - US Enterprise | 920 | 48 | 5.22% | 6.40 | 3 | 307.20 |
| Acme Search - Remote Teams | 760 | 61 | 8.03% | 3.70 | 4 | 225.70 |

## Alerts

| Alert | Severity | Evidence | Suggested Action |
|---|---|---|---|
| High CPC on enterprise ad group | Medium | Avg CPC 6.40, 3 conversions | Review bids before scaling |
| Off-intent search terms | Medium | Terms include jobs, salary, free template | Add campaign-level negatives |
| Low conversion volume | Low | 12 total conversions | Keep manual review before bid automation |

## Search Terms To Review

| Search Term | Impressions | Clicks | Intent Read | Recommendation |
|---|---:|---:|---|---|
| project manager salary | 34 | 3 | job seeker | Add `salary` as broad negative |
| free project plan template | 28 | 5 | free template | Add `template` as broad negative |
| open source task manager | 19 | 2 | non-commercial | Add `open source` as phrase negative |
| project management certification course | 17 | 1 | learning intent | Add `course` as broad negative |

## Recommendations

1. Add 4 negative keywords: `salary`, `template`, `open source`, `course`.
2. Raise exact-match bid for `project management tool` from 5.00 to 5.50 in the US Core campaign.
3. Keep Remote Teams campaign running. It has the strongest CTR and lowest CPC.
4. Do not increase budgets yet. Conversion count is still thin.

## Awaiting Your Go-ahead

Reply with:

- `do 1` to create a dated negative-keyword script.
- `do 2` to create a dated bid-update script.
- `do 1,2` to create a combined dated update script.
- `skip` to defer all changes.

