# Google Ads AI Manager - Agent Context

This repo demonstrates a safe AI-assisted operating model for Google Ads.

The business example is fictional: Acme Corp, a SaaS company selling project management software.

## System Model

Use a read/write split.

Reads:

- Use MCP and GAQL queries for campaign performance, search terms, keyword status, and budget pacing.
- Use the GA4 script for conversion event and attribution checks.
- Reads should not mutate the account.

Writes:

- All Google Ads mutations must happen through Python scripts.
- Scripts must be date-stamped or clearly versioned.
- Scripts must default to dry-run mode.
- Scripts must require `--apply` for live changes.
- Scripts must print a clear preview before applying.

## Script Naming

Use names that make the change auditable.

Examples:

- `create_campaign_apr22.py`
- `add_negatives_may07.py`
- `update_may06.py`
- `pause_low_ctr_keywords_may12.py`

The templates in `scripts/` are starting points. Copy a template into a dated script, edit the change set, run dry-run, then ask for approval before applying.

## Dry-run Pattern

Every write script follows this pattern:

```bash
python scripts/add_negatives_may07.py
python scripts/add_negatives_may07.py --apply
```

No `--apply` means no account mutation.

## Monitoring Routine

Run the routine three times per week.

Suggested cadence:

- Monday
- Wednesday
- Friday

The routine should:

1. Pull Google Ads data through MCP:
   - campaign performance
   - ad group performance
   - search terms
   - high CPC terms
   - low CTR ad groups
2. Pull GA4 conversion events through `scripts/query_ga4_events_template.py`.
3. Cross-reference ad spend with conversion events.
4. Flag search terms to add as negatives.
5. Flag bid changes or paused keywords for review.
6. Produce a report in `reports/`.
7. Wait for human approval before writing any changes.

## Human-in-the-loop Rules

Require human approval before:

- Budget changes.
- Campaign go-live.
- Negative keyword additions.
- Ad copy updates.
- Bid changes.
- Keyword pauses.
- Location targeting changes.

Campaign creation scripts must create campaigns and ads as `PAUSED` by default.

Never enable campaigns from a script unless the user explicitly asks for it and approves the exact campaign names.

## MCP Rule

MCP is for reads only in this repo.

Do not use MCP tools to write to Google Ads even if a third-party server supports it. The design goal here is a durable write artifact: a reviewed Python script that remains in version control.

## Data Hygiene

Do not commit:

- `.env`
- OAuth client secrets
- refresh tokens
- service account keys
- customer IDs from real accounts
- private keyword exports
- client names
- screenshots from live accounts

Use placeholders:

- `YOUR_CUSTOMER_ID`
- `YOUR_MCC_ID`
- `YOUR_GA4_PROPERTY_ID`

## Before Applying Any Script

Checklist:

- Run dry-run.
- Inspect every planned change.
- Confirm the target account ID.
- Confirm campaign status will remain paused if creating campaigns.
- Confirm budget values.
- Confirm negative keyword match types.
- Confirm CSV updates are intended.
- Ask for explicit approval.

